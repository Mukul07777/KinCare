"""Ingest CDSCO's public NSQ / spurious data portal (cdscoonline.gov.in).

The portal behind https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug serves
month-by-month JSON (2019 onward). Raw responses are cached under
data/raw/portal/ so the database can be rebuilt offline.

Rows that duplicate a PDF-derived alert (same batch, alert month within two
months) enrich that row instead of being inserted twice, so PDF page links
are kept where we have them.

Usage: python -m ingest.portal [--refresh] [--since 2019]
Endpoint discovery credit: github.com/ankithsurapani/medcheck (data CC0).
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from rapidfuzz import fuzz

from db import connect
from ingest.parse import brand_of, maker_name
from matcher import normalise_batch

BASE = "https://cdscoonline.gov.in/CDSCO"
PORTAL_PAGE = {"nsq": f"{BASE}/viewPublicNSQDrug", "spurious": f"{BASE}/viewPublicNSQDrug"}
TABLE = {"nsq": "/filteredNsqDrugTable", "spurious": "/filteredSpuriousDrugTable"}
CACHE = Path(__file__).resolve().parents[2] / "data" / "raw" / "portal"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

session = requests.Session()
session.headers.update({"User-Agent": "KinCare/0.1 (drug alert lookup; Flip the Switch 2026)", "X-Requested-With": "XMLHttpRequest"})


def get_json(path: str, **params):
    for attempt in range(3):
        try:
            r = session.get(BASE + path, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            # The portal sometimes returns JSON encoded inside a JSON string.
            return (json.loads(data) if isinstance(data, str) else data), r.url
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def months_for(tab: str, since: int) -> list[str]:
    years, _ = get_json("/reportingYears", tab=tab)
    out = []
    for y in sorted(years):
        if int(y) < since:
            continue
        ms, _ = get_json("/publicReportingMonths", year=y, tab=tab)
        out += [f"{m}-{y}" for m in ms]
    return out


def fetch(tab: str, month: str, refresh: bool) -> dict:
    path = CACHE / tab / f"{month}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data, url = get_json(TABLE[tab], month=month, source="All", tab=tab)
    env = {"url": url, "tab": tab, "month": month, "fetched_at": datetime.now().isoformat(timespec="seconds"), "payload": data}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.4)  # be polite to a government server
    return env


def ym(month_label: str) -> str:
    """'Sep-2026' or 'SEP-2026' -> '2026-09'."""
    m, y = month_label.split("-")
    return f"{y}-{MONTHS.index(m[:3].upper()) + 1:02d}"


def month_gap(a: str, b: str) -> int:
    ya, ma = map(int, a.split("-"))
    yb, mb = map(int, b.split("-"))
    return abs((ya * 12 + ma) - (yb * 12 + mb))


def clean(s) -> str:
    return " ".join(str(s or "").replace("�", "'").split())


def load(refresh: bool = False, since: int = 2019) -> dict:
    conn = connect()
    added = enriched = 0
    for tab in ("nsq", "spurious"):
        for month in months_for(tab, since):
            env = fetch(tab, month, refresh)
            rows = env["payload"].get("aaData") or []
            alert_month = ym(month)
            title = f"CDSCO portal: {'spurious' if tab == 'spurious' else 'NSQ'} list for {month}"
            doc = conn.execute("SELECT id FROM documents WHERE url = ?", (env["url"],)).fetchone()
            if doc:
                continue  # already ingested this month
            cur = conn.execute(
                "INSERT INTO documents (title, source, alert_month, published, url, rows) VALUES (?,?,?,?,?,?)",
                (title, f"portal_{tab}", alert_month, env["fetched_at"][:10], env["url"], len(rows)),
            )
            doc_id = cur.lastrowid
            for r in rows:
                product = clean(r.get("str_product_name") or r.get("product_name_from_dtl"))
                batch = clean(r.get("str_batch_no"))
                if not product or not batch or batch in ("-", "NA"):
                    continue
                bn = normalise_batch(batch)
                brand = clean(r.get("str_brand_name")).strip("() ") or brand_of(product)
                maker_full = clean(r.get("str_manufactured_by"))
                lab_source = clean(r.get("str_reporting_source")).lower()
                source = "cdsco_spurious" if tab == "spurious" else ("state_nsq" if "state" in lab_source else "cdsco_nsq")

                # Same batch, close month AND same medicine: different products can share a batch code.
                dup = next(
                    (d for d in conn.execute("SELECT id, alert_month, brand, product_name, document_id FROM alerts WHERE batch_norm = ?", (bn,)).fetchall()
                     if d["document_id"] != doc_id and month_gap(d["alert_month"], alert_month) <= 2
                     and fuzz.token_set_ratio(d["product_name"].lower(), product.lower()) >= 60),
                    None,
                )
                if dup:
                    conn.execute("UPDATE alerts SET brand = ? WHERE id = ?", (brand or dup["brand"], dup["id"]))
                    enriched += 1
                    continue

                remarks = " ".join(filter(None, [clean(r.get("str_nsq_remarks")), clean(r.get("str_firm_reply"))]))
                conn.execute(
                    """INSERT OR IGNORE INTO alerts (document_id, source, category, product_name, brand, batch_no, batch_norm,
                       mfg_date, expiry, manufacturer, manufacturer_full, reason, reported_by, remarks, alert_month, alert_url, pdf_page)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                    (doc_id, source, "spurious" if tab == "spurious" else "nsq", product, brand, batch, bn,
                     clean(r.get("dt_manufacturing_date")), clean(r.get("dt_expiry_date")),
                     maker_name(maker_full) if maker_full else "", maker_full, clean(r.get("str_nsq_result")),
                     clean(r.get("str_reported_by_lab_or_state")), remarks, alert_month, PORTAL_PAGE[tab]),
                )
                added += 1
            conn.commit()
            print(f"  {tab:8} {month}: {len(rows)} rows")
    total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    print(f"Portal: added {added}, enriched {enriched} existing rows. Alerts in DB: {total}")
    return {"added": added, "enriched": enriched, "total": total}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--since", type=int, default=2019)
    a = ap.parse_args()
    load(a.refresh, a.since)
