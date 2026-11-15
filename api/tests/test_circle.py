"""Care circle: passcode access, elder approval, adherence, appointments, email reminders."""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import circle  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
conn = main.conn


def _profile(owner: str, approve=True, passcode="482913"):
    h = auth_as(owner)
    for t in ("circle_profiles",):
        conn.execute(f"DELETE FROM {t} WHERE owner_device = ?", (owner,))
    r = client.post("/api/circle/profiles", headers=h, json={"member": "Dadi", "elder_name": "Kamla", "elder_email": "kamla@example.com",
                                                             "passcode": passcode, "approve_changes": approve})
    assert r.status_code == 200, r.text
    return h, r.json()["code"]


def _unlock(code, passcode="482913", name="Rahul", role="family"):
    return client.post("/api/circle/unlock", json={"code": code, "passcode": passcode, "name": name, "email": "rahul@example.com", "role": role})


def _emails(subject_part: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM emails WHERE subject LIKE ?", (f"%{subject_part}%",)).fetchone()[0]


def test_weak_passcodes_rejected():
    h = auth_as("circle-weak")
    for p in ("123456", "111111", "abc"):
        r = client.post("/api/circle/profiles", headers=h, json={"elder_name": "X", "passcode": p})
        assert r.status_code == 400


def test_unlock_needs_right_passcode_and_locks_out():
    _, code = _profile("circle-lock")
    assert client.get(f"/api/circle/p/{code}").status_code == 401  # no token, not the owner
    for _ in range(4):
        assert _unlock(code, "000999").status_code == 401
    assert _unlock(code, "000999").status_code == 401  # 5th: locks
    assert _unlock(code).status_code == 429  # even the right passcode, while locked
    assert _emails("wrong passcode entered 5 times") >= 1


def test_member_changes_wait_for_elder_approval():
    h, code = _profile("circle-approve", approve=True)
    tok = {"X-Circle-Token": _unlock(code).json()["token"]}
    r = client.post(f"/api/circle/p/{code}/meds", headers=tok, json={"name": "Amlodipine", "strength": "5 mg", "morning": True})
    assert r.json()["status"] == "pending"
    assert client.get(f"/api/circle/p/{code}", headers=tok).json()["medicines"] == []
    assert _emails("asks to change") >= 1
    cid = r.json()["change_id"]
    assert client.post(f"/api/circle/profiles/{code}/changes/{cid}", headers=tok, json={"approve": True}).status_code == 401  # only the elder
    assert client.post(f"/api/circle/profiles/{code}/changes/{cid}", headers=h, json={"approve": True}).json()["status"] == "applied"
    meds = client.get(f"/api/circle/p/{code}", headers=tok).json()["medicines"]
    assert [m["name"] for m in meds] == ["Amlodipine"]


def test_elder_edits_apply_directly_and_view_only_members_cannot_edit():
    h, code = _profile("circle-direct", approve=False)
    r = client.post(f"/api/circle/p/{code}/meds", headers=h, json={"name": "Metformin", "strength": "500 mg", "morning": True, "night": True})
    assert r.json()["status"] == "applied"
    mid = r.json()["med_id"]
    assert client.put(f"/api/circle/p/{code}/meds/{mid}", headers=h, json={"strength": "1000 mg"}).json()["status"] == "applied"
    u = _unlock(code, name="Asha", role="caretaker").json()
    client.put(f"/api/circle/profiles/{code}/members/{u['member_id']}", headers=h, json={"can_edit": False})
    assert client.delete(f"/api/circle/p/{code}/meds/{mid}", headers={"X-Circle-Token": u["token"]}).status_code == 403
    client.delete(f"/api/circle/profiles/{code}/members/{u['member_id']}", headers=h)
    assert client.get(f"/api/circle/p/{code}", headers={"X-Circle-Token": u["token"]}).status_code == 401  # removed


def test_other_profile_token_is_useless():
    _, a = _profile("circle-a")
    _, b = _profile("circle-b")
    tok = {"X-Circle-Token": _unlock(a).json()["token"]}
    assert client.get(f"/api/circle/p/{b}", headers=tok).status_code == 401


def test_adherence_and_reminder_emails():
    h, code = _profile("circle-adh", approve=False)
    prof = circle.profile(conn, code)
    mid = client.post(f"/api/circle/p/{code}/meds", headers=h, json={"name": "Telma", "strength": "40 mg", "morning": True}).json()["med_id"]
    conn.execute("UPDATE plans SET start_date = ? WHERE device = ?", ((datetime.now().date() - timedelta(days=3)).isoformat(), "circle-adh"))
    for i in (1, 2):
        client.post(f"/api/circle/p/{code}/doses", headers=h,
                    json={"med_id": mid, "slot": "morning", "day": (datetime.now().date() - timedelta(days=i)).isoformat()})
    day = datetime.now().replace(hour=7, minute=50, second=0, microsecond=0)  # 10 min before the 08:00 dose
    a = circle.adherence(conn, prof, 7, day)
    assert a["streak_days"] == 2 and a["pct_7"] == 67  # 3 days due before today's 08:00, 2 taken
    before = _emails("08:00 dose, Telma")
    circle.run_reminders(conn, day)
    circle.run_reminders(conn, day)  # never twice
    assert _emails("08:00 dose, Telma") == before + 1
    circle.run_reminders(conn, day.replace(hour=9, minute=5))
    assert _emails("hasn't taken Telma") >= 1


def test_appointments_crud_and_reminders():
    h, code = _profile("circle-appt")
    tok = {"X-Circle-Token": _unlock(code).json()["token"]}
    when = (datetime.now() + timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M")
    a = client.post(f"/api/circle/p/{code}/appointments", headers=tok, json={"doctor": "Dr Mehta", "specialty": "Cardiology", "at": when})
    assert a.status_code == 200, a.text
    assert client.post(f"/api/circle/p/{code}/appointments", headers=tok, json={"doctor": "X", "at": "tomorrow"}).status_code == 400
    circle.run_reminders(conn)
    assert _emails("appointment tomorrow with Dr Mehta") == 2  # elder + Rahul
    aid = a.json()["id"]
    assert client.put(f"/api/circle/p/{code}/appointments/{aid}", headers=tok, json={"status": "cancelled"}).json()["status"] == "cancelled"
    assert client.get(f"/api/circle/p/{code}/appointments", headers=tok).json() == []
    assert client.delete(f"/api/circle/p/{code}/appointments/{aid}", headers=h).json()["ok"]


def test_care_note_and_calendar_link_without_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    h, code = _profile("circle-note")
    client.post(f"/api/circle/p/{code}/appointments", headers=h, json={"doctor": "Dr Rao", "at": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT10:00")})
    v = client.get(f"/api/circle/p/{code}", headers=h).json()
    assert v["appointments"][0]["gcal"].startswith("https://calendar.google.com/calendar/render?action=TEMPLATE")
    n = client.get(f"/api/circle/p/{code}/note?lang=hi", headers=h).json()
    assert n["source"] == "rules" and "Dr Rao" in n["text"]
