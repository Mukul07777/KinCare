"""Edge cases for Dadi chat, caregivers and Telegram: wrong words, wrong people, wrong times."""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import caregiver  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import voice  # noqa: E402

client = TestClient(main.app)


def H(d):
    return auth_as(d)


def plan(dev, member="Papa", start=None, **slots):
    start = start or (datetime.now().date() - timedelta(days=1)).isoformat()
    meds = [{"name": "Telma 40", "strength": "40 mg", "morning": 1, "noon": 0, "night": 1, **slots}]
    r = client.post("/api/care/plans", headers=H(dev), json={"member": member, "start_date": start, "medicines": meds})
    assert r.status_code == 200, r.text


def mine(dev, at):
    return [d for l, d in caregiver.missed_doses(main.conn, at) if l["elder_device"] == dev]


def link(elder, cg, member="Papa", scopes=("doses", "vitals", "sos"), name="Rahul"):
    code = client.post("/api/caregiver/invite", headers=H(elder), json={"member": member, "elder_name": "Ramesh", "scopes": list(scopes)}).json()["code"]
    r = client.post("/api/caregiver/accept", headers=H(cg), json={"code": code, "name": name, "relation": "son"})
    assert r.status_code == 200, r.text
    return r.json()["link_id"]


# ---- the words: no action from a sentence that doesn't mean it ----
@pytest.mark.parametrize("text", [
    "dawa le lijiye", "दवा ले लीजिए", "kya maine dawa le li", "abandoned", "kab leni hai", "goli lena hai kya", "मैंने दवा ले ली?",
])
def test_not_taken(text):
    assert not voice.is_taken(text), text


@pytest.mark.parametrize("text", ["maine dawa le li", "dawa le li", "मैंने दवा ले ली", "ले ली", "I took my medicine", "taken", "kha li"])
def test_taken(text):
    assert voice.is_taken(text), text


@pytest.mark.parametrize("text", ["betadine kitne ki hai", "Betnovate cream", "familycare tablet", "समय पर दवा"])
def test_not_family(text):
    assert not voice.is_family(text), text


@pytest.mark.parametrize("text", ["beta ko bulao", "बेटे को बुलाओ", "call my family", "बेटी से बात करनी है", "parivar ko batao"])
def test_family(text):
    assert voice.is_family(text), text


@pytest.mark.parametrize("text,want", [
    ("Dolo 650 kitne ki hai", {}), ("telma 40 kis liye", {}), ("batch AT25-0938A", {}), ("BP ki dawa", {}),
    ("BP 120", {}), ("bp 120/80", {"bp_sys": 120, "bp_dia": 80}), ("temperature 98.6", {"temp_c": 37.0}),
    ("oxygen 95 pulse 88", {"spo2": 95, "pulse": 88}), ("मेरा बीपी 150/95 है", {"bp_sys": 150, "bp_dia": 95}),
])
def test_vitals_parsing(text, want):
    assert voice.vitals_in(text) == want


def test_impossible_reading_is_refused_not_saved():
    n = main.conn.execute("SELECT COUNT(*) FROM vitals WHERE device = 'h-imp'").fetchone()[0]
    r = client.post("/api/dadi/chat", headers=H("h-imp"), json={"text": "BP 400/300", "lang": "en"}).json()
    assert r["kind"] == "help" and "again" in r["say"]
    assert main.conn.execute("SELECT COUNT(*) FROM vitals WHERE device = 'h-imp'").fetchone()[0] == n


def test_emergency_beats_every_other_intent():
    for t in ("saans nahi aa rahi, dawa le li", "chest pain, BP 190/120", "बेहोश हो गए, बेटे को बुलाओ"):
        assert client.post("/api/dadi/chat", headers=H("h-em"), json={"text": t}).json()["kind"] == "emergency", t


def test_empty_and_huge_messages():
    assert client.post("/api/dadi/chat", headers=H("h-big"), json={"text": "   "}).status_code == 400
    r = client.post("/api/dadi/chat", headers=H("h-big"), json={"text": "a" * 5000})
    assert r.status_code == 200
    assert len(client.get("/api/dadi/history", headers=H("h-big")).json()[-2]["text"]) == 300
    assert client.post("/api/dadi/chat", json={"text": "hi"}).status_code == 401  # no session


# ---- the clock: midnight must not invent missed doses ----
def test_just_after_midnight_nothing_is_missed():
    dev = "h-midnight"
    plan(dev)
    link(dev, "h-midnight-cg")
    at = datetime.now().replace(hour=0, minute=30)
    assert mine(dev, at) == []


def test_late_evening_can_still_tick_the_night_dose():
    dev = "h-late"
    plan(dev, member="Me")
    r = main._mark_taken_device(dev, "Me", datetime.now().replace(hour=23, minute=40))
    assert r and r["slot"] == "night"


def test_missed_after_an_hour_not_before():
    dev = "h-hour"
    plan(dev)
    link(dev, "h-hour-cg")
    day = datetime.now()
    assert not mine(dev, day.replace(hour=8, minute=59))   # 08:00 dose, 59 min late
    assert [d["slot"] for d in mine(dev, day.replace(hour=9, minute=1))] == ["morning"]
    assert not mine(dev, day.replace(hour=9, minute=2))   # once


def test_taken_dose_is_never_reported_missed():
    dev = "h-taken"
    plan(dev)
    link(dev, "h-taken-cg")
    mid = main.conn.execute("SELECT m.id FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ?", (dev,)).fetchone()[0]
    client.post("/api/care/doses", headers=H(dev), json={"med_id": mid, "slot": "morning"})
    assert not mine(dev, datetime.now().replace(hour=10, minute=0))


def test_course_finished_and_as_needed_meds_never_count():
    dev = "h-course"
    old = (datetime.now().date() - timedelta(days=20)).isoformat()
    plan(dev, start=old, days=5)
    client.post("/api/care/plans", headers=H(dev), json={"member": "Papa", "medicines": [{"name": "Dolo", "as_needed": True, "morning": 1}]})
    lid = link(dev, "h-course-cg")
    d = client.get(f"/api/caregiver/elder/{lid}", headers=H("h-course-cg")).json()
    assert d["doses"]["today"] == [] and d["doses"]["adherence"] is None


# ---- the people: consent boundaries ----
def test_scopes_are_enforced_server_side():
    dev = "h-scope"
    plan(dev)
    client.post("/api/care/vitals", headers=H(dev), json={"member": "Papa", "bp_sys": 190, "bp_dia": 120})
    lid = link(dev, "h-scope-cg", scopes=("sos",))
    d = client.get(f"/api/caregiver/elder/{lid}", headers=H("h-scope-cg")).json()
    assert d["doses"] is None and d["vitals"] is None
    # An urgent reading is not sent to a caregiver who may not see vitals.
    r = client.post("/api/care/vitals", headers=H(dev), json={"member": "Papa", "bp_sys": 195, "bp_dia": 125}).json()
    assert r["level"] == "urgent" and r.get("told", []) == []


def test_other_family_members_stay_private():
    dev = "h-member"
    plan(dev, member="Papa")
    plan(dev, member="Maa")
    lid = link(dev, "h-member-cg", member="Papa")
    names = {m["name"] for m in client.get(f"/api/caregiver/elder/{lid}", headers=H("h-member-cg")).json()["doses"]["medicines"]}
    assert names == {"Telma 40"}
    client.post("/api/care/vitals", headers=H(dev), json={"member": "Maa", "bp_sys": 200, "bp_dia": 130})
    v = client.get(f"/api/caregiver/elder/{lid}", headers=H("h-member-cg")).json()["vitals"]
    assert all(x["bp_sys"] != 200 for x in v["history"])


def test_unknown_scopes_ignored_and_bad_codes_rejected():
    r = client.post("/api/caregiver/invite", headers=H("h-x"), json={"scopes": ["everything", "doses", "doses"]}).json()
    assert r["scopes"] == ["doses"]
    for bad in ("", "ZZZZZZ", "' OR 1=1 --", "a" * 200):
        assert client.post("/api/caregiver/accept", headers=H("h-y"), json={"code": bad, "name": "X"}).status_code in (400, 404)
    assert client.post("/api/caregiver/accept", headers=H("h-y"), json={"code": r["code"], "name": "   "}).status_code == 400


def test_expired_code():
    r = client.post("/api/caregiver/invite", headers=H("h-exp"), json={"scopes": ["doses"]}).json()
    main.conn.execute("UPDATE care_invites SET expires_at = ? WHERE code = ?", ((datetime.now() - timedelta(days=3)).isoformat() + "+00:00", r["code"]))
    assert client.post("/api/caregiver/accept", headers=H("h-exp-cg"), json={"code": r["code"], "name": "R"}).status_code == 400


def test_revoked_caregiver_loses_everything():
    dev = "h-rev"
    plan(dev)
    lid = link(dev, "h-rev-cg")
    client.delete(f"/api/caregiver/links/{lid}", headers=H("h-rev-cg"))
    assert client.get(f"/api/caregiver/elder/{lid}", headers=H("h-rev-cg")).status_code == 400
    assert client.post(f"/api/caregiver/elder/{lid}/nudge", headers=H("h-rev-cg"), json={}).status_code == 400
    assert not mine(dev, datetime.now().replace(hour=23, minute=59))
    assert client.delete(f"/api/caregiver/links/{lid}", headers=H(dev)).status_code == 400
    assert client.get("/api/caregiver/access", headers=H(dev)).json()[0]["action"] == "revoked"


def test_reaccepting_replaces_not_duplicates():
    dev = "h-dup"
    link(dev, "h-dup-cg", scopes=("doses",))
    link(dev, "h-dup-cg", scopes=("vitals",))
    w = client.get("/api/caregiver/links", headers=H("h-dup-cg")).json()["watching"]
    assert len(w) == 1 and w[0]["scopes"] == ["vitals"]


def test_two_caregivers_both_alerted_and_nudges_rate_limited():
    dev = "h-two"
    plan(dev)
    a, _ = link(dev, "h-two-a", name="Rahul"), link(dev, "h-two-b", name="Priya")
    r = client.post("/api/dadi/chat", headers=H(dev), json={"text": "beta ko bulao", "member": "Papa"}).json()
    assert sorted(r["data"]["told"]) == ["Priya", "Rahul"]
    codes = [client.post(f"/api/caregiver/elder/{a}/nudge", headers=H("h-two-a"), json={"text": "hi"}).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]


def test_view_log_is_throttled():
    dev = "h-log"
    lid = link(dev, "h-log-cg")
    for _ in range(5):
        client.get(f"/api/caregiver/elder/{lid}", headers=H("h-log-cg"))
    assert [e["action"] for e in client.get("/api/caregiver/access", headers=H(dev)).json()].count("viewed") == 1


def test_sos_reaches_caregiver_and_is_labelled():
    dev = "h-sos"
    link(dev, "h-sos-cg", member="Me")
    r = client.post("/api/sos", headers=H(dev), json={"member": "Me", "lat": 28.6, "lng": 77.2}).json()
    cg = [d for d in r["deliveries"] if d["name"] == "Rahul"]
    assert cg and cg[0]["status"] == "caregiver"


def test_login_merge_keeps_links_on_both_sides():
    lid = link("h-merge-elder", "h-merge-cg")
    auth.merge(main.conn, "h-merge-cg", "h-merge-account")
    assert client.get(f"/api/caregiver/elder/{lid}", headers=H("h-merge-account")).status_code == 200


# ---- Dadi chat talks for the right person ----
def test_chat_uses_the_member_that_has_a_caregiver():
    dev = "h-who"
    plan(dev, member="Papa")
    link(dev, "h-who-cg", member="Papa")
    assert main.default_member(dev) == "Papa"
    assert main.default_member("h-nobody") == "Me"


# ---- Telegram ----
def test_telegram_ignores_junk_updates():
    for u in ({}, {"message": {}}, {"message": {"chat": {"id": 1}}}, {"callback_query": {}}, {"message": {"chat": {"id": 1}, "photo": []}}):
        assert main.telegram_handle(u) is None
    assert "Connect Telegram" in main.telegram_handle({"message": {"chat": {"id": 5}, "text": "/start"}})
    assert "Connect Telegram" in main.telegram_handle({"message": {"chat": {"id": 5}, "text": "/start not-a-code"}})


def test_telegram_caregiver_chat_cannot_talk_for_the_elder():
    code = main.telegram.link_code(main.conn, "h-tg-cg", "caregiver")
    main.telegram_handle({"message": {"chat": {"id": 4242}, "text": f"/start {code}"}})
    assert "only receives alerts" in main.telegram_handle({"message": {"chat": {"id": 4242}, "text": "dawa le li"}})


def test_telegram_buttons_round_trip():
    code = main.telegram.link_code(main.conn, "h-tg-elder")
    main.telegram_handle({"message": {"chat": {"id": 5151}, "text": f"/start {code}"}})
    for b in main.TG_BUTTONS:
        main.telegram_handle({"message": {"chat": {"id": 5151}, "text": b}})
    kinds = [m["kind"] for m in client.get("/api/dadi/history", headers=H("h-tg-elder")).json() if m["role"] == "kincare"]
    assert kinds == ["nothing_due", "doses", "family_none"]


def test_webhook_rejects_without_secret():
    assert client.post("/api/telegram/webhook", json={}).status_code == 401
