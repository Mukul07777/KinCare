"""OCR accuracy on labelled strip photos: does KinCare read the batch, expiry and brand a person reads off the strip?

    python bench_strips.py            # every photo in tests/strips/labels.csv
    python bench_strips.py --set real # only real phone photos

Labels are typed by a person from the strip (tests/strips/real/README.md). Results are printed per photo, summarised per
set ("real" phone photos vs "synthetic" demo prints, never mixed), and saved to data/strip_bench.json for /status.
"""
import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import ocr
from db import DB_PATH
from matcher import normalise_batch

HERE = Path(__file__).resolve().parent
LABELS = HERE / "tests" / "strips" / "labels.csv"
OUT = DB_PATH.parent / "strip_bench.json"


def _expiry(s: str | None) -> str | None:
    """'10/2027', '10-27', 'OCT 2027' -> '2027-10' so different spellings of one date compare equal."""
    if not s:
        return None
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{2,4})", s)
    if m:
        mm, yy = int(m.group(1)), int(m.group(2))
    elif (m := re.search(r"([A-Za-z]{3})\w*\s*[/\-.]?\s*(\d{2,4})", s)) and m.group(1).lower() in months:
        mm, yy = months.index(m.group(1).lower()) + 1, int(m.group(2))
    else:
        return None
    return f"{yy + 2000 if yy < 100 else yy}-{mm:02d}"


def _brand_ok(got: str | None, want: str) -> bool:
    """The first word of the brand is what matters for matching ("Telma" in "Telma H")."""
    g, w = (got or "").lower(), want.lower()
    return bool(g) and (w.split()[0].strip("-") in g or g.split()[0].strip("-") in w)


def run(only: str | None = None) -> dict:
    rows = [r for r in csv.DictReader(LABELS.open(encoding="utf-8")) if not only or r["set"] == only]
    results = []
    for r in rows:
        path = (LABELS.parent / r["file"]).resolve()
        if not path.exists():
            print(f"  missing: {r['file']}")
            continue
        t = time.perf_counter()
        try:
            f = ocr.scan(path.read_bytes())["fields"]  # same path as the app, sideways reads included
        except Exception as e:  # an unreadable photo counts as a miss, not a crash
            f = {"batch": None, "expiry": None, "brand": None, "error": str(e)}
        ms = (time.perf_counter() - t) * 1000
        res = {
            "file": r["file"], "set": r["set"], "ms": round(ms),
            "batch": {"want": r["batch"], "got": f.get("batch"), "ok": bool(f.get("batch")) and normalise_batch(f["batch"]) == normalise_batch(r["batch"])},
            "expiry": {"want": r["expiry"], "got": f.get("expiry"), "ok": bool(r["expiry"]) and _expiry(f.get("expiry")) == _expiry(r["expiry"])},
            "brand": {"want": r["brand"], "got": f.get("brand"), "ok": _brand_ok(f.get("brand"), r["brand"])},
        }
        results.append(res)
        marks = " ".join(f"{k}:{'✓' if res[k]['ok'] else '✗ ' + str(res[k]['got'])}" for k in ("batch", "expiry", "brand"))
        print(f"  [{r['set']}] {Path(r['file']).name:<28} {ms:6.0f} ms  {marks}")

    def summary(items: list) -> dict:
        n = len(items)
        pct = lambda k: round(100 * sum(i[k]["ok"] for i in items) / n, 1) if n else None
        ms = sorted(i["ms"] for i in items)
        return {"photos": n, "batch_pct": pct("batch"), "expiry_pct": pct("expiry"), "brand_pct": pct("brand"),
                "median_ms": ms[n // 2] if n else None}

    sets = {s: summary([r for r in results if r["set"] == s]) for s in sorted({r["set"] for r in results})}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "sets": sets, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for s, v in sets.items():
        print(f"\n{s}: {v['photos']} photos · batch {v['batch_pct']}% · expiry {v['expiry_pct']}% · brand {v['brand_pct']}% · median {v['median_ms']} ms")
    if "real" not in sets:
        print("\nNo real phone photos yet: add them to tests/strips/real/ (see the README there).")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", help="only this set (real / synthetic)")
    run(ap.parse_args().set)
