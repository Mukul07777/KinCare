"""Same medicine, lower price: brands with identical salts, strengths and form, ranked per tablet / ml.

KinCare only shows prices. Switching brand is a decision for the patient's doctor or pharmacist.
"""
import re
from statistics import median

from ingest.medicines import maker_key

_maker_alerts: dict[str, dict] | None = None


def maker_alerts(conn) -> dict[str, dict]:
    """maker_key -> CDSCO alert record. Built once; exact key match only, so no maker inherits another's alerts."""
    global _maker_alerts
    if _maker_alerts is None:
        out: dict[str, dict] = {}
        for r in conn.execute("SELECT manufacturer, category, alert_month FROM alerts WHERE manufacturer IS NOT NULL"):
            k = maker_key(r["manufacturer"])
            if not k:
                continue
            d = out.setdefault(k, {"alerts": 0, "spurious": 0, "last": None})
            d["alerts"] += 1
            d["spurious"] += r["category"] == "spurious"
            d["last"] = max(d["last"] or "", r["alert_month"])
        _maker_alerts = out
    return _maker_alerts


def _row(conn, r) -> dict:
    d = dict(r)
    d["maker_record"] = maker_alerts(conn).get(d.pop("maker_key") or "", {"alerts": 0, "spurious": 0, "last": None})
    d.pop("name_lc", None)
    return d


# Substring search over 2.46 lakh names. A plain LIKE '%word%' scans every row (~200 ms a keystroke);
# a trigram FTS5 index answers the same LIKE from the index (SQLite >= 3.34).
_fts_ready = False


def ensure_fts(conn) -> None:
    """Build the trigram index once (a few seconds; run in the background at startup). Rebuilt if the list changes."""
    global _fts_ready
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS medicines_fts USING fts5(name_lc, content='medicines', content_rowid='id', tokenize='trigram')")
    conn.execute("CREATE TABLE IF NOT EXISTS fts_state (name TEXT PRIMARY KEY, n INTEGER)")
    n = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    built = conn.execute("SELECT n FROM fts_state WHERE name = 'medicines'").fetchone()
    if not built or built[0] != n:
        conn.execute("INSERT INTO medicines_fts(medicines_fts) VALUES ('rebuild')")
        conn.execute("INSERT OR REPLACE INTO fts_state VALUES ('medicines', ?)", (n,))
    _fts_ready = True


def search(conn, q: str, limit: int = 10) -> list[dict]:
    q = " ".join(q.lower().split())
    if len(q) < 2:
        return []
    like = q.replace("%", "").replace("_", "")
    words = like.split()[:5]
    # Every word must appear in the name ("atorva 10" finds "Atorva 10mg Tablet"), or the query is a salt name.
    names = " AND ".join(["name_lc LIKE ?"] * len(words))
    if _fts_ready and any(len(w) >= 3 for w in words):
        where = f"id IN (SELECT rowid FROM medicines_fts WHERE {names})"
    else:
        where = f"({names})"
    rows = conn.execute(
        f"""SELECT * FROM medicines WHERE {where} OR (salt_key >= ? AND salt_key < ?)
            ORDER BY (name_lc LIKE ?) DESC, length(name), id LIMIT ?""",
        (*[f"%{w}%" for w in words], like, like + "￿", f"{like}%", limit)).fetchall()
    return [_row(conn, r) for r in rows]


def alternatives(conn, mid: int, limit: int = 20) -> dict | None:
    m = conn.execute("SELECT * FROM medicines WHERE id = ?", (mid,)).fetchone()
    if not m:
        return None
    same = conn.execute("SELECT * FROM medicines WHERE salt_key = ? AND form = ? AND unit_price IS NOT NULL ORDER BY unit_price",
                        (m["salt_key"], m["form"])).fetchall()
    prices = [r["unit_price"] for r in same]
    alts = [_row(conn, r) for r in same if r["id"] != mid]
    me = _row(conn, m)
    for a in alts:
        a["saving_pct"] = round((1 - a["unit_price"] / me["unit_price"]) * 100) if me["unit_price"] else None
    clean = next((a for a in alts if a["maker_record"]["alerts"] == 0), None)
    return {
        "medicine": me,
        "brands": len(same),
        "rank": next((i + 1 for i, r in enumerate(same) if r["id"] == mid), None),
        "unit_price": {"min": prices[0] if prices else None, "median": round(median(prices), 3) if prices else None,
                       "max": prices[-1] if prices else None},
        "cheapest_clean": clean,
        "alternatives": alts[:limit],
    }


_STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|iu|ml|%)", re.I)


def match_plan_med(conn, name: str, strength: str | None):
    """Find the brand a prescription line most likely means: exact brand name, else the salt at that strength."""
    n = " ".join((name or "").lower().split())
    if not n:
        return None
    s = _STRENGTH.search(f"{name} {strength or ''}")
    strength_txt = f"{s.group(1)}{s.group(2).lower()}" if s else None
    by_name = "SELECT * FROM medicines WHERE name_lc LIKE ? AND form LIKE 'tablet%' ORDER BY length(name) LIMIT 1"
    tries = [(by_name, (f"{n}%{strength_txt}%",))] if strength_txt else []
    tries.append((by_name, (f"{n}%",)))
    if strength_txt:
        # Brand stem + strength from the salt: "Warf 5mg" -> "Warf 5 Tablet", "Crocin 500" -> "Crocin Advance" (paracetamol 500mg).
        stem = re.sub(r"\s*\d.*$", "", n).strip()
        if len(stem) >= 3:
            tries.append(("SELECT * FROM medicines WHERE name_lc LIKE ? AND salt_key LIKE ? AND form LIKE 'tablet%' ORDER BY length(name) LIMIT 1",
                          (f"{stem} %", f"%({strength_txt})%")))
    for sql, args in tries:
        r = conn.execute(sql, args).fetchone()
        if r:
            return r, False
    if strength_txt:  # written as a generic name: price it at the median brand, and say it's an estimate
        same = conn.execute("SELECT * FROM medicines WHERE salt_key = ? AND form = 'tablet' AND unit_price IS NOT NULL ORDER BY unit_price",
                            (f"{n} ({strength_txt})",)).fetchall()
        if same:
            return same[len(same) // 2], True
    return None, False


def plan_savings(conn, meds: list[dict]) -> dict:
    """Monthly cost of the patient's prescribed medicines vs the cheapest brand with the same salts and form."""
    items, now_total, best_total = [], 0.0, 0.0
    for med in meds:
        per_day = (med.get("morning") or 0) + (med.get("noon") or 0) + (med.get("night") or 0)
        r, estimated = match_plan_med(conn, med["name"], med.get("strength"))
        if not r or not per_day or not r["unit_price"]:
            items.append({"name": med["name"], "matched": None})
            continue
        # Cheapest brand whose maker has no CDSCO alerts on record; cheaper must not mean riskier.
        record = maker_alerts(conn)
        best = next((b for b in conn.execute("SELECT * FROM medicines WHERE salt_key = ? AND form = ? AND unit_price IS NOT NULL ORDER BY unit_price",
                                             (r["salt_key"], r["form"])) if not record.get(b["maker_key"] or "")), r)
        now_m, best_m = r["unit_price"] * per_day * 30, best["unit_price"] * per_day * 30
        now_total += now_m
        best_total += best_m
        items.append({"name": med["name"], "matched": _row(conn, r), "estimated": estimated, "cheapest": _row(conn, best),
                      "monthly_now": round(now_m), "monthly_cheapest": round(best_m)})
    return {"items": items, "monthly_now": round(now_total), "monthly_cheapest": round(best_total),
            "yearly_saving": round((now_total - best_total) * 12)}
