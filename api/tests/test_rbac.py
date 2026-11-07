"""Role-based access control: who may do what. Each test is one promise; CI keeps them true."""
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from starlette.requests import Request  # noqa: E402

import main  # noqa: E402
import roles  # noqa: E402
from conftest import ADMIN  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)


def _guarded():
    """Every route guarded by core.require(...), with the permission it needs. Found from the app, not listed by hand."""
    out = []
    for r in main.app.routes:
        stack = list(getattr(getattr(r, "dependant", None), "dependencies", []))
        while stack:
            d = stack.pop()
            if getattr(d.call, "permission", None):
                out.append((r, d.call))
                break
            stack.extend(d.dependencies)
    return out


GUARDED = _guarded()
PERSONAS = {
    "patient": auth_as("rb-patient"),
    "pharmacist": auth_as("rb-pharm", roles=("pharmacist",)),
    "regulator": auth_as("rb-reg", roles=("regulator",)),
    "admin": auth_as("rb-admin", roles=("admin",)),
}


def _request(headers: dict) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()]})


def test_the_permission_matrix_is_what_we_document():
    assert len(GUARDED) >= 15
    m = {p: set(rs) for p, rs in roles.PERMISSIONS.items()}
    assert m["sales.manage"] == {"pharmacist"}            # a regulator or admin can't read a shop's customer list
    assert m["holders.view"] == {"regulator", "admin"}    # names + phones of holders: never a pharmacist or patient
    assert m["roles.decide"] == {"admin"}
    assert "patient" not in set().union(*m.values())     # being a patient never unlocks a professional endpoint


def test_every_guarded_endpoint_allows_exactly_the_roles_it_should():
    for route, dep in GUARDED:
        path = re.sub(r"\{[^}]+\}", "1", route.path)
        for persona, h in PERSONAS.items():
            ok = roles.allowed(roles.of(main.conn, h["X-Device-Id"]), dep.permission)
            if ok:  # checked on the dependency itself, so allowed calls send nothing and fetch nothing
                assert dep(_request(h))["roles"]
            else:
                for m in route.methods - {"HEAD"}:
                    res = client.request(m, path, headers=h, json={})
                    assert res.status_code == 403, f"{persona} {m} {route.path} -> {res.status_code}"


def test_every_guarded_endpoint_refuses_a_request_without_a_session():
    for route, _ in GUARDED:
        path = re.sub(r"\{[^}]+\}", "1", route.path)
        for m in route.methods - {"HEAD"}:
            assert client.request(m, path, json={}).status_code == 401, f"{m} {route.path}"


def test_roles_only_count_on_a_phone_verified_session():
    roles.grant(main.conn, "rb-guest-reg", "regulator", "test")
    guest = auth_as("rb-guest-reg", kind="guest")
    assert client.get("/api/controller", headers=guest).status_code == 403
    assert client.get("/api/controller", headers=auth_as("rb-guest-reg")).status_code == 200


def test_request_approve_revoke_lifecycle(monkeypatch):
    monkeypatch.setenv("KINCARE_DEMO", "0")
    h = auth_as("rb-new-pharm")
    r = client.post("/api/roles/request", headers=h, json={"role": "pharmacist", "org": "Shree Medicos", "licence": "DL-20B-1234"}).json()
    assert r["status"] == "pending"
    assert client.get("/api/sales", headers=h).status_code == 403          # pending is not granted
    assert client.post("/api/roles/request", headers=h, json={"role": "pharmacist", "org": "x y", "licence": "abc"}).json()["id"] == r["id"]
    assert client.post(f"/api/admin/roles/{r['id']}/approve", headers=PERSONAS["regulator"]).status_code == 403
    assert client.post(f"/api/admin/roles/{r['id']}/approve", headers=ADMIN).json()["status"] == "active"
    assert client.get("/api/sales", headers=h).status_code == 200
    assert "sales.manage" in client.get("/api/auth/me", headers=h).json()["permissions"]
    assert client.post(f"/api/admin/roles/{r['id']}/revoke", headers=PERSONAS["admin"]).json()["status"] == "revoked"
    assert client.get("/api/sales", headers=h).status_code == 403
    assert client.post(f"/api/admin/roles/{r['id']}/approve", headers=ADMIN).status_code == 409  # revoked stays revoked
    acts = [a["action"] for a in client.get("/api/admin/audit", headers=ADMIN).json() if a["target"] in ("pharmacist", "rb-new-pharm")]
    assert {"role.request", "role.approve", "role.revoke"} <= set(acts)


def test_nobody_can_make_themselves_admin_or_approve_themselves(monkeypatch):
    monkeypatch.setenv("KINCARE_DEMO", "0")
    h = PERSONAS["admin"]
    assert client.post("/api/roles/request", headers=h, json={"role": "admin", "org": "KinCare", "licence": "self"}).status_code == 400
    gid = client.post("/api/roles/request", headers=h, json={"role": "regulator", "org": "CDSCO", "licence": "EMP-1"}).json()["id"]
    assert client.post(f"/api/admin/roles/{gid}/approve", headers=h).status_code == 403
    guest = auth_as("rb-guest", kind="guest")
    assert client.post("/api/roles/request", headers=guest, json={"role": "pharmacist", "org": "Shop", "licence": "DL-1"}).status_code == 403


def test_admin_grants_by_phone_and_an_admin_session_needs_no_token():
    main.conn.execute("INSERT OR IGNORE INTO users (phone, device, created_at) VALUES ('+919800011122', 'rb-by-phone', '2026-10-25')")
    assert client.post("/api/admin/roles/grant", headers=PERSONAS["pharmacist"], json={"phone": "9800011122", "role": "admin"}).status_code == 403
    assert client.post("/api/admin/roles/grant", headers=ADMIN, json={"phone": "9800011122", "role": "regulator"}).json()["ok"]
    assert client.get("/api/controller", headers=auth_as("rb-by-phone")).status_code == 200
    assert client.get("/api/admin/overview", headers=PERSONAS["admin"]).status_code == 200
    assert client.get("/api/admin/overview", headers=PERSONAS["regulator"]).status_code == 403


def test_pharmacies_never_see_each_others_customers():
    a, b = auth_as("rb-shop-a", roles=("pharmacist",)), auth_as("rb-shop-b", roles=("pharmacist",))
    client.put("/api/sales", headers=a, json=[{"customer": "Ravi", "phone": "9876500001", "batch": "RB1"}])
    assert client.get("/api/sales", headers=b).json() == []
    assert [s["customer"] for s in client.get("/api/sales", headers=a).json()] == ["Ravi"]


def test_regulators_see_masked_phones_admins_see_full():
    main.conn.execute("INSERT INTO notifications (channel, name, phone, language, batch, message, status) VALUES ('whatsapp','Asha','+919812345678','hi','RB2','x','sent')")
    main.conn.commit()
    reg = next(n for n in client.get("/api/notifications", headers=PERSONAS["regulator"]).json() if n["batch"] == "RB2")
    adm = next(n for n in client.get("/api/notifications", headers=ADMIN).json() if n["batch"] == "RB2")
    assert reg["phone"] == "+91 ••••• 5678" and adm["phone"] == "+919812345678"


def test_a_pharmacist_cannot_message_an_arbitrary_number(monkeypatch):
    monkeypatch.setenv("KINCARE_DEMO", "0")
    r = client.post("/api/recall/run", headers=PERSONAS["pharmacist"], json={"scope": "latest", "demo_phone": "9811122233"})
    assert r.status_code == 403


def test_looking_at_holders_is_audited_and_refusals_leave_no_trace():
    c = main.conn
    c.execute("""INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                 VALUES ('cdsco_nsq', 'nsq', 'Rbacin 500', 'Rbacin 500', 'RB-77', 'RB77', 'Test Labs', 'Assay', '2026-09', 'https://x')""")
    c.commit()
    try:
        assert client.get("/api/blast/RB-77", headers=PERSONAS["pharmacist"]).status_code == 403
        assert not [a for a in roles.log(c, 500) if a["target"] == "RB-77"]
        assert client.get("/api/blast/RB-77", headers=PERSONAS["regulator"]).status_code == 200
        seen = [a for a in roles.log(c, 500) if a["target"] == "RB-77"]
        assert len(seen) == 1 and seen[0]["action"] == "holders.view" and seen[0]["actor"] == "rb-reg"
    finally:
        c.execute("DELETE FROM alerts WHERE batch_norm = 'RB77'")  # other test files count alerts in this shared DB
        c.commit()


def test_the_audit_log_never_shows_account_ids_even_to_admins(monkeypatch):
    monkeypatch.setenv("KINCARE_DEMO", "0")
    main.conn.execute("INSERT OR IGNORE INTO users (phone, device, created_at) VALUES ('+919800055566', 'acct_rbaudit', '2026-10-25')")
    client.post("/api/roles/request", headers=auth_as("acct_rbaudit"), json={"role": "regulator", "org": "CDSCO", "licence": "EMP-9"})
    text = str(client.get("/api/admin/audit", headers=ADMIN).json())
    assert "acct_" not in text and "+91 ••••• 5566" in text
