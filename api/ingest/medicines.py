"""Ingest the Indian Medicine Dataset (253,973 brands with MRP, maker, pack and salt composition).

Used to find the same medicine for less: brands with the *identical* salts, strengths and dosage
form (an SR tablet never matches a plain tablet), compared per tablet / per ml, not per pack.
Each maker is linked to its record in KinCare's CDSCO alert database, so cheaper never quietly
means riskier.

Source: github.com/junioralive/Indian-Medicine-Dataset (MIT). Cached under data/raw/medicines/.
Usage: python -m ingest.medicines [--refresh]
"""
import argparse
import csv
import re
from pathlib import Path

import requests

from db import connect
from matcher import normalise_maker

URL = "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"
RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "medicines" / "indian_medicine_data.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    name_lc TEXT NOT NULL,
    price REAL,
    maker TEXT,
    maker_key TEXT,
    pack TEXT,
    salts TEXT NOT NULL,
    salt_key TEXT NOT NULL,
    form TEXT NOT NULL,
    qty REAL,
    unit TEXT,
    unit_price REAL
);
CREATE INDEX IF NOT EXISTS idx_med_salt ON medicines(salt_key, form, unit_price);
CREATE INDEX IF NOT EXISTS idx_med_name ON medicines(name_lc);
"""

_PACK = re.compile(r"^\s*\w+ of ([\d.]+)\s*(.*)$", re.I)
_UNITS = {"ml", "gm", "g", "mg", "kg", "l"}


def maker_key(name: str | None) -> str:
    return normalise_maker(name).replace(" ", "")


def salt_part(s: str) -> str:
    """'Amoxycillin  (500mg) ' -> 'amoxycillin (500mg)'; spacing and case never decide a match."""
    s = " ".join(s.lower().split())
    return re.sub(r"\s*\(\s*", " (", re.sub(r"\s*\)", ")", s)).strip()


def parse_pack(label: str) -> tuple[str, float | None, str]:
    """'strip of 10 tablets' -> ('tablet', 10, 'tablet'); 'bottle of 100 ml Syrup' -> ('ml syrup', 100, 'ml')."""
    m = _PACK.match(label or "")
    if not m:
        return (" ".join((label or "").lower().split()) or "unknown", None, "pack")
    qty, rest = float(m.group(1)), m.group(2).lower().split()
    # Plurals don't change the form ("tablets" = "tablet"), release type does ("tablet sr").
    rest = [w[:-1] if w.endswith("s") and len(w) > 3 and w not in ("plus",) else w for w in rest]
    form = " ".join(rest) or "unit"
    unit = rest[0] if rest and rest[0] in _UNITS else (rest[0] if rest else "unit")
    return form, qty, unit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.refresh or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(URL, timeout=300)
        r.raise_for_status()
        RAW.write_bytes(r.content)

    conn = connect()
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM medicines")
    rows = []
    with open(RAW, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Is_discontinued"].strip().upper() == "TRUE":
                continue
            parts = [salt_part(p) for p in (r["short_composition1"], r["short_composition2"]) if p and p.strip()]
            if not parts:
                continue
            try:
                price = float(r["price(₹)"])
            except ValueError:
                price = None
            form, qty, unit = parse_pack(r["pack_size_label"])
            rows.append((int(r["id"]), r["name"].strip(), r["name"].strip().lower(), price, r["manufacturer_name"].strip(),
                         maker_key(r["manufacturer_name"]), r["pack_size_label"].strip(), " + ".join(parts), "+".join(sorted(parts)),
                         form, qty, unit, round(price / qty, 4) if price and qty else None))
    conn.executemany("INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    groups = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM medicines GROUP BY salt_key, form HAVING COUNT(*) > 1)").fetchone()[0]
    print(f"loaded {len(rows)} medicines in use; {groups} salt+form groups have more than one brand to compare")


if __name__ == "__main__":
    main()
