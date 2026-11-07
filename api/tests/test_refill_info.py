import json
import os
import tempfile
from datetime import date
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import care  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import medinfo  # noqa: E402
import prices  # noqa: E402
import push  # noqa: E402
import stores  # noqa: E402
from ingest.medicines import maker_key, parse_pack, salt_part  # noqa: E402

client = TestClient(main.app)
H = auth_as("refill-test-device")

ROWS = [
    (9101, "Glycomet 500 Tablet", 21.0, "USV Ltd", "strip of 10 tablets", "Metformin (500mg)"),
    (9102, "Metfo Clean 500 Tablet", 5.0, "Cleanpharma Pvt Ltd", "strip of 10 tablets", "Metformin (500mg)"),
    (9103, "Crocin Advance Tablet", 20.0, "GSK", "strip of 15 tablets", "Paracetamol (500mg)"),
    (9104, "Crocin 1000mg Tablet", 41.0, "GSK", "strip of 10 tablets", "Paracetamol (1000mg)"),
]


def setup_module():
    main.conn.execute("DELETE FROM medicines WHERE id IN (9101, 9102, 9103, 9104)")
    for mid, name, price, maker, pack, comp in ROWS:
        form, qty, unit = parse_pack(pack)
        main.conn.execute("INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (mid, name, name.lower(), price, maker, maker_key(maker), pack, salt_part(comp), salt_part(comp), form, qty, unit, price / qty))
    main.conn.execute("""INSERT INTO alerts (source, category, product_name, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                         VALUES ('cdsco_nsq', 'nsq', 'Metformin Hydrochloride Tablets IP 500 mg', 'MF77', 'MF77', 'M/s. Other Labs', 'Dissolution', '2026-03', 'https://x')""")
    # Cached FDA label, so the test never goes online.
    main.conn.execute("CREATE TABLE IF NOT EXISTS fda_info (generic TEXT PRIMARY KEY, body TEXT)")
    main.conn.execute("INSERT OR REPLACE INTO fda_info VALUES ('metformin hydrochloride', ?)",
                      (json.dumps({"uses": "Lowers blood sugar in type 2 diabetes.", "label_name": "METFORMIN HYDROCHLORIDE"}),))
    main.conn.commit()
    prices._maker_alerts = None


def test_refill_status_rules():
    med = {"morning": 1, "noon": 0, "night": 1, "days": None, "as_needed": 0}
    r = care.refill_status(med, "2026-10-01", 10, 6, date(2026, 10, 3))
    assert r["left"] == 4 and r["days_left"] == 2.0 and r["low"]
    assert not care.refill_status(med, "2026-10-01", 30, 6, date(2026, 10, 3))["low"]
    # Course ends tomorrow and 4 tablets cover it: no refill reminder.
    short = {**med, "days": 3}
    assert not care.refill_status(short, "2026-10-01", 10, 6, date(2026, 10, 3))["low"]
    assert care.refill_status({**med, "as_needed": 1}, "2026-10-01", 10, 0, date(2026, 10, 3)) is None


def test_purchase_counts_tablets_and_refill_adds_up():
    plan = client.post("/api/care/plans", headers=H, json={"member": "Papa", "advice": [], "medicines": [
        {"name": "Glycomet 500", "strength": "500 mg", "morning": 1, "night": 1}]}).json()
    mid = main.conn.execute("SELECT id FROM plan_meds WHERE plan_id = ?", (plan["id"],)).fetchone()[0]
    client.post("/api/care/purchase", headers=H, json={"med_id": mid, "batch": "OK123"})
    r = next(x for x in client.get("/api/care/refills", headers=H).json() if x["med_id"] == mid)
    assert r["left"] == 10 and r["per_day"] == 2  # qty taken from the pack size in the medicine dataset
    for slot in ("morning", "night"):
        client.post("/api/care/doses", headers=H, json={"med_id": mid, "slot": slot})
    r = next(x for x in client.get("/api/care/refills", headers=H).json() if x["med_id"] == mid)
    assert r["left"] == 8 and not r["low"]
    client.post("/api/care/purchase", headers=H, json={"med_id": mid, "batch": "OK124", "qty": 30})
    r = next(x for x in client.get("/api/care/refills", headers=H).json() if x["med_id"] == mid)
    assert r["left"] == 38  # 8 still at home + 30 new
    assert client.post("/api/care/purchase", headers=H, json={"med_id": mid, "batch": "X", "qty": 0}).status_code == 400


def test_refill_reminder_once_with_cheaper_clean_brand():
    plan = client.post("/api/care/plans", headers=H, json={"member": "Maa", "advice": [], "medicines": [
        {"name": "Glycomet 500", "strength": "500 mg", "morning": 1, "night": 1}]}).json()
    mid = main.conn.execute("SELECT id FROM plan_meds WHERE plan_id = ?", (plan["id"],)).fetchone()[0]
    client.post("/api/care/purchase", headers=H, json={"med_id": mid, "batch": "OK200", "qty": 4, "phone": "9876543210", "language": "en"})
    main.send_due_reminders()
    main.send_due_reminders()
    notes = [r["message"] for r in main.conn.execute("SELECT message FROM notifications WHERE batch = 'OK200'") if "left" in r["message"]]
    assert len(notes) == 1 and "only 4 tablets" in notes[0] and "Metfo Clean 500 Tablet" in notes[0]


def test_medicine_info_page_data():
    r = client.get("/api/medicines/9101/info").json()
    assert r["salts"][0]["name"] == "metformin" and r["salts"][0]["label_name"] == "metformin hydrochloride"
    assert r["salts"][0]["label"]["uses"].startswith("Lowers blood sugar")
    assert r["alerts"]["total"] >= 1 and r["alerts"]["recent"][0]["batch_no"] == "MF77"
    assert r["price"]["cheapest_clean"]["name"] == "Metfo Clean 500 Tablet" and r["price"]["rank"] == 2
    assert client.get("/api/medicines/1/info").status_code == 404
    assert medinfo.salt_names("telmisartan (40mg) + hydrochlorothiazide (12.5mg)") == ["telmisartan", "hydrochlorothiazide"]


def test_push_subscription_and_validation():
    key = client.get("/api/push/key", headers=H).json()
    assert key["subscribed"] is False and (key["key"] is None or len(key["key"]) > 80)
    bad = client.post("/api/push/subscribe", headers=H, json={"endpoint": "http://evil", "keys": {}})
    assert bad.status_code in (400, 503)
    if push.ready():
        ok = client.post("/api/push/subscribe", headers=H, json={"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}})
        assert ok.status_code == 200 and client.get("/api/push/key", headers=H).json()["subscribed"] is True
        client.delete("/api/push/subscribe", headers=H)
        assert client.get("/api/push/key", headers=H).json()["subscribed"] is False


def test_store_parse_sorts_by_distance_and_dedupes():
    els = [
        {"lat": 28.70, "lon": 77.10, "tags": {"name": "Far Kendra"}},
        {"center": {"lat": 28.6140, "lon": 77.2091}, "tags": {"name": "Pradhan Mantri Bhartiya Janaushadhi Kendra", "addr:city": "New Delhi"}},
        {"lat": 28.61401, "lon": 77.20911, "tags": {"name": "duplicate"}},
        {"tags": {"name": "no location"}},
    ]
    s = stores.parse(els, 28.6139, 77.2090)
    assert [x["name"] for x in s] == ["Pradhan Mantri Bhartiya Janaushadhi Kendra", "Far Kendra"]
    assert s[0]["km"] < 0.1 and s[0]["address"] == "New Delhi"
    assert client.get("/api/stores/janaushadhi", params={"lat": 51.5, "lon": -0.1}).status_code == 422  # outside India


def test_prescription_brand_matches_by_stem_and_strength():
    # Prescriptions say "Crocin 500"; the dataset calls it "Crocin Advance Tablet" (paracetamol 500mg).
    r, est = prices.match_plan_med(main.conn, "Crocin 500", "500 mg")
    assert r["name"] == "Crocin Advance Tablet" and not est
    assert prices.match_plan_med(main.conn, "Crocin 1000", "1000 mg")[0]["name"] == "Crocin 1000mg Tablet"
