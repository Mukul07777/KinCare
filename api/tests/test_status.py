import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)


def test_status_reports_live_numbers():
    main._timings.clear()  # only this test's requests: earlier tests in the same run must not leak in
    client.post("/api/billing/checkout", json={"plan": "basic"}, headers=auth_as("status-test"))  # 503 without Stripe: not a crash
    client.get("/api/check", params={"batch": "NOPE1"})  # at least one timed request
    s = client.get("/api/status").json()
    assert s["ok"] and s["tests"] >= 90
    assert {"alerts", "medicines", "latest_list", "journal"} <= s["data"].keys()
    assert s["latency"]["requests"] >= 1 and s["latency"]["server_errors"] == 0
    assert s["quality"]["false_alarms"] == 0


def test_nightly_run_is_next_2am_ist():
    t = main._next_nightly()
    assert (t.hour, t.minute) == (main.NIGHTLY_HOUR_IST, 0) and t.utcoffset() == timedelta(hours=5, minutes=30)
    assert timedelta(0) < t - datetime.now(timezone.utc) <= timedelta(days=1)


def test_failed_ingest_is_logged_not_raised(monkeypatch):
    from ingest import fetch

    monkeypatch.setattr(fetch, "main_for", lambda **_: (_ for _ in ()).throw(RuntimeError("portal down")))
    main._refresh("test")
    last = main.conn.execute("SELECT trigger, status, error FROM ingest_runs ORDER BY id DESC LIMIT 1").fetchone()
    assert (last["trigger"], last["status"]) == ("test", "failed") and "portal down" in last["error"]
