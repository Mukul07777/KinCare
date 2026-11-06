import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core import conn  # noqa: E402
from matcher import normalise_batch  # noqa: E402

client = TestClient(main.app)


def _seed_alert(batch: str, product: str, brand: str):
    conn.execute(
        """INSERT OR IGNORE INTO alerts (source, category, product_name, brand, batch_no, batch_norm, mfg_date, expiry,
           manufacturer, manufacturer_full, reason, reported_by, remarks, alert_month, alert_url, pdf_page)
           VALUES ('state_nsq','nsq',?,?,?,?,'Nov-2025','Oct-2027','Test Pharma','','Failed assay','LUCKNOW','','2026-09','',NULL)""",
        (product, brand, batch, normalise_batch(batch)),
    )
    conn.commit()


def test_switch_network_shows_blast_radius_and_doctor_gate():
    _seed_alert("AT25-0938A", "Aceclofenac, Paracetamol & Chlorzoxazone Tablets", "Namik-MR")
    _seed_alert("H26MAB011", "Thyroxine Sodium Tablets IP", "Thyrox 50")
    r = client.get("/api/switch/network")
    assert r.status_code == 200
    n = r.json()
    assert {"pharmacy", "families", "flagged", "documents", "agents"} <= n.keys()
    assert len(n["agents"]) == 4
    by = {f["batch"].upper(): f for f in n["flagged"]}
    assert len(by["AT25-0938A"]["holders"]) == 3                    # one recall, three homes (switch/network.json)
    assert by["H26MAB011"]["doctor"]["required"] is True             # thyroid hormone needs the doctor too
    assert not by["AT25-0938A"]["doctor"]["required"]
    times = [min(h["times"]) for h in by["AT25-0938A"]["holders"]]
    assert times == sorted(times)                                    # earliest dose first
