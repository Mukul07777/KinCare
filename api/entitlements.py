"""What a device's plan allows. Safety is never gated: scans, batch checks and recall alerts are free for all.

Tiers (each includes the one below): free < basic < family < pharmacy < pharmacy_pro.
- New devices get a 14-day Family trial, no card.
- A paying pharmacy covers Basic for its own customers (phones on its sales records):
  the pharmacy pays, its customers get WhatsApp reminders free. That is KinCare's distribution channel.
- KINCARE_ALL_ACCESS=1 unlocks everything (stage demos, development).
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import billing

TIERS = ["free", "basic", "family", "pharmacy", "pharmacy_pro"]
TRIAL_DAYS = 14
LIMITS = {  # members = people with a care plan; wa = WhatsApp reminder numbers
    "free": {"members": 1, "wa": 0},
    "basic": {"members": 1, "wa": 1},
    "family": {"members": 6, "wa": 3},
    "pharmacy": {"members": 6, "wa": 3},
    "pharmacy_pro": {"members": 6, "wa": 3},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    device TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL
);
"""


def seen(conn: sqlite3.Connection, device: str) -> None:
    conn.execute("INSERT OR IGNORE INTO accounts (device, first_seen) VALUES (?, ?)", (device, datetime.now(timezone.utc).isoformat()))


def tier_of(plan_id: str | None) -> str:
    """'family_year' -> 'family'."""
    return (plan_id or "free").removesuffix("_year")


def active_plan(conn: sqlite3.Connection, device: str) -> dict | None:
    """Latest paid plan still inside its billing period (31 days monthly, 366 days yearly)."""
    for r in conn.execute("SELECT plan, paid_at, email FROM payments WHERE device = ? AND status = 'paid' ORDER BY paid_at DESC", (device,)):
        days = 366 if billing.PLANS.get(r["plan"], {}).get("interval") == "year" else 31
        if datetime.fromisoformat(r["paid_at"].replace("Z", "+00:00")) > datetime.now(timezone.utc) - timedelta(days=days):
            return dict(r)
    return None


def sponsored(conn: sqlite3.Connection, phone: str | None) -> str | None:
    """Name of a paying pharmacy that sold to this phone, if any (it covers the customer's Basic plan)."""
    if not phone:
        return None
    for r in conn.execute("SELECT DISTINCT device, pharmacy FROM sales WHERE phone = ?", (phone,)):
        p = active_plan(conn, r["device"])
        if p and TIERS.index(tier_of(p["plan"])) >= TIERS.index("pharmacy"):
            return r["pharmacy"] or "your pharmacy"
    return None


def of(conn: sqlite3.Connection, device: str) -> dict:
    if os.environ.get("KINCARE_ALL_ACCESS") == "1":
        return {"tier": "pharmacy_pro", "plan": "all_access", "trial_days_left": None, **LIMITS["pharmacy_pro"]}
    paid = active_plan(conn, device)
    if paid:
        t = tier_of(paid["plan"])
        return {"tier": t, "plan": paid["plan"], "trial_days_left": None, **LIMITS[t]}
    r = conn.execute("SELECT first_seen FROM accounts WHERE device = ?", (device,)).fetchone()
    first = datetime.fromisoformat(r[0]) if r else datetime.now(timezone.utc)
    left = TRIAL_DAYS - (datetime.now(timezone.utc) - first).days
    if left > 0:
        return {"tier": "family", "plan": "trial", "trial_days_left": left, **LIMITS["family"]}
    return {"tier": "free", "plan": "free", "trial_days_left": 0, **LIMITS["free"]}


def at_least(ent: dict, tier: str) -> bool:
    return TIERS.index(ent["tier"]) >= TIERS.index(tier)


def can_add_member(conn: sqlite3.Connection, device: str, member: str) -> tuple[bool, str | None]:
    ent = of(conn, device)
    members = {r[0] for r in conn.execute("SELECT DISTINCT member FROM plans WHERE device = ?", (device,))}
    if member in members or len(members) < ent["members"]:
        return True, None
    return False, (f"Your plan covers {ent['members']} person. Family (₹69/month) covers up to 6 people; "
                   "batch checks and recall alerts stay free.")


def whatsapp_reminders_ok(conn: sqlite3.Connection, device: str, phone: str) -> tuple[bool, str | None]:
    """WhatsApp dose reminders: Basic or above, a trial, or a paying pharmacy covering this customer.

    Returns (ok, sponsor name). Numbers already in use on this device never count twice."""
    sponsor = sponsored(conn, phone)
    if sponsor:
        return True, sponsor
    ent = of(conn, device)
    if not at_least(ent, "basic"):
        return False, None
    used = {r[0] for r in conn.execute(
        "SELECT DISTINCT m.phone FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ? AND m.phone IS NOT NULL", (device,))}
    return (phone in used or len(used) < ent["wa"]), None
