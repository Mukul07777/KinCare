"""DPDP Act rights: see everything held about you, erase it; and no shared device ids that would pool strangers' data."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import privacy  # noqa: E402

client = TestClient(main.app)


def H(d):
    return auth_as(d)


def test_device_id_header_is_ignored_identity_comes_only_from_the_session():
    client.post("/api/care/vitals", headers=H("pv-victim"), json={"member": "Me", "bp_sys": 150, "bp_dia": 95})
    # Knowing someone's id is worth nothing: without their session token there is no session at all...
    assert client.get("/api/care/vitals", headers={"X-Device-Id": "pv-victim"}).status_code == 401
    # ...and with your own token, their id in the header still gives you only your own data.
    mine = client.get("/api/care/vitals", headers={**H("pv-attacker"), "X-Device-Id": "pv-victim"}).json()
    assert mine == []


def _fill(dev, cg):
    client.post("/api/care/plans", headers=H(dev), json={"member": "Papa", "medicines": [{"name": "Telma 40", "morning": 1}]})
    mid = main.conn.execute("SELECT m.id FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ?", (dev,)).fetchone()[0]
    client.post("/api/care/doses", headers=H(dev), json={"med_id": mid, "slot": "morning"})
    client.post("/api/care/vitals", headers=H(dev), json={"member": "Papa", "bp_sys": 130, "bp_dia": 85})
    client.post("/api/dadi/chat", headers=H(dev), json={"text": "namaste"})
    code = client.post("/api/caregiver/invite", headers=H(dev), json={"member": "Papa", "scopes": ["doses"]}).json()["code"]
    lid = client.post("/api/caregiver/accept", headers=H(cg), json={"code": code, "name": "Rahul"}).json()["link_id"]
    client.get(f"/api/caregiver/elder/{lid}", headers=H(cg))
    return mid, lid


def test_export_has_everything_and_no_secrets():
    _fill("pv-elder", "pv-son")
    d = client.get("/api/account/export", headers=H("pv-elder")).json()["data"]
    for k in ("plans", "plan_medicines", "doses_taken", "vitals", "dadi_chat", "caregiver_links", "caregiver_access_log"):
        assert d.get(k), k
    assert "push_subs" not in d and "tg_codes" not in d


def test_erase_removes_everything_and_ends_caregiver_links():
    mid, lid = _fill("pv-del", "pv-del-son")
    r = client.delete("/api/account", headers=H("pv-del")).json()["deleted"]
    assert r["plans"] and r["plan_meds"] and r["doses"] and r["vitals"] and r["care_links"]
    assert client.get("/api/account/export", headers=H("pv-del")).status_code == 401  # every session of the account ended too
    left = privacy.export(main.conn, "pv-del")
    assert set(left) <= {"accounts"}
    assert not main.conn.execute("SELECT 1 FROM doses WHERE med_id = ?", (mid,)).fetchone()
    assert client.get(f"/api/caregiver/elder/{lid}", headers=H("pv-del-son")).status_code == 400
    assert client.get("/api/caregiver/links", headers=H("pv-del-son")).json()["watching"] == []


def test_erase_leaves_other_people_alone():
    _fill("pv-keep", "pv-keep-son")
    _fill("pv-gone", "pv-gone-son")
    client.delete("/api/account", headers=H("pv-gone"))
    assert client.get("/api/account/export", headers=H("pv-keep")).json()["data"].get("plans")


def test_retention_purges_only_old_raw_data():
    main.conn.execute("INSERT INTO dadi_chat (device, role, text, at) VALUES ('pv-old', 'me', 'old', '2020-01-01T00:00:00Z')")
    main.conn.execute("INSERT INTO dadi_chat (device, role, text) VALUES ('pv-old', 'me', 'new')")
    privacy.purge_old(main.conn)
    assert [r[0] for r in main.conn.execute("SELECT text FROM dadi_chat WHERE device = 'pv-old'")] == ["new"]
