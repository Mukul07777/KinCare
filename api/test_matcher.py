import os
import tempfile
from pathlib import Path

os.environ["KINCARE_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from conftest import ADMIN  # noqa: E402
from testutil import auth_as  # noqa: E402
from matcher import match, normalise_batch, normalise_maker  # noqa: E402

# Rows copied from real CDSCO alerts (Feb 2025 spurious list, Jun 2025 NSQ list).
FIXTURES = [
    ("cdsco_spurious", "spurious", "Telma H (Telmisartan 40mg & Hydrochlorothiazide 12.5mg)", "Telma H", "05240198", "Under Investigation", "2025-02"),
    ("cdsco_nsq", "nsq", "Dexamethasone Sodium Phosphate Injection I.P. (Dexacos)", "Dexacos", "P24L220", "Paksons pharmaceuticals Private Limited", "2025-06"),
    ("state_nsq", "nsq", "Paracetamol Tablets IP", "Paracetamol", "KN-101", "Konis Pharmaceuticals Pvt. Ltd.", "2025-05"),
]
for src, cat, prod, brand, batch, maker, month in FIXTURES:
    main.conn.execute(
        """INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (src, cat, prod, brand, batch, normalise_batch(batch), maker, "test", month, "https://cdsco.gov.in/x.pdf"),
    )
main.conn.commit()
client = TestClient(main.app)
HDR = auth_as("test-device", roles=("pharmacist",))


def test_normalise_batch():
    assert normalise_batch(" p24-l/220 ") == "P24L220"


def test_normalise_maker():
    assert normalise_maker("M/s Paksons Pharmaceuticals Pvt. Ltd.") == "paksons pharmaceuticals"
    # Distinguishing words survive, so different firms stay different.
    assert normalise_maker("Apple Formulations Pvt Ltd") != normalise_maker("Apple Remedies Pvt Ltd")


def test_unknown_batch_never_claims_safety():
    body = client.get("/api/check", params={"batch": "NOTREAL123"}).text.lower()
    assert "safe" not in body


def test_manufacturer_history():
    r = client.get("/api/manufacturer", params={"name": "Paksons Pharmaceuticals Pvt Ltd"}).json()
    assert r["total"] == 1 and "Paksons pharmaceuticals Private Limited" in r["variants"]
    # Regression: a shared industry word must not merge different firms.
    assert "Konis Pharmaceuticals Pvt. Ltd." not in r["variants"]


def test_near_miss_batch_never_matches():
    assert main.candidates("05240199") == []


def test_spurious_unknown_maker_uses_brand():
    hits = match(main.candidates("05240198"), "05240198", maker="Glenmark", brand="Telma H")
    assert hits[0]["score"]["level"] == "strong" and hits[0]["score"]["maker"] is None


def test_wrong_maker_is_only_possible():
    hits = match(main.candidates("P24L220"), "P24L220", maker="Totally Different Co")
    assert hits[0]["score"]["level"] == "possible"


def test_check_endpoint():
    r = client.get("/api/check", params={"batch": "05240198", "brand": "Telma H"}).json()
    assert r["verdict"] == "alert_found"
    assert [s["status"] for s in r["sources"] if s["id"] == "cdsco_spurious"] == ["match"]
    assert client.get("/api/check", params={"batch": "ZZZ"}).json()["verdict"] == "no_alert_found"


def test_inventory_check():
    r = client.post("/api/inventory/check", json=[
        {"product": "Telma H", "batch": "0524 0198", "qty": 40},
        {"product": "Amlodac 5", "batch": "AMD-7781", "qty": 12},
    ]).json()
    assert r["total"] == 2 and r["flagged"] == 1


def test_alerts_search_and_stats():
    assert client.get("/api/alerts", params={"q": "dexacos"}).json()["total"] == 1
    assert client.get("/api/stats").json()["total"] == 3


def test_watchlist_roundtrip():
    assert client.post("/api/watchlist", json={"batch": "05240198", "brand": "Telma H"}, headers=HDR).json()["verdict"] == "alert_found"
    assert len(client.get("/api/watchlist", headers=HDR).json()) == 1
    assert client.post("/api/watchlist/recheck", headers=HDR).json()["changed"] == []
    client.delete("/api/watchlist/05240198", headers=HDR)
    assert client.get("/api/watchlist", headers=HDR).json() == []
    assert client.get("/api/watchlist").status_code == 401  # no session, no data


def test_pharmacy_state_roundtrip():
    client.put("/api/pharmacy/state", json={"tasks": [1]}, headers=HDR)
    assert client.get("/api/pharmacy/state", headers=HDR).json() == {"tasks": [1]}


def test_scan_ocr():
    img = Path(__file__).parent / "tests" / "fixtures" / "strip_telma.png"
    r = client.post("/api/scan", files={"image": ("s.png", img.read_bytes(), "image/png")}).json()
    assert r["fields"]["batch"] == "05240198" and r["fields"]["brand"] == "Telma H"


def test_ask_regulator():
    r = client.get("/api/ask", params={"q": "spurious drugs in 2025"}).json()
    assert r["total"] == 1 and r["citations"][0]["batch_no"] == "05240198"
    r = client.get("/api/ask", params={"q": "is batch P24L220 flagged?"}).json()
    assert r["total"] == 1 and "batch P24L220" in r["understood"]
    assert client.get("/api/ask", params={"q": "paracetamol failures in 2025"}).json()["total"] == 1
    r = client.get("/api/ask", params={"q": "paracetamol in 2019"}).json()
    assert r["total"] == 0 and "not that it was tested and passed" in r["answer"]


def test_hindi_messages_never_say_safe():
    import notify

    a = {"category": "spurious", "brand": "Telma H", "product_name": "Telma H", "alert_month": "2025-02", "alert_url": "https://cdsco.gov.in/x.pdf"}
    for lang in ("hi", "en"):
        text = notify.whatsapp_text(a, "05240198", "Ravi", lang) + notify.voice_script(a, "05240198", "Ravi", lang)
        assert "05240198" in text.replace(" ", "") and "safe" not in text.lower()
    assert "नकली" in notify.whatsapp_text(a, "05240198", None, "hi")


def test_pharmacy_sales_notify():
    client.put("/api/sales", headers=HDR, json=[
        {"pharmacy": "Shree Medicos", "customer": "Ravi", "phone": "9876543210", "batch": "P24L220", "product": "Dexacos"},
        {"customer": "Asha", "phone": "9876500000", "batch": "CLEAN1"},
    ])
    r = client.post("/api/pharmacy/notify", params={"batch": "P24L220"}, headers=HDR).json()
    assert r["buyers"] == 1 and {n["channel"] for n in r["notifications"]} == {"whatsapp", "voice"}
    assert all(n["status"] == "outbox" for n in r["notifications"])  # no Twilio keys in tests


def test_recall_engine_end_to_end(monkeypatch):
    import time as _t

    import agents
    import recall
    from ingest import portal

    monkeypatch.setattr(agents, "run_source", lambda src, emit: [])
    monkeypatch.setattr(portal, "load", lambda **kw: None)
    rid = client.post("/api/recall/run", headers=HDR, json={"scope": "latest", "demo_phone": "9811122233", "demo_name": "Judge"}).json()["run_id"]
    for _ in range(50):
        types = [r[0] for r in main.conn.execute("SELECT type FROM events WHERE run_id = ?", (rid,))]
        if "run_complete" in types:
            break
        _t.sleep(0.1)
    assert {"run_started", "agent_done", "list_ready", "match", "notified", "run_complete"} <= set(types)
    notes = client.get("/api/notifications", params={"run_id": rid}, headers=ADMIN).json()
    assert {n["channel"] for n in notes} == {"whatsapp", "voice"}
    # Both the demo contact and the pharmacy customer holding the same flagged batch are reached.
    assert {"+919811122233", "+919876543210"} <= {n["phone"] for n in notes}


def test_failure_explainer_and_insights():
    import insights

    f = insights.failures_of("Assay of Dextrose and Dissolution")
    assert [x["key"] for x in f] == ["assay", "dissolution"] and f[0]["hi"]
    assert insights.failures_of("Diethylene glycol detected")[0]["severity"] == "critical"
    assert insights.failures_of("Does not conform", "spurious")[0]["key"] == "spurious"
    assert insights.state_of("RDTL, Guwahati") == "Assam" and insights.group_of("Telma H (Telmisartan 40mg)") == "Heart & BP"
    r = client.get("/api/check", params={"batch": "05240198", "brand": "Telma H"}).json()
    assert r["matches"][0]["explain"][0]["key"] == "spurious"
    assert client.get("/api/insights").json()["total"] == 3


def test_bill_scan_checks_every_batch():
    img = Path(__file__).parent / "tests" / "fixtures" / "bill_shree.png"
    r = client.post("/api/scan/bill", files={"image": ("b.png", img.read_bytes(), "image/png")}).json()
    batches = [i["batch"] for i in r["items"]]
    assert {"BDS25003", "05240198", "AML24017", "MHPL-733"} <= set(batches)
    assert r["flagged"] == 1 and next(i for i in r["items"] if i["batch"] == "05240198")["match"]  # only Telma H is in the test DB


def test_checkin_flow_and_triage():
    import checkin

    assert checkin.triage("unwell", ["breathlessness"], None, None) == "urgent"
    assert checkin.triage("ok", [], 185, 95) == "urgent"
    assert checkin.triage("unwell", ["headache"], 150, 90) == "review"
    assert checkin.triage("ok", [], 128, 82) == "ok"

    client.put("/api/sales", headers=HDR, json=[{"customer": "Ravi Kumar", "phone": "9876543210", "batch": "P24L220"}])
    r = client.post("/api/pharmacy/notify", params={"batch": "P24L220"}, headers=HDR).json()
    wa = next(n for n in r["notifications"] if n["channel"] == "whatsapp")["message"]
    token = wa.split("checkin?t=")[1].split()[0]
    info = client.get(f"/api/checkin/{token}").json()
    assert info["batch"] == "P24L220" and not info["responded"] and len(info["symptoms"]) >= 8
    assert client.post(f"/api/checkin/{token}", json={"feeling": "unwell", "symptoms": ["dizziness", "chest_pain"], "bp_sys": 170, "bp_dia": 100}).json()["triage"] == "urgent"
    assert client.post(f"/api/checkin/{token}", json={"feeling": "ok", "bp_sys": 400}).status_code == 400
    q = client.get("/api/checkins").json()
    assert q["urgent"] >= 1 and q["items"][0]["triage"] == "urgent"
    csv_text = client.get("/api/checkins/pvpi.csv").text
    assert "Chest pain" in csv_text and "RK" in csv_text
    assert client.get("/api/checkin/nope").status_code == 404


def test_watchlist_member_and_expiry():
    client.post("/api/watchlist", headers=HDR, json={"batch": "AML24017", "brand": "Amlodipine", "member": "Maa", "expiry": "08/2027"})
    w = next(i for i in client.get("/api/watchlist", headers=HDR).json() if i["batch"] == "AML24017")
    assert w["member"] == "Maa" and w["expiry"] == "08/2027"


def test_care_vitals_never_suggest_medicine():
    for v in ({"temp_c": 38.6}, {"temp_c": 40.5}, {"spo2": 90}, {"bp_sys": 150, "bp_dia": 95}, {"temp_c": 36.8}):
        r = client.post("/api/care/vitals", headers=HDR, json=v).json()
        text = (r["en"] + " ".join(r["reasons"])).lower()
        assert not any(w in text for w in ("paracetamol", "tablet", "dose", "mg")), text
    assert client.post("/api/care/vitals", headers=HDR, json={"temp_c": 40.5}).json()["level"] == "urgent"
    assert client.post("/api/care/vitals", headers=HDR, json={"temp_c": 38.4}).json()["level"] == "doctor"
    assert client.post("/api/care/vitals", headers=HDR, json={"temp_c": 55}).status_code == 400
    assert len(client.get("/api/care/vitals", headers=HDR).json()) >= 7


def test_prescription_to_reminders_and_report():
    img = Path(__file__).parent / "tests" / "fixtures" / "prescription.png"
    rx = client.post("/api/care/prescription/scan", files={"image": ("rx.png", img.read_bytes(), "image/png")}).json()
    names = [m["name"] for m in rx["medicines"]]
    assert names == ["Dolo", "Pantocid", "Ascoril", "Cetzine"] and "Rest" in [a["en"] for a in rx["advice"]]
    plan = client.post("/api/care/plans", headers=HDR, json={"member": "Maa", "doctor": "Dr. A. Sharma",
        "advice": [a["en"] for a in rx["advice"]], "medicines": rx["medicines"]}).json()
    today = client.get("/api/care/today", headers=HDR).json()
    assert len(today["doses"]) == 7  # Dolo x2, Pantocid x1, Ascoril x3, Cetzine x1
    d = today["doses"][0]
    client.post("/api/care/doses", headers=HDR, json={"med_id": d["med_id"], "slot": d["slot"]})
    rep = client.get("/api/care/report", headers=HDR, params={"member": "Maa"}).json()
    assert sum(a["taken"] for a in rep["adherence"]) == 1 and sum(a["due"] for a in rep["adherence"]) == 7
    assert client.delete(f"/api/care/plans/{plan['id']}", headers=HDR).json()["ok"]


# ---- Early Signal ----
def _report(device, batch, symptoms, city="Delhi"):
    return client.post("/api/reports", json={"batch": batch, "symptoms": symptoms, "city": city}, headers=auth_as(device))


def test_signal_needs_disproportion_not_just_volume():
    main.conn.execute("DELETE FROM reports")
    for i in range(30):  # headaches everywhere: common, not a signal
        _report(f"bg{i}", f"BG{i:04d}", ["headache"])
    for i in range(6):
        _report(f"hit{i}", "SIG2024", ["no_effect", "headache"])
    sig = {s["batch_norm"]: s for s in client.get("/api/signals").json()["signals"]}
    s = sig["SIG2024"]
    flagged = {x["key"]: x["flagged"] for x in s["symptoms"]}
    assert s["level"] == "signal" and s["method"] == "prr"
    assert flagged["no_effect"] and not flagged["headache"]


def test_one_device_cannot_stuff_a_signal():
    main.conn.execute("DELETE FROM reports")
    for _ in range(5):
        _report("same-phone", "STUFF01", ["chest_pain"])
    assert client.get("/api/signals").json()["signals"] == []


def test_red_flag_reports_raise_urgent():
    main.conn.execute("DELETE FROM reports")
    for i, s in enumerate([["chest_pain"], ["fainting"], ["dizziness"]]):
        _report(f"r{i}", "RED777", s)
    s = client.get("/api/signals").json()["signals"][0]
    assert s["level"] == "urgent" and s["red_flag_reports"] == 2


def test_report_rejects_unknown_symptoms():
    assert _report("x", "ABC123", ["made_up"]).status_code == 400


# ---- SOS, billing, admin ----
H = auth_as("sos-dev")


def test_sos_message_has_location_vitals_and_medicines():
    client.post("/api/sos/contacts", json={"name": "Beta", "phone": "98765 43210", "relation": "son"}, headers=H)
    client.post("/api/care/vitals", json={"member": "Papa", "temp_c": 39.4, "spo2": 91}, headers=H)
    r = client.post("/api/sos", json={"member": "Papa", "lat": 28.5459, "lng": 77.2732}, headers=H).json()
    assert "maps.google.com/?q=28.54590,77.27320" in r["message"]
    assert "39.4" in r["message"] and "SpO2 91%" in r["message"]
    d = r["deliveries"][0]
    assert d["phone"] == "+919876543210" and d["link"].startswith("https://wa.me/919876543210")


def test_sos_contact_rejects_bad_phone():
    assert client.post("/api/sos/contacts", json={"name": "x", "phone": "123"}, headers=H).status_code == 400


def test_checkout_without_stripe_key_is_clear_503(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    plans = client.get("/api/billing/plans", headers=H).json()
    assert not plans["ready"] and {p["id"] for p in plans["plans"]} >= {"family", "pharmacy"}
    assert client.post("/api/billing/checkout", json={"plan": "family"}, headers=H).status_code == 503


def test_confirm_rejects_other_devices_session():
    main.conn.execute("INSERT INTO payments (device, plan, session_id, amount, currency) VALUES ('owner', 'family', 'cs_x', 4900, 'inr')")
    assert client.get("/api/billing/confirm?session_id=cs_x", headers=H).status_code == 404


def test_admin_overview_and_token(monkeypatch):
    o = client.get("/api/admin/overview", headers=ADMIN).json()
    assert o["sos_open"] >= 1 and "mrr" in o["payments"]
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"X-Admin-Token": "s3cret"}).status_code == 200


def _plan(dev: str, name: str) -> int:
    h = auth_as(dev)
    client.post("/api/care/plans", headers=h, json={"member": "Dadi", "medicines": [{"name": name, "morning": 1, "noon": 1, "night": 1}]})
    return client.get("/api/care/plans", headers=h).json()[0]["medicines"][0]["id"]


def test_purchase_clean_batch_sets_reminders_once():
    mid = _plan("buyclean0001", "Crocin 500")
    r = client.post("/api/care/purchase", headers=auth_as("buyclean0001"), json={"med_id": mid, "batch": "ZZ999", "phone": "9876543210"}).json()
    assert r["verdict"] == "no_alert_found"
    main.send_due_reminders()
    assert main.send_due_reminders() == 0  # never the same reminder twice


def test_purchase_flagged_batch_sends_alert_not_reminder():
    mid = _plan("buyflag00001", "Telma H")
    r = client.post("/api/care/purchase", headers=auth_as("buyflag00001"), json={"med_id": mid, "batch": "05240198"}).json()
    assert r["verdict"] == "alert_found"


def test_purchase_other_device_forbidden():
    mid = _plan("owner0000001", "Crocin 500")
    assert client.post("/api/care/purchase", headers=auth_as("intruder0001"), json={"med_id": mid, "batch": "X1"}).status_code == 404


def test_interactions_from_cached_label():
    import json

    import interactions

    main.conn.execute("CREATE TABLE IF NOT EXISTS fda_labels (generic TEXT PRIMARY KEY, body TEXT)")
    main.conn.execute("INSERT OR REPLACE INTO fda_labels VALUES ('warfarin', ?)", (json.dumps({"drug_interactions": "Aspirin increases the risk of bleeding."}),))
    main.conn.execute("INSERT OR REPLACE INTO fda_labels VALUES ('aspirin', ?)", (json.dumps({}),))
    r = interactions.check(main.conn, ["Warf 5mg", "Ecosprin 75"])
    assert [(i["a"], i["b"]) for i in r["interactions"]] == [("Warf 5mg", "Ecosprin 75")]


def test_ocr_lookalike_batch_is_only_ever_a_possible_match():
    from matcher.core import lookalike
    alert = {"batch_no": "DOB57480", "manufacturer": "Micro Labs Ltd", "brand": "Dolo-650", "product_name": "Paracetamol Tablets IP"}
    assert match([alert], "DOB57480", "Micro Labs")[0]["score"]["level"] == "strong"
    s = match([alert], "D0B57480", "Micro Labs")[0]["score"]  # OCR read the letter O as a zero
    assert s["level"] == "possible" and s["lookalike"] and s["batch"] == 90
    assert match([alert], "D0B57481") == []                   # a really different batch never matches
    assert lookalike("ds-0B5") == lookalike("DS0B5") == "D5085"


def test_strip_read_with_cut_edges_and_a_repeated_brand():
    import ocr
    L = lambda t, h=10: {"text": t, "conf": 0.9, "height": h, "top": h, "left": 0}
    f = ocr.extract_fields([L("Dolo-650 Dolo-650 Paracetamol TabtetsIP", 40), L("Dolo-650"), L("Dolo-650 FOR 15 TABS"),
                            L("Mfg.Lic.No.:M/600/2012"), L("NO.DOB57480 MAY.2026"), L("XP.APR.2030 M.R.P")])["fields"]
    assert f["batch"] == "DOB57480" and f["expiry"] == "APR.2030" and f["brand"] == "Dolo-650"
    assert ocr.extract_fields([L("Mfg.Lic.No.:M/600/2012"), L("Regd. No. 12345")])["fields"]["batch"] is None
