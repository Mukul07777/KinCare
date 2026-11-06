"""Recall blast radius: who holds a flagged batch, next dose first, body signal."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

import blast
import roles

from core import _log_note, _plans, _refresh, alert_device, conn, current_account, now, require, rows, run_check

router = APIRouter()


# ---- recall blast radius: who holds a flagged batch, next dose first, body signal ----

@router.get("/api/insights/recall-gap")
def recall_gap():
    """Months from manufacture to CDSCO listing, and shelf life left when listed, across every alert."""
    import timeline

    return timeline.recall_gap(conn)


@router.get("/api/blast")
def blast_inbox(_: dict = Depends(require("holders.view"))):
    """Flagged batches that someone KinCare knows is holding."""
    return blast.flagged_with_holders(conn)


@router.get("/api/blast/{batch}")
def blast_view(batch: str, who: dict = Depends(require("holders.view"))):
    check = run_check(batch, None, None)
    if not check["matches"]:
        raise HTTPException(404, "This batch is not on any alert list KinCare tracks")
    # Names, phones and next doses of everyone holding the batch: every look is logged.
    roles.audit(conn, who["actor"], "holders.view", batch)
    conn.commit()
    a = check["matches"][0]["alert"]
    return {"alert": a, "explain": check["matches"][0]["explain"], **blast.exposure(conn, batch)}


@router.post("/api/blast/{batch}/alert")
def blast_alert(batch: str, who: dict = Depends(require("holders.alert"))):
    """Alert every holder not yet told, soonest next dose first. Simulated holders are marked, never messaged."""
    import notify

    check = run_check(batch, None, None)
    if not check["matches"]:
        raise HTTPException(404, "This batch is not on any alert list KinCare tracks")
    alert = check["matches"][0]["alert"]
    ex = blast.exposure(conn, batch)
    out = []
    for h in ex["holders"]:
        if h["alert"]:
            continue
        if h["simulated"]:
            status = "simulated"
        else:
            status = "outbox"
            if h["phone"]:
                status = _log_note("whatsapp", h["name"], h["phone"], "hi", batch, notify.whatsapp_text(alert, batch, h["name"], "hi"), alert["id"])
            if h["source"] == "care":
                dev = conn.execute("SELECT p.device FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE m.id = ?", (int(h["key"].split(":")[1]),)).fetchone()
                if dev and alert_device(dev[0], f"⛔ Stop: {h['medicine']} batch {batch} is flagged",
                                     "Don't take the next dose. Speak to your pharmacist or doctor.", "/care", f"blast-{h['key']}") and status != "sent":
                    status = "push"
        blast.mark(conn, ex["batch"], h["key"], status)
        out.append({"key": h["key"], "status": status, "minutes": h["minutes"]})
    roles.audit(conn, who["actor"], "holders.alert", batch, f"{len(out)} holders")
    conn.commit()
    return {"alerted": out, "count": len(out)}


@router.post("/api/blast/{batch}/demo")
def blast_demo(batch: str, holders: int = Query(24, ge=3, le=60), _: dict = Depends(require("demo.seed"))):
    """Seed clearly-labelled simulated holders (with vitals) for a real flagged batch, for the stage demo."""
    check = run_check(batch, None, None)
    if not check["matches"]:
        raise HTTPException(404, "Pick a batch that is on an alert list")
    a = check["matches"][0]["alert"]
    return {"seeded": blast.seed_demo(conn, a["batch_no"], a.get("brand") or a["product_name"], holders)}


@router.delete("/api/blast/{batch}/demo")
def blast_demo_clear(batch: str, _: dict = Depends(require("demo.seed"))):
    blast.clear_demo(conn, batch)
    return {"ok": True}


@router.get("/api/care/batch-effects")
def care_batch_effects(account: str = Depends(current_account)):
    """For each bought medicine: vitals in the 2 weeks before starting this batch vs since."""
    dev = account
    out = []
    for p in _plans(dev):
        for m in p["medicines"]:
            if m.get("bought_at") and m.get("batch"):
                b = blast.body_signal(conn, dev, p["member"], m["bought_at"])
                if b:
                    out.append({"med_id": m["id"], "name": m["name"], "member": p["member"], "batch": m["batch"], "since": m["bought_at"], **b})
    return out


@router.get("/api/admin/overview")
def admin_overview(_: dict = Depends(require("admin.view"))):
    import billing
    import signals

    one = lambda sql, a=(): conn.execute(sql, a).fetchone()[0]
    week = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-7 days')"
    devices = one("""SELECT COUNT(*) FROM (SELECT device FROM watchlist UNION SELECT device FROM vitals UNION SELECT device FROM plans
                     UNION SELECT device FROM reports UNION SELECT device FROM contacts UNION SELECT device FROM payments)""")
    # Active = paid within one billing period; a yearly plan counts as a twelfth of its price per month.
    paid = []
    for p in rows("""SELECT plan, COUNT(*) AS n, SUM(amount) AS amount, MIN(paid_at) AS first FROM payments WHERE status = 'paid'
                     AND paid_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-366 days') GROUP BY plan"""):
        yearly = billing.PLANS.get(p["plan"], {}).get("interval") == "year"
        if not yearly:
            p = {**p, **conn.execute("""SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS amount FROM payments WHERE status = 'paid' AND plan = ?
                                       AND paid_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-31 days')""", (p["plan"],)).fetchone()}
        if p["n"]:
            paid.append({"plan": p["plan"], "n": p["n"], "amount": p["amount"] // 12 if yearly else p["amount"]})
    sig = signals.detect(conn)
    return {
        "users": devices,
        "payments": {
            "ready": billing.ready(), "test_mode": billing.test_mode(),
            "mrr": sum(p["amount"] for p in paid) // 100,
            "active_by_plan": [{**p, "name": billing.PLANS.get(p["plan"], {}).get("name", p["plan"])} for p in paid],
            "lifetime": one("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'paid'") // 100,
            "recent": rows("SELECT plan, amount, currency, status, email, created_at, paid_at FROM payments ORDER BY created_at DESC LIMIT 10"),
        },
        "sos": rows("SELECT id, member, lat, lng, delivered, at, resolved_at FROM sos_events ORDER BY at DESC LIMIT 10"),
        "sos_open": one("SELECT COUNT(*) FROM sos_events WHERE resolved_at IS NULL"),
        "vitals_urgent_7d": one(f"SELECT COUNT(*) FROM vitals WHERE level = 'urgent' AND at >= {week}"),
        "vitals_7d": one(f"SELECT COUNT(*) FROM vitals WHERE at >= {week}"),
        "checkins_urgent": one("SELECT COUNT(*) FROM checkins WHERE triage = 'urgent' AND reviewed = 0"),
        "signals": {"flagged": sum(s["level"] != "watch" for s in sig), "reports": one("SELECT COUNT(*) FROM reports")},
        "watchlist": one("SELECT COUNT(*) FROM watchlist"),
        "flagged_watch": one("SELECT COUNT(*) FROM watchlist WHERE last_verdict = 'alert_found'"),
        "data": {**rows("SELECT COUNT(*) AS alerts, MIN(alert_month) AS start, MAX(alert_month) AS end FROM alerts")[0],
                 "last_ingest": one("SELECT MAX(ingested_at) FROM documents")},
        "recall_runs": one("SELECT COUNT(DISTINCT run_id) FROM events"),
        "notifications": one("SELECT COUNT(*) FROM notifications"),
    }


@router.post("/api/admin/sos/{sid}/resolve")
def admin_sos_resolve(sid: int, _: dict = Depends(require("admin.view"))):
    conn.execute("UPDATE sos_events SET resolved_at = ? WHERE id = ?", (now(), sid))
    conn.commit()
    return {"ok": True}


@router.post("/api/admin/ingest")
def admin_ingest(tasks: BackgroundTasks, _: dict = Depends(require("ingest.run"))):
    tasks.add_task(_refresh)
    return {"started": True}
