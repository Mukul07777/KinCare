import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import sessions  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
c = main.conn


def login(device: str, phone: str) -> dict:
    h = auth_as(device)
    code = client.post("/api/auth/start", headers=h, json={"phone": phone}).json()["demo_code"]  # no WhatsApp in tests: demo mode
    return client.post("/api/auth/verify", headers=h, json={"phone": phone, "code": code}).json()


def browser():
    """A browser: its own cookie jar, the HttpOnly session cookie, and the X-KinCare header the web app adds."""
    b = TestClient(main.app, headers={"X-KinCare": "1"})
    assert b.post("/api/session").json() == {"session": True, "signed_in": False, "masked": None}
    return b


def code_for(b, phone):
    return b.post("/api/auth/start", json={"phone": phone}).json()["demo_code"]  # KINCARE_DEMO=1 in tests


def test_first_login_keeps_this_phones_data_and_second_phone_joins_the_account():
    a, b = browser(), browser()
    guest_cookie = a.cookies.get(sessions.COOKIE)
    a.post("/api/watchlist", json={"batch": "AUTHB1", "brand": "X"})
    r = a.post("/api/auth/verify", json={"phone": "98111 22233", "code": code_for(a, "98111 22233")}).json()
    assert r["signed_in"] and r["new"] and "device" not in r  # the account id never leaves the server
    assert a.cookies.get(sessions.COOKIE) != guest_cookie       # new session after login (no session fixation)
    assert sessions.resolve(main.conn, guest_cookie) is None    # the guest token is dead

    # Second phone already had its own watchlist item and a vitals reading: both merge into the account.
    b.post("/api/watchlist", json={"batch": "AUTHB2", "brand": "Y"})
    b.post("/api/care/vitals", json={"member": "Me", "pulse": 80})
    r = b.post("/api/auth/verify", json={"phone": "+91 9811122233", "code": code_for(b, "+91 9811122233")}).json()
    assert not r["new"] and r["merged"] >= 2
    for x in (a, b):  # both phones now see the same account
        assert {w["batch"] for w in x.get("/api/watchlist").json()} >= {"AUTHB1", "AUTHB2"}
    assert b.get("/api/care/vitals").json()[0]["pulse"] == 80
    assert a.get("/api/auth/me").json()["masked"] == "+91 ••••• 2233"
    assert len(a.get("/api/auth/sessions").json()) == 2


def test_wrong_code_expiry_and_rate_limit():
    h = auth_as("auth-phone-c")
    p = "9822233344"
    client.post("/api/auth/start", headers=h, json={"phone": p})
    bad = client.post("/api/auth/verify", headers=h, json={"phone": p, "code": "000000"})
    assert bad.status_code == 401 and "4 tries left" in bad.json()["detail"]
    for _ in range(4):
        client.post("/api/auth/verify", headers=h, json={"phone": p, "code": "000000"})
    locked = client.post("/api/auth/verify", headers=h, json={"phone": p, "code": "000000"})
    assert locked.status_code == 401 and "Ask for a new code" in locked.json()["detail"]

    client.post("/api/auth/start", headers=h, json={"phone": p})
    third = client.post("/api/auth/start", headers=h, json={"phone": p})
    assert third.status_code == 200
    assert client.post("/api/auth/start", headers=h, json={"phone": p}).status_code == 429  # 4th send in 10 minutes

    # An expired code never works, even if correct.
    code = third.json()["demo_code"]
    c.execute("UPDATE otps SET expires_at = '2000-01-01T00:00:00+00:00' WHERE phone = '+919822233344' AND used = 0")
    c.commit()
    assert "expired" in client.post("/api/auth/verify", headers=h, json={"phone": p, "code": code}).json()["detail"]


def test_old_code_dies_when_a_new_one_is_sent():
    h = auth_as("auth-phone-d")
    p = "9833344455"
    first = client.post("/api/auth/start", headers=h, json={"phone": p}).json()["demo_code"]
    second = client.post("/api/auth/start", headers=h, json={"phone": p}).json()["demo_code"]
    if first != second:
        assert client.post("/api/auth/verify", headers=h, json={"phone": p, "code": first}).status_code == 401
    assert client.post("/api/auth/verify", headers=h, json={"phone": p, "code": second}).status_code == 200
