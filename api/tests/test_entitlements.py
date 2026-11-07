import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import entitlements  # noqa: E402
import main  # noqa: E402
from testutil import auth_as  # noqa: E402

client = TestClient(main.app)
c = main.conn


def dev(age_days: int = 0) -> dict:
    """A fresh device, first seen `age_days` ago."""
    d = f"ent-{uuid.uuid4().hex[:10]}"
    c.execute("INSERT INTO accounts (device, first_seen) VALUES (?, ?)", (d, (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()))
    c.commit()
    return auth_as(d)


def pay(h: dict, plan: str, days_ago: int = 0) -> None:
    c.execute("INSERT INTO payments (device, plan, session_id, amount, currency, status, paid_at) VALUES (?,?,?,?,?,?,?)",
              (h["X-Device-Id"], plan, uuid.uuid4().hex, 100, "inr", "paid",
               (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")))
    c.commit()


def plan(h: dict, member: str, phone: str | None = None):
    r = client.post("/api/care/plans", headers=h, json={"member": member, "advice": [], "medicines": [{"name": "Amlong 5", "strength": "5 mg", "morning": 1}]})
    return r


def test_new_device_gets_14_day_family_trial_then_free():
    e = client.get("/api/account/entitlement", headers=dev()).json()
    assert e["plan"] == "trial" and e["tier"] == "family" and e["trial_days_left"] == 14 and e["members"] == 6
    e = client.get("/api/account/entitlement", headers=dev(age_days=20)).json()
    assert e["plan"] == "free" and e["members"] == 1 and e["wa"] == 0


def test_member_limit_after_trial_and_family_unlocks_it():
    h = dev(age_days=20)
    assert plan(h, "Me").status_code == 200
    blocked = plan(h, "Dadi")
    assert blocked.status_code == 402 and "Family" in blocked.json()["detail"]
    assert plan(h, "Me").status_code == 200  # same person, more medicines: always fine
    pay(h, "family")
    assert plan(h, "Dadi").status_code == 200


def test_whatsapp_reminders_need_a_plan_but_recall_alerts_never_do():
    h = dev(age_days=20)
    plan(h, "Me")
    mid = c.execute("SELECT m.id FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ?", (h["X-Device-Id"],)).fetchone()[0]
    r = client.post("/api/care/purchase", headers=h, json={"med_id": mid, "batch": "CLEAN1", "phone": "9811111111", "qty": 10}).json()
    assert r["whatsapp"] == "upgrade"
    assert c.execute("SELECT phone FROM plan_meds WHERE id = ?", (mid,)).fetchone()[0] is None  # no reminder loop for free users

    c.execute("""INSERT INTO alerts (source, category, product_name, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                 VALUES ('cdsco_nsq', 'nsq', 'Amlodipine Tablets', 'BADENT1', 'BADENT1', 'X Labs', 'Assay', '2026-09', 'https://x')""")
    c.commit()
    r = client.post("/api/care/purchase", headers=h, json={"med_id": mid, "batch": "BADENT1", "phone": "9811111111"}).json()
    assert r["verdict"] == "alert_found"
    sent = c.execute("SELECT 1 FROM notifications WHERE phone = '+919811111111' AND batch = 'BADENT1'").fetchone()
    c.execute("DELETE FROM alerts WHERE batch_norm = 'BADENT1'")  # other test files count alerts in this shared DB
    c.commit()
    assert sent  # the recall alert still went to the free user's WhatsApp


def test_paying_pharmacy_covers_its_customers():
    shop = dev(age_days=40)
    pay(shop, "pharmacy")
    c.execute("INSERT INTO sales (device, pharmacy, phone, product, batch, batch_norm) VALUES (?,?,?,?,?,?)",
              (shop["X-Device-Id"], "Sharma Medicos", "+919822222222", "Amlong 5", "B1", "B1"))
    c.commit()
    customer = dev(age_days=40)  # past the trial, no plan of their own
    plan(customer, "Me")
    mid = c.execute("SELECT m.id FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ?", (customer["X-Device-Id"],)).fetchone()[0]
    r = client.post("/api/care/purchase", headers=customer, json={"med_id": mid, "batch": "CLEAN2", "phone": "9822222222"}).json()
    assert r["whatsapp"] == "sponsored:Sharma Medicos"


def test_yearly_plan_stays_active_all_year_and_all_access_switch(monkeypatch):
    h = dev(age_days=100)
    pay(h, "family_year", days_ago=200)
    assert entitlements.of(c, h["X-Device-Id"])["tier"] == "family"
    h2 = dev(age_days=100)
    pay(h2, "family", days_ago=40)  # monthly plan not renewed
    assert entitlements.of(c, h2["X-Device-Id"])["tier"] == "free"
    monkeypatch.setenv("KINCARE_ALL_ACCESS", "1")
    assert entitlements.of(c, h2["X-Device-Id"])["tier"] == "pharmacy_pro"
