import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from conftest import ADMIN  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)


def test_reset_removes_only_simulated_rows():
    main.conn.execute("""INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                         VALUES ('state_nsq', 'nsq', 'Reset Test Tablets', 'ResetMed', 'RST-1', 'RST1', 'X Ltd', 'Assay', '2026-09', 'https://x')""")
    main.conn.commit()
    real = client.post("/api/care/plans", headers=auth_as("real-user"), json={"member": "Me", "advice": [], "medicines": [
        {"name": "Real Med", "strength": "5 mg", "morning": 1, "noon": 0, "night": 0}]}).json()["id"]
    assert client.post("/api/blast/RST-1/demo", params={"holders": 5}, headers=ADMIN).json()["seeded"] >= 5
    client.post("/api/packs/demo", headers=ADMIN)
    main.conn.execute("INSERT INTO reports (device, batch, batch_norm, symptoms, origin) VALUES ('sim-r', 'RST-1', 'RST1', 'rash', 'simulated')")
    main.conn.commit()

    r = client.post("/api/admin/demo-reset", headers=ADMIN).json()
    assert r["ok"] and r["copied_code_scans"] > 0 and r["symptom_reports"] == 1
    one = lambda sql: main.conn.execute(sql).fetchone()[0]
    assert one("SELECT COUNT(*) FROM plans WHERE device LIKE 'sim-%'") == 0
    assert one("SELECT COUNT(*) FROM pack_scans WHERE origin = 'simulated'") == 0
    assert one(f"SELECT COUNT(*) FROM plans WHERE id = {real}") == 1  # the real user's plan stays
    main.conn.execute("DELETE FROM alerts WHERE batch_norm = 'RST1'")
    main.conn.commit()
