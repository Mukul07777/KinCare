"""Drug-controller dashboard: one screen for a state drug controller (or CDSCO) that joins what
KinCare sees on the ground with the regulator's own alerts.

- Alerts by testing state: volume, trend, what fails, which makers, how fast failures reach the list
- Flagged batches still in homes (blast radius) and how many holders have been alerted
- Copied pack codes (fake-pack radar) and patient symptom signals ahead of the regulator
- An action queue that ranks all of it, most urgent first
"""
import sqlite3
import threading
from collections import Counter
from datetime import datetime
from statistics import median

import blast
import insights
import packs
import signals
import timeline


def _month(ym: str) -> int:
    return int(ym[:4]) * 12 + int(ym[5:7]) - 1


def _label(mi: int) -> str:
    return f"{mi // 12}-{mi % 12 + 1:02d}"


_cache: dict[tuple, dict] = {}
_fill = threading.Lock()


def overview(conn: sqlite3.Connection, state: str | None = None) -> dict:
    # The regulator half only changes when an ingest adds alerts. Classifying all ~7k of them by regex took ~0.5 s a
    # request (12 s p95 under 32 parallel clients), so it is cached per state until the alert table changes.
    # The ground half (holders, alerts sent, copied codes, signals) is always live.
    key = (state, *conn.execute("SELECT COUNT(*), MAX(id) FROM alerts").fetchone())
    if key not in _cache:
        with _fill:  # single flight: 40 cold requests at once compute it once, not 40 times
            if key not in _cache:
                if len(_cache) > 64:
                    _cache.clear()
                _cache[key] = _regulator(conn, state)
    reg, ground = _cache[key], _ground(conn)
    return {
        **reg,
        "kpis": {**reg["kpis"], **ground["kpis"]},
        "held": ground["held"], "actions": ground["actions"],
        "scope_note": "Alerts are filtered by the state of the testing lab. Ground data (holders, copied codes, signals) is shown for all of India.",
        "generated_at": datetime.now().isoformat(timespec="minutes"),
    }


def _regulator(conn: sqlite3.Connection, state: str | None) -> dict:
    rows = [dict(r) for r in conn.execute(
        "SELECT batch_norm, batch_no, product_name, brand, manufacturer, reason, category, reported_by, alert_month, mfg_date FROM alerts")]
    for r in rows:
        r["state"] = insights.state_of(r["reported_by"])
    states = Counter(r["state"] for r in rows if r["state"])
    mine = [r for r in rows if r["state"] == state] if state else rows
    latest = max((_month(r["alert_month"]) for r in rows), default=0)

    # Alerts, last 18 months, plus the year-on-year change.
    months = [_label(latest - i) for i in range(17, -1, -1)]
    per_month = Counter(r["alert_month"] for r in mine)
    last12 = sum(per_month.get(_label(latest - i), 0) for i in range(12))
    prev12 = sum(per_month.get(_label(latest - 12 - i), 0) for i in range(12))

    # What fails, which drug groups, which makers (last 24 months).
    recent = [r for r in mine if _month(r["alert_month"]) > latest - 24]
    fails, groups, makers, critical = Counter(), Counter(), Counter(), 0
    for r in recent:
        f = insights.failures_of(r["reason"], r["category"])
        fails.update(x["label"] for x in f)
        critical += f[0]["severity"] == "critical"
        if (g := insights.group_of(r["product_name"])) != "Other":
            groups[g] += 1
        if r["manufacturer"] and "investigation" not in r["manufacturer"].lower():
            makers[r["manufacturer"].strip(" :")] += 1

    # How long a failed batch takes to reach the list, in this state.
    lags = []
    for r in mine:
        a, m = timeline.month_index(r["alert_month"]), timeline.month_index(r["mfg_date"])
        if a is not None and m is not None and 0 <= a - m <= 72:
            lags.append(a - m)

    top = lambda c, n: [{"name": k, "n": v} for k, v in c.most_common(n)]  # noqa: E731
    return {
        "state": state,
        "states": [{"name": k, "n": v} for k, v in states.most_common()],
        "as_of": _label(latest),
        "kpis": {
            "alerts_12m": last12, "alerts_prev_12m": prev12, "spurious_12m": sum(1 for r in mine if r["category"] == "spurious" and _month(r["alert_month"]) > latest - 12),
            "critical_24m": critical, "median_lag_months": median(lags) if lags else None, "lag_sample": len(lags),
        },
        "trend": [{"month": m, "n": per_month.get(m, 0)} for m in months],
        "failures": top(fails, 6), "groups": top(groups, 6), "makers": top(makers, 8),
    }


def _ground(conn: sqlite3.Connection) -> dict:
    # On the ground: flagged batches people hold, copied codes, symptom signals, urgent check-ins.
    held = []
    for b in blast.flagged_with_holders(conn, limit=40):
        ex = blast.exposure(conn, b["batch_no"])["summary"]
        held.append({**b, "holders": ex["holders"], "alerted": ex["alerted"], "due_24h": ex["due_24h"], "reacting": ex["reacting"], "simulated": ex["simulated"]})
    held.sort(key=lambda h: (-(h["holders"] - h["alerted"]), -h["holders"]))
    radar = packs.radar(conn)
    sig = [s for s in signals.detect(conn) if s["level"] != "watch"]
    urgent_checkins = conn.execute("SELECT COUNT(*) FROM checkins WHERE triage = 'urgent' AND reviewed = 0").fetchone()[0]

    actions = []
    for h in held:
        if h["holders"] > h["alerted"]:
            left = h["holders"] - h["alerted"]
            actions.append({"kind": "recall", "severity": 0 if h["category"] == "spurious" or h["due_24h"] else 1,
                            "title": f"{left} {'person still holds' if left == 1 else 'people still hold'} {h['medicine']} batch {h['batch_no']}",
                            "detail": f"{h['category'].upper()} · {h['month']} · {h['due_24h']} {'dose' if h['due_24h'] == 1 else 'doses'} due in 24 h", "href": f"/blast?batch={h['batch_norm']}",
                            "simulated": bool(h["simulated"])})
    for r in radar["rings"]:
        if r["level"] == "clone":
            actions.append({"kind": "counterfeit", "severity": 0, "title": f"Copied pack code {r['serial']} in {len(r['cities'])} cities",
                            "detail": r["reasons"][0]["text"] if r["reasons"] else "", "href": "/radar", "simulated": r["simulated"]})
    for s in sig:
        actions.append({"kind": "signal", "severity": 0 if s["level"] == "urgent" else 1,
                        "title": f"{s['reports']} patients report problems with {s['brand'] or 'batch'} {s['batch']}",
                        "detail": ("Not on any regulator list yet: test this batch" if s["ahead_of_regulator"] else "Already on a regulator list"),
                        "href": "/signals", "simulated": s["simulated"]})
    if urgent_checkins:
        actions.append({"kind": "checkin", "severity": 0, "title": f"{urgent_checkins} urgent patient check-ins after a recall",
                        "detail": "Pharmacists have not reviewed them yet", "href": "/pharmacy", "simulated": False})
    actions.sort(key=lambda a: (a["severity"], a["simulated"]))

    return {
        "kpis": {
            "batches_in_homes": len(held), "people_holding": sum(h["holders"] for h in held), "people_alerted": sum(h["alerted"] for h in held),
            "copied_codes": radar["clones"], "signals": len(sig), "urgent_checkins": urgent_checkins,
        },
        "held": held[:10], "actions": actions[:12],
    }
