import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import billing  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import whatsapp  # noqa: E402

client = TestClient(main.app)
H = auth_as("wa-test-device")
PHONE = "+919812345678"


def hook(text: str, phone: str = PHONE) -> dict:
    """The shape Meta posts for one incoming text message."""
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "messages": [{"from": phone.lstrip("+"), "type": "text", "text": {"body": text}}]}}]}]}


def test_intent_parsing():
    assert whatsapp.intent("1") == ("taken", None)
    assert whatsapp.intent("le li ✅".replace(" ✅", "")) == ("taken", None)
    assert whatsapp.intent("Hi") == ("hello", None)
    assert whatsapp.intent("JOIN") == ("hello", None)
    assert whatsapp.intent("check AT25-0938A") == ("batch", "AT25-0938A")
    assert whatsapp.intent("B.No. pcm2304") == ("batch", "PCM2304")
    assert whatsapp.intent("what is this")[0] == "other"
    assert whatsapp.intent("hello world")[0] == "hello"


def test_free_text_inside_window_template_outside(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TEMPLATE", "kincare_update")
    inside = whatsapp.payload(PHONE, "Line one\nLine two", in_window=True)
    assert inside["type"] == "text" and inside["to"] == "919812345678"
    outside = whatsapp.payload(PHONE, "Line one\nLine two", in_window=False)
    assert outside["type"] == "template" and outside["template"]["name"] == "kincare_update"
    assert outside["template"]["components"][0]["parameters"][0]["text"] == "Line one · Line two"  # no newlines in template variables

    c = main.conn
    c.execute("DELETE FROM wa_inbound WHERE phone = ?", (PHONE,))
    assert not whatsapp.window_open(c, PHONE)
    whatsapp.record_inbound(c, PHONE, "hi")
    assert whatsapp.window_open(c, PHONE)
    assert not whatsapp.window_open(c, PHONE, now=datetime.now(timezone.utc) + timedelta(hours=24))


def test_webhook_verify_and_signature(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "s3cret")
    ok = client.get("/api/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "s3cret", "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    assert client.get("/api/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"}).status_code == 403

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "appsecret")
    raw = json.dumps(hook("hi")).encode()
    bad = client.post("/api/whatsapp/webhook", content=raw, headers={"X-Hub-Signature-256": "sha256=00"})
    assert bad.status_code == 401
    sig = "sha256=" + hmac.new(b"appsecret", raw, hashlib.sha256).hexdigest()
    assert client.post("/api/whatsapp/webhook", content=raw, headers={"X-Hub-Signature-256": sig}).json()["handled"] == 1


def test_reply_1_ticks_the_due_dose_and_batch_check():
    plan = client.post("/api/care/plans", headers=H, json={"member": "Nani", "advice": [], "medicines": [
        {"name": "Amlong 5", "strength": "5 mg", "morning": 1, "noon": 1, "night": 1}]}).json()
    mid = main.conn.execute("SELECT id FROM plan_meds WHERE plan_id = ?", (plan["id"],)).fetchone()[0]
    client.post("/api/care/purchase", headers=H, json={"med_id": mid, "batch": "OKWA1", "phone": PHONE, "language": "en", "qty": 30})
    # Pretend the 08:00 reminder already went out today.
    day = datetime.now().date().isoformat()
    main.conn.execute("DELETE FROM doses WHERE med_id = ?", (mid,))
    # A purchase late in the day already logs earlier slots as reminded; keep only the morning one so the test
    # doesn't depend on the time it runs.
    main.conn.execute("DELETE FROM reminders_sent WHERE med_id = ?", (mid,))
    main.conn.execute("INSERT OR REPLACE INTO reminders_sent (med_id, day, slot, sent_at) VALUES (?,?,?,?)", (mid, day, "morning", main.now()))
    main.conn.commit()

    assert client.post("/api/whatsapp/webhook", json=hook("1")).json()["handled"] == 1
    assert main.conn.execute("SELECT 1 FROM doses WHERE med_id = ? AND day = ? AND slot = 'morning'", (mid, day)).fetchone()
    reply = main.conn.execute("SELECT message FROM notifications WHERE phone = ? ORDER BY id DESC LIMIT 1", (PHONE,)).fetchone()[0]
    assert "Marked Amlong 5 as taken for Nani" in reply

    main.conn.execute("""INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                         VALUES ('cdsco_nsq', 'nsq', 'Namik-MR Tablets', 'Namik-MR', 'WA25-77', 'WA2577', 'Aspo', 'Assay', '2026-09', 'https://cdsco.gov.in/x')""")
    main.conn.commit()
    client.post("/api/whatsapp/webhook", json=hook("check WA25-77"))
    reply = main.conn.execute("SELECT message FROM notifications WHERE phone = ? ORDER BY id DESC LIMIT 1", (PHONE,)).fetchone()[0]
    assert "Namik-MR" in reply and "not of standard quality" in reply
    client.post("/api/whatsapp/webhook", json=hook("check ZZ99-12345"))
    reply = main.conn.execute("SELECT message FROM notifications WHERE phone = ? ORDER BY id DESC LIMIT 1", (PHONE,)).fetchone()[0]
    assert "not on any CDSCO or state alert list" in reply


def test_every_plan_profitable_even_in_the_worst_case():
    # Worst case: every capped number uses its full paid-message cap every month.
    for pid, p in billing.PLANS.items():
        price_month = p["amount"] / 100 / (12 if p["interval"] == "year" else 1)
        per_number = 1 if pid.startswith("pharmacy") else whatsapp.PAID_CAP  # pharmacy numbers get ~1 recall alert each
        worst = p["wa_numbers"] * per_number * whatsapp.PAID_RATE_INR
        assert worst < 0.4 * price_month, (pid, round(worst), price_month)
    assert billing.PLANS["basic"]["amount"] == 2900 and billing.PLANS["family"]["amount"] == 6900
    assert billing.PLANS["family_year"]["amount"] == 10 * billing.PLANS["family"]["amount"] + 900  # ~2 months free


def test_paid_cap_stops_routine_reminders_not_recalls(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    monkeypatch.setenv("WHATSAPP_PHONE_ID", "p")
    monkeypatch.setenv("WHATSAPP_TEMPLATE", "kincare_update")
    sent = []

    class Ok:
        ok = True
        def json(self): return {"messages": [{"id": "wamid.x"}]}

    monkeypatch.setattr(whatsapp.requests, "post", lambda url, json, **k: sent.append(json["type"]) or Ok())
    phone = "+919800000099"
    c = main.conn
    c.execute("DELETE FROM wa_inbound WHERE phone = ?", (phone,))
    c.execute("DELETE FROM wa_paid WHERE phone = ?", (phone,))
    for _ in range(whatsapp.PAID_CAP):
        assert whatsapp.send(c, phone, "dose")[0] == "sent"
    assert whatsapp.send(c, phone, "dose")[0] == "capped"            # routine reminder: falls back to the phone notification
    assert whatsapp.send(c, phone, "recall", urgent=True)[0] == "sent"  # safety messages always go
    assert whatsapp.paid_this_month(c, phone) == whatsapp.PAID_CAP + 1
    whatsapp.record_inbound(c, phone, "1")                            # patient replied: window open, free again
    assert whatsapp.send(c, phone, "dose")[0] == "sent" and sent[-1] == "text"
    assert whatsapp.paid_this_month(c, phone) == whatsapp.PAID_CAP + 1
