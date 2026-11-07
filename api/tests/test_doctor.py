import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import doctor  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
H = auth_as("doc-test-device")


def test_news2_bands():
    assert doctor.news2(37.0, 120, 75, 98)["risk"] == "low"
    assert doctor.news2(37.0, 120, 75, 98)["score"] == 0
    one_red = doctor.news2(37.0, 120, 135, 98)
    assert one_red["score"] == 3 and one_red["risk"] == "low-medium"
    assert doctor.news2(39.5, 95, 120, 93)["risk"] == "high"  # 2 + 2 + 2 + 2 = 8


def test_live_stream_flags_on_median_and_saves_history():
    r = client.post("/api/care/live", headers=H, json={"member": "Dadi", "source": "replay",
                                                       "samples": [{"pulse": 140, "spo2": 90}] * 5 + [{"pulse": 999}]})
    body = r.json()
    assert r.status_code == 200 and body["accepted"] == 5  # the impossible pulse is dropped
    assert body["assessment"]["level"] == "urgent" and body["saved_to_history"]
    again = client.post("/api/care/live", headers=H, json={"member": "Dadi", "source": "replay", "samples": [{"pulse": 80}]})
    assert not again.json()["saved_to_history"]  # one history row per 5 min per source
    assert client.post("/api/care/live", headers=H, json={"member": "Dadi", "source": "bogus", "samples": [{"pulse": 80}]}).status_code == 400


def test_doctor_link_view_messages_and_revoke():
    client.post("/api/care/plans", headers=H, json={"member": "Dadi", "doctor": "Dr. Rao", "advice": ["Rest"],
                                                    "medicines": [{"name": "Paracetamol", "strength": "500 mg", "food": "after",
                                                                   "morning": 1, "noon": 0, "night": 1, "days": 5, "as_needed": False}]})
    lk = client.post("/api/doctor/links", headers=H, json={"member": "Dadi", "doctor": "Dr. Rao", "hours": 24}).json()
    tok = lk["token"]
    assert lk["room"].startswith("kincare-consult-") and tok not in lk["room"]

    view = client.get(f"/api/doctor/{tok}").json()
    assert view["member"] == "Dadi" and view["latest"]["pulse"] is not None and view["news2"]["partial"]
    assert view["plans"][0]["medicines"][0]["name"] == "Paracetamol"

    live = client.get(f"/api/doctor/{tok}/live").json()
    assert live["online"] and live["samples"]

    r = client.post(f"/api/doctor/{tok}/messages", json={"kind": "advice", "text": "Check oxygen every 2 hours"}).json()
    assert r["added_to_plan"]
    assert "Check oxygen every 2 hours" in client.get("/api/care/today", headers=H).json()["advice"]
    inbox = client.get("/api/care/messages", headers=H).json()
    assert inbox["unread"] == 1
    client.post("/api/care/messages", headers=H, json={"token": tok, "text": "Thank you doctor"})
    assert len(client.get(f"/api/doctor/{tok}/live", params={"msg_since": r["id"]}).json()["messages"]) == 1
    # Another phone can't post into this patient's thread.
    assert client.post("/api/care/messages", headers=auth_as("other"), json={"token": tok, "text": "hi"}).status_code == 404

    client.delete(f"/api/doctor/links/{tok}", headers=H)
    assert client.get(f"/api/doctor/{tok}").status_code == 410


def test_ppg_estimate_on_clean_and_noisy_waves():
    import math
    import random

    import ppg

    hz = 25
    t = [i * 1000 / hz for i in range(12 * hz)]
    # 72 bpm: a systolic bump plus a smaller dicrotic bump per beat, as camera brightness (darker = more blood).
    beat = [-(max(0, math.sin(2 * math.pi * 1.2 * x / 1000)) ** 3 + 0.25 * max(0, -math.sin(2 * math.pi * 1.2 * x / 1000)) ** 3) for x in t]
    assert abs(ppg.estimate(t, beat) - 72) <= 2
    rnd = random.Random(1)
    assert ppg.estimate(t, [rnd.random() for _ in t]) is None  # noise gets no number


def test_bidmc_reference_record_if_downloaded():
    from ingest import bidmc

    if not (bidmc.RAW / "bidmc01.dat").exists():
        return  # raw data not fetched on this machine
    r = bidmc.load_record(1)
    assert r["age"] == 88 and r["seconds"] > 400 and len(r["pleth"]) > 400 * 20
    assert r["validation"]["errors"] and sum(r["validation"]["errors"]) / len(r["validation"]["errors"]) < 5
