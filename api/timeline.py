"""The recall gap, measured on real CDSCO data: how long a failed batch is out in the world before it is listed,
and how much shelf life it still has when it is. Those months are the window in which people are still taking it.

Dates on alerts come in several shapes ("Aug-2025", "08/2025", "2025-08", "Sept 2024"); anything unreadable is skipped,
and the response says how many alerts each number is based on.
"""
import re
import sqlite3
import threading
from statistics import median

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_cache: dict | None = None
_key: tuple | None = None
_fill = threading.Lock()


def month_index(s: str | None) -> int | None:
    """'Aug-2025' / '08/2025' / '2025-08' / 'Sept. 2024' -> months since year 0. None if unreadable or implausible."""
    if not s:
        return None
    t = s.strip().lower()
    y = m = None
    if mt := re.search(r"([a-z]{3,9})\.?[\s\-/,]*'?(\d{2,4})", t):
        m, y = MONTHS.get(mt.group(1)[:3]), int(mt.group(2))
    elif mt := re.search(r"\b(\d{4})[\-/.](\d{1,2})\b", t):
        y, m = int(mt.group(1)), int(mt.group(2))
    elif mt := re.search(r"\b(\d{1,2})[\-/.](\d{2,4})\b", t):
        m, y = int(mt.group(1)), int(mt.group(2))
    if not m or not y or not 1 <= m <= 12:
        return None
    if y < 100:
        y += 2000
    if not 2010 <= y <= 2040:
        return None
    return y * 12 + m - 1


def compute(conn: sqlite3.Connection) -> dict:
    lags, shelf, expired_before = [], [], 0
    by_year: dict[int, list[int]] = {}
    hist = [0] * 8  # 0-3, 3-6, 6-9, 9-12, 12-18, 18-24, 24-36, 36+ months
    edges = [3, 6, 9, 12, 18, 24, 36]
    for mfg, exp, listed in conn.execute("SELECT mfg_date, expiry, alert_month FROM alerts"):
        a = month_index(listed)
        if a is None:
            continue
        mi, ei = month_index(mfg), month_index(exp)
        if mi is not None and 0 <= a - mi <= 72:
            lag = a - mi
            lags.append(lag)
            by_year.setdefault(a // 12, []).append(lag)
            hist[next((i for i, e in enumerate(edges) if lag < e), len(edges))] += 1
        if ei is not None and mi is not None and ei > mi:
            left = ei - a
            if left < 0:
                expired_before += 1
            else:
                shelf.append(left)
    in_date = len(shelf)
    total_exp = in_date + expired_before
    return {
        "alerts_used_lag": len(lags),
        "alerts_used_shelf": total_exp,
        "median_lag_months": median(lags) if lags else None,
        "p75_lag_months": sorted(lags)[int(len(lags) * 0.75)] if lags else None,
        "median_shelf_left_months": median(shelf) if shelf else None,
        "pct_in_date_when_listed": round(100 * in_date / total_exp, 1) if total_exp else None,
        "in_date_when_listed": in_date,
        "histogram": [{"label": l, "n": n} for l, n in zip(["0–3", "3–6", "6–9", "9–12", "12–18", "18–24", "24–36", "36+"], hist)],
        "by_year": [{"year": y, "median_lag_months": median(v), "n": len(v)} for y, v in sorted(by_year.items()) if len(v) >= 20],
        "source": "CDSCO + state NSQ / spurious alerts, manufacture date and expiry as printed on each alert",
    }


def recall_gap(conn: sqlite3.Connection, refresh: bool = False) -> dict:
    """Cached until the alert table changes (a nightly ingest must move the headline number); single flight."""
    global _cache, _key
    key = tuple(conn.execute("SELECT COUNT(*), MAX(id) FROM alerts").fetchone())
    if _cache is None or refresh or key != _key:
        with _fill:
            if _cache is None or refresh or key != _key:
                _cache, _key = compute(conn), key
    return _cache
