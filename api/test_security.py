"""Security and privacy guarantees for medical data. Each test is one promise; CI keeps them true."""
import os
import re
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import core  # noqa: E402
import main  # noqa: E402
import sessions  # noqa: E402
import vault  # noqa: E402
from db import DB_PATH  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)


def _needs_account(route) -> bool:
    deps = getattr(route, "dependant", None)
    stack = list(deps.dependencies) if deps else []
    while stack:
        d = stack.pop()
        if d.call in (core.current_account, core.signed_in_account):
            return True
        stack.extend(d.dependencies)
    return False


PERSONAL = [r for r in main.app.routes if getattr(r, "methods", None) and _needs_account(r)]


def test_every_personal_endpoint_refuses_a_request_without_a_session():
    assert len(PERSONAL) >= 60
    for r in PERSONAL:
        path = re.sub(r"\{[^}]+\}", "1", r.path)
        for m in r.methods - {"HEAD"}:
            res = client.request(m, path, json={})
            assert res.status_code == 401, f"{m} {r.path} -> {res.status_code}"


def test_a_device_id_header_or_a_forged_token_gives_nothing():
    client.post("/api/care/vitals", headers=auth_as("sec-victim"), json={"member": "Me", "bp_sys": 150, "bp_dia": 95})
    for h in ({"X-Device-Id": "sec-victim"}, {"Authorization": "Bearer sec-victim"}, {"Authorization": "Bearer " + "A" * 43},
              {"Cookie": f"{sessions.COOKIE}=sec-victim"}):
        assert client.get("/api/care/vitals", headers=h).status_code == 401, h


def test_tokens_are_stored_only_as_hashes_and_are_256_bit():
    tok = sessions.create(main.conn, "sec-hash", "guest")
    assert len(tok) >= 43  # 32 random bytes, base64url
    raw = sqlite3.connect(DB_PATH).execute("SELECT group_concat(token_hash) FROM sessions").fetchone()[0]
    assert tok not in raw and sessions._hash(tok) in raw


def test_revoked_and_expired_sessions_stop_working():
    tok = sessions.create(main.conn, "sec-rev", "user")
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/watchlist", headers=h).status_code == 200
    client.post("/api/auth/logout", headers=h)
    assert client.get("/api/watchlist", headers=h).status_code == 401
    tok2 = sessions.create(main.conn, "sec-rev", "user")
    main.conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE token_hash = ?", (sessions._hash(tok2),))
    assert client.get("/api/watchlist", headers={"Authorization": f"Bearer {tok2}"}).status_code == 401


def test_sign_out_other_devices_keeps_this_one():
    a, b = sessions.create(main.conn, "sec-many", "user"), sessions.create(main.conn, "sec-many", "user")
    ha, hb = {"Authorization": f"Bearer {a}"}, {"Authorization": f"Bearer {b}"}
    assert client.post("/api/auth/logout-others", headers=ha).json()["ended"] >= 1
    assert client.get("/api/watchlist", headers=ha).status_code == 200
    assert client.get("/api/watchlist", headers=hb).status_code == 401


def test_session_cookie_is_httponly_and_samesite():
    r = TestClient(main.app).post("/api/session")
    c = r.headers["set-cookie"].lower()
    assert "httponly" in c and "samesite=lax" in c and "path=/" in c


def test_csrf_cookie_requests_need_the_app_header_and_origin():
    b = TestClient(main.app)
    b.post("/api/session")
    body = {"batch": "CSRF1"}
    assert b.post("/api/watchlist", json=body).status_code == 403                                         # no X-KinCare
    assert b.post("/api/watchlist", json=body, headers={"X-KinCare": "1", "Origin": "https://evil.example"}).status_code == 403
    assert b.post("/api/watchlist", json=body, headers={"X-KinCare": "1"}).status_code == 200
    assert b.get("/api/watchlist").status_code == 200                                                     # reads need no header


def test_security_headers_and_no_caching_of_medical_data():
    r = client.get("/api/watchlist", headers=auth_as("sec-hdr"))
    for k, v in {"x-content-type-options": "nosniff", "x-frame-options": "DENY", "referrer-policy": "no-referrer", "cache-control": "no-store"}.items():
        assert r.headers.get(k) == v, k
    assert "default-src 'none'" in r.headers["content-security-policy"]


def test_cors_allows_only_configured_origins():
    r = client.options("/api/watchlist", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"


def test_production_never_shows_login_codes(monkeypatch):
    monkeypatch.delenv("KINCARE_DEMO", raising=False)
    r = client.post("/api/auth/start", headers=auth_as("sec-prod", "guest"), json={"phone": "9800000001"})
    assert r.status_code == 503 and "demo_code" not in r.text


def test_admin_always_needs_the_token(monkeypatch):
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"X-Admin-Token": "wrong"}).status_code == 401
    monkeypatch.delenv("ADMIN_TOKEN")
    for h in ({}, {"X-Admin-Token": ""}, {"X-Admin-Token": "None"}):  # no token configured: admin is off, not open
        assert client.get("/api/admin/overview", headers=h).status_code == 401


def test_unsigned_whatsapp_webhooks_are_refused_outside_demo(monkeypatch):
    monkeypatch.delenv("KINCARE_DEMO", raising=False)
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    body = {"entry": [{"changes": [{"value": {"messages": [{"from": "919800000002", "type": "text", "text": {"body": "1"}}]}}]}]}
    assert client.post("/api/whatsapp/webhook", json=body).status_code == 401


def test_whatsapp_simulator_cannot_act_as_a_real_phone():
    import inspect

    from routes import whatsapp_bot

    assert "phone" not in inspect.signature(whatsapp_bot.whatsapp_simulate).parameters
    assert whatsapp_bot.SANDBOX_PHONE == "+910000000000"


def test_sharing_health_data_needs_a_verified_phone():
    r = client.post("/api/caregiver/invite", headers=auth_as("sec-guest", "guest"), json={"scopes": ["doses"]})
    assert r.status_code == 403 and "Sign in" in r.json()["detail"]
    assert client.post("/api/doctor/links", headers=auth_as("sec-guest", "guest"), json={"member": "Me"}).status_code == 403


def test_login_and_invite_codes_are_rate_limited():
    h = auth_as("sec-rl", "guest")
    codes = [client.post("/api/auth/start", headers=h, json={"phone": f"98000000{i:02d}"}).status_code for i in range(7)]
    assert codes[:5] == [200] * 5 and 429 in codes[5:]
    codes = [client.get(f"/api/caregiver/invite/ZZZZ{i:02d}").status_code for i in range(22)]
    assert 429 in codes


def test_chats_doctor_messages_and_diagnoses_are_encrypted_at_rest():
    h = auth_as("sec-vault")
    client.post("/api/dadi/chat", headers=h, json={"text": "mera BP 150 by 95 hai", "lang": "en"})
    client.post("/api/care/plans", headers=h, json={"member": "Me", "diagnosis": "Hypertension stage 2", "medicines": [{"name": "Telma 40", "morning": 1}]})
    db = sqlite3.connect(DB_PATH)
    raw_chat = [r[0] for r in db.execute("SELECT text FROM dadi_chat WHERE device = 'sec-vault'")]
    raw_dx = db.execute("SELECT diagnosis FROM plans WHERE device = 'sec-vault'").fetchone()[0]
    assert raw_chat and all(t.startswith("enc1:") for t in raw_chat) and raw_dx.startswith("enc1:")
    assert "150" not in " ".join(raw_chat) and "Hypertension" not in raw_dx
    # The app still reads them back.
    assert client.get("/api/dadi/history", headers=h).json()[0]["text"] == "mera BP 150 by 95 hai"
    assert client.get("/api/care/plans", headers=h).json()[0]["diagnosis"] == "Hypertension stage 2"


def test_ciphertext_cannot_be_tampered_or_moved_between_columns():
    from cryptography.exceptions import InvalidTag

    c = vault.seal("secret note", "dadi_chat", "text")
    with pytest.raises(InvalidTag):
        vault.open_(c, "doctor_messages", "text")  # bound to its table and column
    flipped = c[:-2] + ("A" if c[-2] != "A" else "B") + c[-1]
    with pytest.raises(Exception):
        vault.open_(flipped, "dadi_chat", "text")
    assert vault.seal("same", "plans", "diagnosis") != vault.seal("same", "plans", "diagnosis")  # fresh nonce each time


def test_old_plaintext_rows_get_encrypted():
    main.conn.execute("INSERT INTO dadi_chat (device, role, text) VALUES ('sec-old', 'me', 'written before encryption')")
    assert vault.migrate(main.conn) >= 1
    raw = sqlite3.connect(DB_PATH).execute("SELECT text FROM dadi_chat WHERE device = 'sec-old'").fetchone()[0]
    assert raw.startswith("enc1:") and vault.open_(raw, "dadi_chat", "text") == "written before encryption"
