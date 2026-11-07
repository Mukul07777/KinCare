import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from conftest import ADMIN  # noqa: E402
from testutil import auth_as  # noqa: E402
import packs  # noqa: E402

client = TestClient(main.app)


def scan(dev, serial, batch="B1", lat=None, lng=None, gtin="08900000000001"):
    return client.post("/api/packs/scan", headers=auth_as(dev),
                       json={"serial": serial, "gtin": gtin, "batch": batch, "expiry": "2027-01", "lat": lat, "lng": lng}).json()


def test_first_scan_and_same_phone_again_are_fine():
    a = scan("p1", "S-OK-1", lat=28.61, lng=77.21)
    assert a["level"] == "ok" and not a["seen_before"]
    b = scan("p1", "S-OK-1", lat=28.62, lng=77.22)
    assert b["level"] == "ok" and b["you_before"]


def test_far_apart_on_two_phones_within_a_day_is_a_clone():
    scan("d1", "S-FAR-1", lat=28.61, lng=77.21)           # Delhi
    r = scan("d2", "S-FAR-1", lat=22.57, lng=88.36)       # Kolkata, minutes later
    assert r["level"] == "clone" and any(x["kind"] == "far" for x in r["reasons"])
    assert set(r["cities"]) == {"Delhi", "Kolkata"}


def test_different_batch_under_same_serial_is_a_clone():
    scan("m1", "S-MIX-1", batch="AB123")
    r = scan("m2", "S-MIX-1", batch="ZZ999")
    assert r["level"] == "clone" and r["reasons"][0]["kind"] == "mismatch"


def test_location_rounded_and_validated():
    scan("r1", "S-ROUND-1", lat=12.971234, lng=77.594567)
    row = main.conn.execute("SELECT lat, lng, city FROM pack_scans WHERE serial = 'S-ROUND-1'").fetchone()
    assert (row["lat"], row["lng"], row["city"]) == (12.97, 77.59, "Bengaluru")
    assert client.post("/api/packs/scan", headers=auth_as("r1"), json={"serial": "X", "lat": 99, "lng": 1}).status_code == 400


def test_demo_ring_on_the_qr_test_code_shows_on_radar_then_clears():
    assert client.post("/api/packs/demo", headers=ADMIN).json()["seeded"] == len(packs.DEMO_ROUTE)
    rad = client.get("/api/packs/radar").json()
    ring = next(r for r in rad["rings"] if r["serial"] == "TST0001")
    assert ring["level"] == "clone" and ring["simulated"] and len(ring["points"]) == len(packs.DEMO_ROUTE)
    # A judge scanning the on-screen test code joins the same serial and gets the warning.
    assert scan("judge", "TST0001", batch="05240198", gtin="08901234567890")["level"] == "clone"
    assert client.delete("/api/packs/demo", headers=ADMIN).json()["cleared"] == len(packs.DEMO_ROUTE)


def test_slow_far_travel_is_not_flagged():
    old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    packs.record(main.conn, "t1", "S-SLOW-1", "g", "B1", None, 28.61, 77.21, at=old)
    assert scan("t2", "S-SLOW-1", gtin="g", lat=19.08, lng=72.88)["level"] == "ok"  # days apart: could have travelled
