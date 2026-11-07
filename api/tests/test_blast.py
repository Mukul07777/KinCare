import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import blast  # noqa: E402
import main  # noqa: E402
from conftest import ADMIN  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
c = main.conn
BATCH = "BL25-0042"


def setup_module():
    c.execute("""INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                 VALUES ('cdsco_nsq', 'nsq', 'Blastocin 500 Tablets', 'Blastocin 500', ?, 'BL250042', 'Test Labs', 'Dissolution', '2026-09', 'https://x')""", (BATCH,))
    c.commit()


def teardown_module():
    blast.clear_demo(c, BATCH)
    c.execute("DELETE FROM alerts WHERE batch_norm = 'BL250042'")  # other test files count alerts in this shared DB
    c.commit()


def test_body_signal_compares_before_and_after_starting():
    t0 = datetime.now(timezone.utc) - timedelta(days=5)
    for k, (days, pulse) in enumerate([(-9, 72), (-7, 74), (-3, 73), (1, 88), (2, 90), (3, 87)]):
        c.execute("INSERT INTO vitals (device, member, at, pulse, spo2) VALUES ('bs-dev', 'Me', ?, ?, 98)",
                  ((t0 + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z"), pulse))
    c.commit()
    b = blast.body_signal(c, "bs-dev", "Me", t0.isoformat())
    pulse = next(x for x in b["changes"] if x["key"] == "pulse")
    assert b["enough"] and pulse["before"] == 73 and pulse["after"] == 88 and pulse["delta"] == 15 and pulse["flagged"]
    assert not next(x for x in b["changes"] if x["key"] == "spo2")["flagged"]
    assert blast.body_signal(c, "nobody", "Me", t0.isoformat())["enough"] is False


def test_exposure_soonest_dose_first_with_body_signal():
    assert client.post(f"/api/blast/{BATCH}/demo", params={"holders": 12}, headers=ADMIN).json()["seeded"] == 12
    r = client.get("/api/blast/BL250042", headers=ADMIN).json()  # normalised batch in the URL works too
    s = r["summary"]
    assert r["alert"]["brand"] == "Blastocin 500"
    assert s["holders"] >= 12 + 3 and s["simulated"] == s["holders"]
    mins = [h["minutes"] for h in r["holders"] if h["minutes"] is not None]
    assert mins == sorted(mins) and len(mins) == 12  # care holders ranked by next dose
    assert r["holders"][-1]["minutes"] is None        # pharmacy customers (no dose times) come after
    assert s["with_vitals"] == 12 and s["reacting"] == 4 and s["top_change"] == "Resting pulse"  # every 3rd simulated holder
    assert any(b["batch_no"] == BATCH for b in client.get("/api/blast", headers=ADMIN).json())


def test_alert_everyone_once_simulated_never_messaged():
    before = c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    r = client.post(f"/api/blast/{BATCH}/alert", headers=ADMIN).json()
    assert r["count"] >= 15 and {a["status"] for a in r["alerted"]} == {"simulated"}
    assert c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == before  # nothing sent to simulated people
    assert client.post(f"/api/blast/{BATCH}/alert", headers=ADMIN).json()["count"] == 0         # never alerts twice
    assert client.get(f"/api/blast/{BATCH}", headers=ADMIN).json()["summary"]["alerted"] >= 15
    assert client.get("/api/blast/NOTFLAGGED999", headers=ADMIN).status_code == 404


def test_patient_sees_their_own_body_signal():
    h = auth_as("bs-patient")
    plan = client.post("/api/care/plans", headers=h, json={"member": "Me", "advice": [], "medicines": [{"name": "Amlong 5", "strength": "5 mg", "morning": 1}]}).json()
    mid = c.execute("SELECT id FROM plan_meds WHERE plan_id = ?", (plan["id"],)).fetchone()[0]
    client.post("/api/care/purchase", headers=h, json={"med_id": mid, "batch": "OKBS1", "qty": 10})
    r = client.get("/api/care/batch-effects", headers=h).json()
    assert r[0]["name"] == "Amlong 5" and r[0]["enough"] is False  # no vitals yet: says so, invents nothing


def test_recall_gap_reads_every_date_shape():
    import timeline

    assert timeline.month_index("Aug-2025") == timeline.month_index("08/2025") == timeline.month_index("2025-08") == timeline.month_index("Aug 25")
    assert timeline.month_index("Sept. 2024") == 2024 * 12 + 8
    assert timeline.month_index("junk") is None and timeline.month_index("13/2025") is None
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE alerts (mfg_date TEXT, expiry TEXT, alert_month TEXT)")
    db.executemany("INSERT INTO alerts VALUES (?,?,?)", [("Jan-2025", "Dec-2026", "2025-11"),   # listed 10 months after made, 13 left
                                                         ("03/2024", "02/2026", "2025-03"),    # 12 months, 11 left
                                                         ("Jun-2023", "May-2024", "2025-01"),  # listed after expiry
                                                         ("junk", None, "2025-01")])
    r = timeline.compute(db)
    assert r["alerts_used_lag"] == 3 and r["median_lag_months"] == 12 and r["median_shelf_left_months"] == 12
    assert r["in_date_when_listed"] == 2 and r["pct_in_date_when_listed"] == 66.7
    assert client.get("/api/insights/recall-gap").status_code == 200
