import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import prices  # noqa: E402
from ingest.medicines import maker_key, parse_pack, salt_part  # noqa: E402

client = TestClient(main.app)
H = auth_as("prices-test-device")

# Rows as they appear in the Indian Medicine Dataset.
ROWS = [
    (9001, "Telmikind 40 Tablet", 98.0, "Mankind Pharma Ltd", "strip of 10 tablets", "Telmisartan (40mg)"),
    (9002, "Telmisoft 40 Tablet", 6.5, "Innovexia Life Sciences Pvt Ltd", "strip of 10 tablets", "Telmisartan (40mg)"),
    (9003, "Telmi Risky 40 Tablet", 4.0, "Riskycorp Pharma Pvt Ltd", "strip of 10 tablets", "Telmisartan (40mg)"),
    (9004, "Telmikind 40 SR Tablet", 1.0, "Mankind Pharma Ltd", "strip of 10 tablet sr", "Telmisartan (40mg)"),
]


def setup_module():
    main.conn.execute("DELETE FROM medicines")
    for mid, name, price, maker, pack, comp in ROWS:
        form, qty, unit = parse_pack(pack)
        main.conn.execute("INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (mid, name, name.lower(), price, maker, maker_key(maker), pack, salt_part(comp), salt_part(comp), form, qty, unit, price / qty))
    main.conn.execute("""INSERT INTO alerts (source, category, product_name, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                         VALUES ('cdsco_nsq', 'nsq', 'Telmisartan Tablets', 'RX1', 'RX1', 'M/s. Riskycorp Pharma Pvt. Ltd.', 'Dissolution', '2026-01', 'https://x')""")
    main.conn.commit()
    prices._maker_alerts = None


def test_pack_and_salt_normalising():
    assert parse_pack("strip of 10 tablets") == ("tablet", 10.0, "tablet")
    assert parse_pack("strip of 15 tablet sr")[0] == "tablet sr"
    assert parse_pack("bottle of 100 ml Syrup") == ("ml syrup", 100.0, "ml")
    assert salt_part("Amoxycillin  (500mg) ") == "amoxycillin (500mg)"
    assert maker_key("M/s. Riskycorp Pharma Pvt. Ltd.") == maker_key("Riskycorp Pharma Pvt Ltd")


def test_alternatives_same_salt_same_form_only_and_maker_record():
    r = client.get("/api/medicines/9001/alternatives").json()
    names = [a["name"] for a in r["alternatives"]]
    assert "Telmikind 40 SR Tablet" not in names  # SR is a different form, never offered as a swap
    assert names[0] == "Telmi Risky 40 Tablet" and r["alternatives"][0]["maker_record"]["alerts"] == 1
    assert r["cheapest_clean"]["name"] == "Telmisoft 40 Tablet" and r["cheapest_clean"]["saving_pct"] == 93
    assert r["brands"] == 3 and r["rank"] == 3


def test_search_and_plan_savings():
    assert client.get("/api/medicines/search", params={"q": "telmik"}).json()[0]["name"].startswith("Telmikind")
    client.post("/api/care/plans", headers=H, json={"member": "Papa", "advice": [], "medicines": [
        {"name": "Telmikind 40", "strength": "40 mg", "food": "after", "morning": 1, "noon": 0, "night": 0, "days": 30, "as_needed": False}]})
    s = client.get("/api/care/savings", headers=H, params={"member": "Papa"}).json()
    # 9.80 vs 0.65 a tablet, 30 a month: the cheaper Riskycorp brand is skipped, its maker has an alert on record.
    assert s["monthly_now"] == 294 and s["monthly_cheapest"] == 20
    assert s["items"][0]["cheapest"]["name"] == "Telmisoft 40 Tablet"
    assert s["items"][0]["estimated"] is False
