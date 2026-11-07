import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
REG = auth_as("ctl-regulator", roles=("regulator",))


def setup_module():
    rows = [
        ("CTL-SP-1", "spurious", "Fake Amoxycillin Tablets", "Govt Analyst, Drugs Testing Laboratory, Gujarat", "2026-09", "Jan-2026"),
        ("CTL-NSQ-1", "nsq", "Paracetamol Tablets IP", "Govt Analyst, Drugs Testing Laboratory, Gujarat", "2026-08", "Oct-2025"),
        ("CTL-NSQ-2", "nsq", "Metformin Tablets IP", "Central Drugs Laboratory, Kolkata", "2026-09", "Nov-2025"),
    ]
    for batch, cat, prod, lab, month, mfg in rows:
        main.conn.execute("""INSERT INTO alerts (source, category, product_name, batch_no, batch_norm, manufacturer, reason, reported_by, alert_month, mfg_date, alert_url)
                             VALUES (?, ?, ?, ?, ?, 'Ctl Pharma Ltd', 'The sample does not conform to IP with respect to Assay', ?, ?, ?, 'https://x')""",
                          ("cdsco_nsq" if cat == "nsq" else "cdsco_spurious", cat, prod, batch, batch.replace("-", ""), lab, month, mfg))
    # Someone holds the spurious batch (a watchlist entry).
    main.conn.execute("""INSERT OR REPLACE INTO watchlist (device, batch, brand, added_at, last_verdict, last_checked_at)
                         VALUES ('ctl-dev', 'CTL-SP-1', 'Fake Amoxycillin', '2026-09-01', 'alert_found', '2026-09-01')""")
    main.conn.commit()


def teardown_module():
    # Other test files count alerts in the shared test DB, so leave it as we found it.
    main.conn.execute("DELETE FROM alerts WHERE batch_norm LIKE 'CTL%'")
    main.conn.execute("DELETE FROM watchlist WHERE device = 'ctl-dev'")
    main.conn.commit()


def test_overview_kpis_state_filter_and_action_queue():
    o = client.get("/api/controller", headers=REG).json()
    assert o["kpis"]["alerts_12m"] >= 3 and o["trend"] and len(o["trend"]) == 18
    assert any(a["kind"] == "recall" and "CTL-SP-1" in a["title"] for a in o["actions"])
    assert o["actions"][0]["severity"] == 0  # most urgent first

    g = client.get("/api/controller", headers=REG, params={"state": "Gujarat"}).json()
    assert g["state"] == "Gujarat" and g["kpis"]["alerts_12m"] < o["kpis"]["alerts_12m"]
    assert any(s["name"] == "Gujarat" for s in g["states"])
    assert all(x["name"] != "Other" for x in g["groups"])
