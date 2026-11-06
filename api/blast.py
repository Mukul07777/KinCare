"""Recall blast radius: who holds a flagged batch, whose next dose is soonest, and is their body reacting.

A regulator list says *which batch* failed. KinCare knows *who has it*: patients who recorded buying it,
pharmacy customers it was sold to, and people watching it. For each holder we compute the next dose
time (from their prescription) and compare their vitals before vs after they started the batch.
Alerts go out soonest-dose first, so the person about to swallow the next tablet hears first.

The vitals comparison is a signal for a doctor, never a diagnosis: we say "changed since starting",
never "caused by".
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from statistics import median

import care
from matcher import normalise_batch

SCHEMA = """
CREATE TABLE IF NOT EXISTS blast_alerts (
    batch_norm TEXT NOT NULL,
    holder TEXT NOT NULL,            -- 'plan:<med_id>' | 'sale:<sale_id>' | 'watch:<device>'
    status TEXT NOT NULL,            -- sent / outbox / push / failed
    at TEXT NOT NULL,
    PRIMARY KEY (batch_norm, holder)
);
"""

# A change worth telling a doctor about (median after vs median before). Deliberately conservative.
THRESHOLDS = {"pulse": 10, "spo2": -3, "bp_sys": 15, "temp_c": 0.8}
LABELS = {"pulse": ("Resting pulse", "bpm"), "spo2": ("Oxygen", "%"), "bp_sys": ("Systolic BP", "mmHg"), "temp_c": ("Temperature", "°C")}
WINDOW_BEFORE = timedelta(days=14)


def _ts(s: str | None) -> datetime | None:
    if not s:
        return None
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def body_signal(conn: sqlite3.Connection, device: str, member: str, started: str | None) -> dict | None:
    """Median vitals in the 14 days before starting this batch vs since. None if there isn't enough to compare."""
    t0 = _ts(started)
    if not t0:
        return None
    rows = conn.execute("SELECT at, pulse, spo2, bp_sys, temp_c FROM vitals WHERE device = ? AND member = ? AND at >= ?",
                        (device, member, (t0 - WINDOW_BEFORE).strftime("%Y-%m-%dT%H:%M:%S"))).fetchall()
    before = [r for r in rows if _ts(r["at"]) < t0]
    after = [r for r in rows if _ts(r["at"]) >= t0]
    if len(before) < 2 or len(after) < 2:
        return {"enough": False, "before": len(before), "after": len(after), "changes": []}
    changes = []
    for k, limit in THRESHOLDS.items():
        b = [r[k] for r in before if r[k] is not None]
        a = [r[k] for r in after if r[k] is not None]
        if len(b) < 2 or len(a) < 2:
            continue
        delta = round(median(a) - median(b), 1)
        flagged = delta >= limit if limit > 0 else delta <= limit
        label, unit = LABELS[k]
        changes.append({"key": k, "label": label, "unit": unit, "before": round(median(b), 1), "after": round(median(a), 1),
                        "delta": delta, "flagged": flagged})
    return {"enough": True, "before": len(before), "after": len(after), "changes": changes,
            "flagged": [c for c in changes if c["flagged"]]}


def _next_dose(med: dict, start: str, now: datetime, taken: set[tuple[str, str]]) -> tuple[datetime | None, str | None]:
    """Next untaken dose from now (a dose already due today and not taken counts as 'now')."""
    for offset in range(0, 3):
        day = now.date() + timedelta(days=offset)
        for d in care.doses_for(med, start, day):
            at = datetime.combine(day, datetime.strptime(d["time"], "%H:%M").time())
            if (day.isoformat(), d["slot"]) in taken:
                continue
            if offset == 0 and at < now:
                return now, d["slot"]  # overdue today: due right now
            if at >= now:
                return at, d["slot"]
    return None, None


def exposure(conn: sqlite3.Connection, batch: str, now: datetime | None = None) -> dict:
    """Everyone KinCare knows holds this batch, soonest next dose first."""
    bn = normalise_batch(batch)
    now = now or datetime.now()
    alerted = {r["holder"]: dict(r) for r in conn.execute("SELECT * FROM blast_alerts WHERE batch_norm = ?", (bn,))}
    holders = []

    # 1. Patients who recorded buying it against a prescription: we know their dose times and vitals.
    for m in conn.execute("""SELECT m.*, p.member, p.start_date, p.device FROM plan_meds m JOIN plans p ON p.id = m.plan_id
                             WHERE m.batch IS NOT NULL AND m.bought_at IS NOT NULL"""):
        m = dict(m)
        if normalise_batch(m["batch"]) != bn:
            continue
        taken = {(r["day"], r["slot"]) for r in conn.execute("SELECT day, slot FROM doses WHERE med_id = ?", (m["id"],))}
        nxt, slot = _next_dose(m, m["start_date"], now, taken)
        doses_taken = conn.execute("SELECT COUNT(*) FROM doses WHERE med_id = ? AND taken_at >= ?", (m["id"], m["bought_at"])).fetchone()[0]
        key = f"plan:{m['id']}"
        holders.append({
            "key": key, "source": "care", "name": m["member"], "phone": m["phone"], "city": m["pharmacy"],
            "medicine": m["name"], "since": m["bought_at"], "doses_taken": doses_taken,
            "next_dose": nxt.isoformat(timespec="minutes") if nxt else None, "next_slot": slot,
            "minutes": int((nxt - now).total_seconds() // 60) if nxt else None,
            "body": body_signal(conn, m["device"], m["member"], m["bought_at"]),
            "simulated": m["device"].startswith("sim-"), "alert": alerted.get(key),
        })

    # 2. Pharmacy customers it was sold to: no dose times, so they rank after known-due doses.
    for s in conn.execute("SELECT * FROM sales WHERE batch_norm = ?", (bn,)):
        key = f"sale:{s['id']}"
        holders.append({"key": key, "source": "pharmacy", "name": s["customer"] or "Customer", "phone": s["phone"], "city": s["city"] or s["pharmacy"],
                        "medicine": s["product"], "since": s["sold_at"], "doses_taken": None, "next_dose": None, "next_slot": None,
                        "minutes": None, "body": None, "simulated": s["device"].startswith("sim-"), "alert": alerted.get(key)})

    # 3. People watching the batch.
    for w in conn.execute("SELECT * FROM watchlist"):
        if normalise_batch(w["batch"]) != bn:
            continue
        key = f"watch:{w['device']}"
        holders.append({"key": key, "source": "watchlist", "name": w["name"] or w["member"] or "Watcher", "phone": w["phone"], "city": None,
                        "medicine": w["brand"], "since": w["added_at"], "doses_taken": None, "next_dose": None, "next_slot": None,
                        "minutes": None, "body": None, "simulated": w["device"].startswith("sim-"), "alert": alerted.get(key)})

    holders.sort(key=lambda h: (h["minutes"] is None, h["minutes"] if h["minutes"] is not None else 0, h["name"]))
    with_body = [h for h in holders if h["body"] and h["body"]["enough"]]
    reacting = [h for h in with_body if h["body"]["flagged"]]
    # Which vital moved most often among holders: the batch-level body signal.
    counts: dict[str, int] = {}
    for h in reacting:
        for c in h["body"]["flagged"]:
            counts[c["label"]] = counts.get(c["label"], 0) + 1
    return {
        "batch": bn,
        "holders": holders,
        "summary": {
            "holders": len(holders),
            "due_1h": sum(1 for h in holders if h["minutes"] is not None and h["minutes"] <= 60),
            "due_6h": sum(1 for h in holders if h["minutes"] is not None and h["minutes"] <= 360),
            "due_24h": sum(1 for h in holders if h["minutes"] is not None and h["minutes"] <= 1440),
            "alerted": sum(1 for h in holders if h["alert"]),
            "doses_taken": sum(h["doses_taken"] or 0 for h in holders),
            "with_vitals": len(with_body),
            "reacting": len(reacting),
            "top_change": max(counts.items(), key=lambda kv: kv[1])[0] if counts else None,
            "simulated": sum(1 for h in holders if h["simulated"]),
        },
    }


def mark(conn: sqlite3.Connection, batch_norm: str, holder: str, status: str) -> None:
    conn.execute("INSERT OR REPLACE INTO blast_alerts (batch_norm, holder, status, at) VALUES (?,?,?,?)",
                 (batch_norm, holder, status, datetime.now(timezone.utc).isoformat()))


def flagged_with_holders(conn: sqlite3.Connection, limit: int = 12) -> list[dict]:
    """Flagged batches that at least one known person holds: the recall desk's inbox."""
    held = {normalise_batch(r[0]) for r in conn.execute("SELECT batch FROM plan_meds WHERE batch IS NOT NULL AND bought_at IS NOT NULL")}
    held |= {r[0] for r in conn.execute("SELECT batch_norm FROM sales")}
    held |= {normalise_batch(r[0]) for r in conn.execute("SELECT batch FROM watchlist")}
    if not held:
        return []
    marks = ",".join("?" * len(held))
    rows = conn.execute(f"""SELECT batch_norm, MAX(batch_no) AS batch_no, MAX(COALESCE(brand, product_name)) AS medicine, MAX(manufacturer) AS maker,
                                   MAX(category) AS category, MAX(alert_month) AS month, MAX(reason) AS reason
                            FROM alerts WHERE batch_norm IN ({marks}) GROUP BY batch_norm ORDER BY month DESC LIMIT ?""", (*held, limit)).fetchall()
    return [dict(r) for r in rows]


# ---- demo seeding: simulated holders, clearly labelled ----

CITIES = ["Delhi", "Noida", "Gurugram", "Jaipur", "Lucknow", "Chandigarh", "Ghaziabad", "Faridabad"]
NAMES = ["Kamla", "Ramesh", "Sunita", "Arjun", "Meena", "Harish", "Farida", "Joseph", "Lakshmi", "Gurpreet", "Anil", "Shabnam",
         "Vijay", "Rekha", "Imran", "Pooja", "Suresh", "Neha", "Mohan", "Asha", "Deepak", "Savita", "Rahul", "Kiran"]


def seed_demo(conn: sqlite3.Connection, batch: str, medicine: str, n: int = 24, seed: int = 11) -> int:
    """Simulated holders for a real flagged batch: device ids start with 'sim-' and the UI labels them.

    Each gets a prescription, a purchase 3-9 days ago, ticked doses, and vitals before/after; about a third
    show a pulse rise after starting, so the body signal has something real-shaped to find."""
    import random

    rnd = random.Random(seed)
    clear_demo(conn, batch)
    now = datetime.now(timezone.utc)
    for i in range(n):
        dev = f"sim-{normalise_batch(batch)}-{i}"
        name = NAMES[i % len(NAMES)] + (f" {'BCDEFG'[i // len(NAMES) - 1]}." if i >= len(NAMES) else "")
        slots = rnd.choice([(1, 0, 1), (1, 0, 0), (0, 0, 1), (1, 1, 1)])
        days_ago = rnd.randint(3, 9)
        start = (date.today() - timedelta(days=days_ago)).isoformat()
        bought = (now - timedelta(days=days_ago, hours=rnd.randint(0, 6))).isoformat()
        cur = conn.execute("INSERT INTO plans (device, member, doctor, start_date, advice) VALUES (?,?,?,?,?)",
                           (dev, name, "Simulated", start, "[]"))
        med = conn.execute("""INSERT INTO plan_meds (plan_id, name, strength, food, morning, noon, night, days, as_needed, batch, bought_at, pharmacy, qty, language)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (cur.lastrowid, medicine, "", "", *slots, 30, 0, batch, bought, rnd.choice(CITIES), 30, "hi")).lastrowid
        # Doses ticked so far, ~85% adherent, today's past slots included, so next doses spread across the day
        # and only the people who really missed one show as "due now".
        hm = datetime.now().strftime("%H:%M")
        for d in range(days_ago, -1, -1):
            day = (date.today() - timedelta(days=d)).isoformat()
            for (slot, t), on in zip(care.SLOTS, slots):
                if d == 0 and t > hm:
                    continue
                if on and rnd.random() < 0.85:
                    conn.execute("INSERT OR IGNORE INTO doses (med_id, day, slot, taken_at) VALUES (?,?,?,?)", (med, day, slot, bought))
        # Vitals: 4 readings before, 4 after. Reactors get a pulse rise and a small SpO2 dip.
        reacts = i % 3 == 0
        base_p, base_o = rnd.randint(68, 82), rnd.randint(96, 99)
        for k in range(8):
            after = k >= 4
            at = (now - timedelta(days=days_ago + 6) + timedelta(days=k * (days_ago + 6) / 8)) if not after else \
                 (now - timedelta(days=days_ago) + timedelta(days=(k - 3) * days_ago / 5))
            p = base_p + rnd.randint(-3, 3) + (rnd.randint(12, 20) if reacts and after else 0)
            o = base_o - (rnd.randint(2, 4) if reacts and after else 0)
            conn.execute("INSERT INTO vitals (device, member, at, pulse, spo2, source, level) VALUES (?,?,?,?,?,?,?)",
                         (dev, name, at.strftime("%Y-%m-%dT%H:%M:%S.000Z"), p, min(o, 100), "simulated", "ok"))
    # A few pharmacy customers too (sold over the counter, no prescription on KinCare).
    for j in range(max(3, n // 6)):
        conn.execute("INSERT INTO sales (device, pharmacy, city, customer, phone, language, product, batch, batch_norm, sold_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (f"sim-shop-{normalise_batch(batch)}", "Sharma Medicos (simulated)", rnd.choice(CITIES), NAMES[(j + 7) % len(NAMES)], None, "hi",
                      medicine, batch, normalise_batch(batch), (now - timedelta(days=rnd.randint(1, 12))).isoformat()))
    conn.commit()
    return n


def clear_demo(conn: sqlite3.Connection, batch: str | None = None) -> None:
    like = f"sim-{normalise_batch(batch)}-%" if batch else "sim-%"
    shop = f"sim-shop-{normalise_batch(batch)}" if batch else "sim-shop-%"
    for (pid,) in conn.execute("SELECT id FROM plans WHERE device LIKE ?", (like,)).fetchall():
        conn.execute("DELETE FROM doses WHERE med_id IN (SELECT id FROM plan_meds WHERE plan_id = ?)", (pid,))
        conn.execute("DELETE FROM plan_meds WHERE plan_id = ?", (pid,))
    conn.execute("DELETE FROM plans WHERE device LIKE ?", (like,))
    conn.execute("DELETE FROM vitals WHERE device LIKE ?", (like,))
    conn.execute("DELETE FROM sales WHERE device LIKE ?", (shop,))
    if batch:
        conn.execute("DELETE FROM blast_alerts WHERE batch_norm = ?", (normalise_batch(batch),))
    conn.commit()
