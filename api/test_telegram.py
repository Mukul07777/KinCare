"""Everything WhatsApp does, on Telegram: '1' after a dose, strip photos, batch checks, reminders, recall alerts."""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import care  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
FIX = Path(__file__).parent / "tests" / "fixtures"


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(main.telegram, "send", lambda chat_id, text, buttons=None: out.append((chat_id, text, buttons)) or True)
    monkeypatch.setattr(care, "SLOTS", [("morning", "00:00"), ("noon", "00:01"), ("night", "00:02")])  # every dose already due
    return out


def linked(dev, chat_id, role="self"):
    code = main.telegram.link_code(main.conn, dev, role)
    main.telegram_handle({"message": {"chat": {"id": chat_id}, "text": f"/start {code}"}})


def plan(dev, member="Me"):
    main.conn.execute("DELETE FROM plans WHERE device = ?", (dev,))
    start = (datetime.now().date() - timedelta(days=1)).isoformat()
    client.post("/api/care/plans", headers=auth_as(dev), json={"member": member, "start_date": start,
                                                                       "medicines": [{"name": "Telma 40", "morning": 1}]})


def test_one_after_a_dose_ticks_it(sent):
    plan("tg-one")
    linked("tg-one", 101)
    main.telegram_handle({"message": {"chat": {"id": 101}, "text": "1"}})
    assert "Telma 40" in sent[-1][1] and sent[-1][2] == main.TG_BUTTONS
    main.telegram_handle({"message": {"chat": {"id": 101}, "text": "ok"}})  # "ok" in a chat is not "I took it"
    assert "Telma" not in sent[-1][1] or "दर्ज" not in sent[-1][1]


def test_dose_reminder_reaches_telegram_without_a_purchase_and_only_once(sent):
    plan("tg-rem")
    linked("tg-rem", 202)
    main.conn.execute("DELETE FROM reminders_sent")
    sent.clear()
    main.send_due_reminders()
    mine = [x for x in sent if x[0] == 202]
    assert len(mine) == 1 and "Telma 40" in mine[0][1] and mine[0][2] == main.TG_BUTTONS
    sent.clear()
    main.send_due_reminders()
    assert not [x for x in sent if x[0] == 202]


def test_caregiver_chat_gets_no_elder_reminders(sent):
    plan("tg-cg-only")
    linked("tg-cg-only", 303, role="caregiver")
    main.conn.execute("DELETE FROM reminders_sent")
    sent.clear()
    main.send_due_reminders()
    assert not [x for x in sent if x[0] == 303]


def test_alert_device_goes_to_telegram(sent):
    linked("tg-alert", 404)
    sent.clear()
    assert main.alert_device("tg-alert", "⛔ Batch X is now flagged", "Stop using it.") >= 1
    assert sent[0][0] == 404 and "flagged" in sent[0][1]


def test_strip_photo_on_telegram_reads_and_checks_the_batch(sent, monkeypatch):
    linked("tg-photo", 505)
    monkeypatch.setattr(main.telegram, "download", lambda fid: (FIX / "strip_telma.png").read_bytes())
    assert main.telegram.incoming_photo({"message": {"chat": {"id": 505}, "photo": [{"file_id": "s"}, {"file_id": "big"}]}}) == (505, "big")
    main._tg_photo_task(505, "tg-photo", "big")  # what the background thread runs
    assert "batch" in sent[-1][1].lower() or "बैच" in sent[-1][1] or "Batch" in sent[-1][1]
    hist = client.get("/api/dadi/history", headers=auth_as("tg-photo")).json()
    assert hist[-2]["text"] == "📷 Strip photo" and hist[-1]["channel"] == "telegram"


def test_photo_from_unlinked_chat_is_refused(sent):
    assert main.telegram_handle({"message": {"chat": {"id": 606}, "photo": [{"file_id": "x"}]}}) == "unlinked"


def test_start_message_lists_every_feature(sent):
    linked("tg-help", 707)
    text = sent[-1][1]
    for w in ("फ़ोटो", "बैच नंबर", "1 या दवा ले ली", "BP", "याद दिलाएँगे"):
        assert w in text, w
