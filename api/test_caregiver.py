import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import voice  # noqa: E402

client = TestClient(main.app)
ELDER = auth_as("cg-elder")
SON = auth_as("cg-son")
STRANGER = auth_as("cg-stranger")


def _plan(headers, member="Papa"):
    # Morning, noon and night every day, started yesterday: today has doses both past and (maybe) still to come.
    start = (datetime.now().date() - timedelta(days=1)).isoformat()
    main.conn.execute("DELETE FROM plans WHERE device = ?", (headers["X-Device-Id"],))
    r = client.post("/api/care/plans", headers=headers, json={"member": member, "start_date": start, "advice": [],
                                                             "medicines": [{"name": "Telma 40", "strength": "40 mg", "morning": 1, "noon": 1, "night": 1}]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _link(scopes=("doses", "vitals", "sos")):
    inv = client.post("/api/caregiver/invite", headers=ELDER, json={"member": "Papa", "elder_name": "Ramesh", "scopes": list(scopes)}).json()
    assert len(inv["code"]) == 6 and inv["url"].endswith(inv["code"])
    prev = client.get(f"/api/caregiver/invite/{inv['code'].lower()}").json()
    assert prev["elder_name"] == "Ramesh" and [s["key"] for s in prev["scopes"]] == list(scopes)
    r = client.post("/api/caregiver/accept", headers=SON, json={"code": inv["code"], "name": "Rahul", "relation": "son"}).json()
    return r["link_id"], inv["code"]


def test_voice_parsers():
    assert voice.vitals_in("BP 140/90 hai") == {"bp_sys": 140, "bp_dia": 90}
    assert voice.vitals_in("बीपी १३० बटा ८५, नब्ज 72") == {"bp_sys": 130, "bp_dia": 85, "pulse": 72}
    assert voice.vitals_in("bukhar 101")["temp_c"] == 38.3  # Fahrenheit read as such
    assert voice.is_taken("maine dawa le li") and voice.is_taken("मैंने दवा खा ली")
    assert not voice.is_taken("kya maine dawa le li?")
    assert voice.is_family("beta ko bulao") and not voice.is_family("dolo kitne ki hai")


def test_invite_needs_a_scope_and_codes_are_single_use():
    assert client.post("/api/caregiver/invite", headers=ELDER, json={"scopes": []}).status_code == 400
    inv = client.post("/api/caregiver/invite", headers=ELDER, json={"scopes": ["doses"]}).json()
    assert client.post("/api/caregiver/accept", headers=ELDER, json={"code": inv["code"], "name": "Me"}).status_code == 400  # not on the elder's own phone
    assert client.post("/api/caregiver/accept", headers=SON, json={"code": inv["code"], "name": "Rahul"}).status_code == 200
    assert client.post("/api/caregiver/accept", headers=STRANGER, json={"code": inv["code"], "name": "X"}).status_code == 400


def test_caregiver_sees_only_consented_scopes_and_is_logged():
    _plan(ELDER)
    client.post("/api/care/vitals", headers=ELDER, json={"member": "Papa", "bp_sys": 128, "bp_dia": 82})
    lid, _ = _link(("doses",))
    d = client.get(f"/api/caregiver/elder/{lid}", headers=SON).json()
    assert d["vitals"] is None and d["sos"] is None  # not shared: null, not empty
    assert d["doses"]["medicines"][0]["name"] == "Telma 40"
    yesterday = d["doses"]["week"][-2]
    assert yesterday["due"] == 3 and yesterday["taken"] == 0 and len(yesterday["missed"]) == 3
    assert client.get(f"/api/caregiver/elder/{lid}", headers=STRANGER).status_code == 400
    log = client.get("/api/caregiver/access", headers=ELDER).json()
    assert {"linked", "viewed"} <= {e["action"] for e in log} and log[0]["caregiver_name"] == "Rahul"


def test_revoke_is_immediate_from_either_side():
    lid, _ = _link()
    assert client.delete(f"/api/caregiver/links/{lid}", headers=STRANGER).status_code == 400
    assert client.delete(f"/api/caregiver/links/{lid}", headers=ELDER).json()["by"] == "elder"
    assert client.get(f"/api/caregiver/elder/{lid}", headers=SON).status_code == 400
    assert lid not in [l["id"] for l in client.get("/api/caregiver/links", headers=SON).json()["watching"]]


def test_missed_dose_alerts_once_and_nudge_reaches_dadi_chat(monkeypatch):
    import care

    monkeypatch.setattr(care, "SLOTS", [("morning", "00:00"), ("noon", "00:01"), ("night", "00:02")])  # all overdue, whatever the clock says
    monkeypatch.setattr(main.caregiver_mod, "MISSED_AFTER", timedelta(0))
    _plan(ELDER)
    lid, _ = _link()
    main.conn.execute("DELETE FROM care_alerts_sent")
    first = main.send_caregiver_alerts()
    assert first >= 1 and main.send_caregiver_alerts() == 0  # never the same alert twice
    r = client.post(f"/api/caregiver/elder/{lid}/nudge", headers=SON, json={"text": "Papa, Telma le lo"})
    assert r.json()["in_app"]
    hist = client.get("/api/dadi/history", headers=ELDER).json()
    assert hist[-1]["role"] == "family" and "Telma le lo" in hist[-1]["text"]


def test_dadi_chat_ticks_dose_logs_vitals_and_calls_family(monkeypatch):
    import care

    monkeypatch.setattr(care, "SLOTS", [("morning", "00:00"), ("noon", "00:01"), ("night", "00:02")])
    _plan(ELDER)
    _link()
    r = client.post("/api/dadi/chat", headers=ELDER, json={"text": "maine dawa le li", "member": "Papa"}).json()
    assert r["kind"] == "taken" and r["data"]["dose"]["name"] == "Telma 40"
    v = client.post("/api/dadi/chat", headers=ELDER, json={"text": "BP 190/120", "member": "Papa"}).json()
    assert v["kind"] == "vitals_urgent" and "Rahul" in v["say"]
    f = client.post("/api/dadi/chat", headers=ELDER, json={"text": "beta ko bulao", "member": "Papa", "lang": "en"}).json()
    assert f["kind"] == "family" and f["data"]["told"] == ["Rahul"]
    e = client.post("/api/dadi/chat", headers=ELDER, json={"text": "saans nahi aa rahi, beta ko bulao", "member": "Papa"}).json()
    assert e["kind"] == "emergency" and "108" in e["say"] and "Rahul" in e["data"]["told"]


def test_telegram_start_links_chat_and_messages_reach_the_same_chat():
    code = main.telegram.link_code(main.conn, "cg-tg-elder")
    reply = main.telegram_handle({"message": {"chat": {"id": 777}, "from": {"first_name": "Kamla"}, "text": f"/start {code}"}})
    assert "जुड़ गया" in reply
    assert main.telegram.claim(main.conn, code, 778, None) is None  # one use
    main.telegram_handle({"message": {"chat": {"id": 777}, "text": "namaste"}})
    hist = client.get("/api/dadi/history", headers=auth_as("cg-tg-elder")).json()
    assert [m["channel"] for m in hist] == ["telegram", "telegram"] and hist[1]["kind"] == "hello"
    assert "only receives alerts" in main.telegram_handle({"message": {"chat": {"id": 999}, "text": "hi"}})
