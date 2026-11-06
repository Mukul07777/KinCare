"""Early Signal: patients as sensors.

Symptom reports are grouped by batch and tested with the same disproportionality
method pharmacovigilance agencies use (PRR with the Evans criteria: a >= 3,
PRR >= 2, chi-square >= 4). A batch whose reports carry a symptom far more often
than every other batch is a signal, possibly before any regulator list names it.

A signal is a reason for a lab to test the batch. It is not proof, and we say so.
"""
from collections import Counter

from checkin import RED_FLAGS, SYMPTOMS

MIN_REPORTS = 3  # distinct reporters before a batch is shown at all


def _prr(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """PRR and Yates chi-square for the 2x2 table [[a, b], [c, d]]."""
    if 0 in (a, b, c, d):  # Haldane correction keeps the ratio finite
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    n = a + b + c + d
    prr = (a / (a + b)) / (c / (c + d))
    chi2 = n * (max(abs(a * d - b * c) - n / 2, 0)) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
    return round(prr, 2), round(chi2, 2)


def detect(conn) -> list[dict]:
    reports = [dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY created_at")]
    for r in reports:
        r["sym"] = set(filter(None, r["symptoms"].split(",")))
    total = len(reports)
    background = Counter(s for r in reports for s in r["sym"])

    groups: dict[str, list[dict]] = {}
    for r in reports:
        groups.setdefault(r["batch_norm"], []).append(r)

    out = []
    for key, rs in groups.items():
        n = len(rs)
        if n < MIN_REPORTS:
            continue
        others = total - n
        counts = Counter(s for r in rs for s in r["sym"])
        method = "prr" if others >= MIN_REPORTS else "cluster"
        symptoms = []
        for s, a in counts.most_common():
            c = background[s] - a
            if method == "prr":
                prr, chi2 = _prr(a, n - a, c, others - c)
                flagged = a >= 3 and prr >= 2 and chi2 >= 4
            else:  # too little background to compare against: fall back to a plain cluster rule
                prr, chi2 = None, None
                flagged = a >= 3 and a / n >= 0.5
            label = SYMPTOMS.get(s, (s, s))
            symptoms.append({"key": s, "en": label[0], "hi": label[1], "n": a, "share": round(a / n, 2),
                             "prr": prr, "chi2": chi2, "flagged": flagged, "red_flag": s in RED_FLAGS})

        red = sum(1 for r in rs if r["sym"] & RED_FLAGS)
        level = "urgent" if red >= 2 else "signal" if any(x["flagged"] for x in symptoms) else "watch"
        listed = conn.execute(
            "SELECT alert_month, category, product_name FROM alerts WHERE batch_norm = ? ORDER BY alert_month LIMIT 1", (key,)
        ).fetchone()
        first, last = rs[0]["created_at"], rs[-1]["created_at"]
        out.append({
            "batch": Counter(r["batch"] for r in rs).most_common(1)[0][0],
            "batch_norm": key,
            "brand": _common(r["brand"] for r in rs),
            "maker": _common(r["maker"] for r in rs),
            "reports": n,
            "red_flag_reports": red,
            "cities": sorted({r["city"] for r in rs if r["city"]}),
            "first_report": first,
            "last_report": last,
            "level": level,
            "method": method,
            "symptoms": symptoms,
            "not_working": counts.get("no_effect", 0),
            "simulated": all(r["origin"] == "simulated" for r in rs),
            "regulator": dict(listed) if listed else None,
            "ahead_of_regulator": listed is None or listed["alert_month"] > first[:7],
        })
    rank = {"urgent": 0, "signal": 1, "watch": 2}
    out.sort(key=lambda s: (rank[s["level"]], -s["reports"]))
    return out


def _common(values) -> str | None:
    c = Counter(v for v in values if v)
    return c.most_common(1)[0][0] if c else None


def summary(conn) -> dict:
    one = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "reports": one("SELECT COUNT(*) FROM reports"),
        "batches": one("SELECT COUNT(DISTINCT batch_norm) FROM reports"),
        "cities": one("SELECT COUNT(DISTINCT city) FROM reports WHERE city IS NOT NULL AND city != ''"),
        "min_reports": MIN_REPORTS,
    }
