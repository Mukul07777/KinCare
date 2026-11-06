"""Batch checks and the alert store: check, scan, bill, inventory, alerts, stats, manufacturers, insights, ingest."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from rapidfuzz import fuzz

from matcher import match, normalise_batch, normalise_maker

from core import SOURCES, _core, _fill, _insights_cache, _next_nightly, _refresh, _stats_cache, _stats_now, candidates, conn, now, on_startup, require, rows, run_check

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "alerts": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]}


@router.get("/api/check")
def check(batch: str = Query(..., min_length=1), maker: str | None = None, brand: str | None = None):
    return run_check(batch, maker, brand)


@router.post("/api/scan")
async def scan(image: UploadFile = File(...)):
    """OCR a strip photo, then check the batch it found."""
    import ocr

    data = await image.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 12 MB)")
    try:
        result = ocr.scan(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.post("/api/scan/bill")
async def scan_bill(image: UploadFile = File(...)):
    """OCR a pharmacy bill and check every batch-like token on it."""
    import insights
    import ocr

    data = await image.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 12 MB)")
    try:
        r = ocr.scan_bill(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    items = []
    for c in r["candidates"]:
        hits = match(candidates(c["batch"]), c["batch"], None, c["line"])
        items.append({**c, "verdict": "alert_found" if hits else "no_alert_found",
                      "match": {**hits[0], "explain": insights.failures_of(hits[0]["alert"]["reason"], hits[0]["alert"]["category"])} if hits else None})
    return {"checked_at": now(), "items": items, "flagged": sum(1 for i in items if i["match"]), "lines": r["lines"]}


class InventoryRow(BaseModel):
    product: str = ""
    batch: str
    maker: str = ""
    qty: int = 0


@router.post("/api/inventory/check")
def inventory_check(items: list[InventoryRow]):
    """Match every stock row against the alert store (pharmacy bulk check)."""
    out = []
    for i, r in enumerate(items):
        hits = match(candidates(r.batch), r.batch, r.maker or None, r.product or None)
        out.append({"row": i, **r.model_dump(), "matches": hits})
    return {"checked_at": now(), "total": len(items), "flagged": sum(1 for o in out if o["matches"]), "rows": out}


@router.get("/api/alerts")
def alerts(
    q: str | None = None,
    category: str | None = None,
    source: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    where, args = [], []
    if q:
        where.append("(product_name LIKE ? OR batch_no LIKE ? OR manufacturer LIKE ? OR batch_norm LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like, f"%{normalise_batch(q)}%"]
    if category:
        where.append("category = ?")
        args.append(category)
    if source:
        where.append("source = ?")
        args.append(source)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM alerts {clause}", args).fetchone()[0]
    items = rows(f"SELECT * FROM alerts {clause} ORDER BY alert_month DESC, id LIMIT ? OFFSET ?", [*args, limit, offset])
    return {"total": total, "items": items}


@router.get("/api/stats")
def stats():
    """Alert-table summary for the home page; recomputed only after an ingest changes the table."""
    one = lambda sql: conn.execute(sql).fetchone()[0]
    key = tuple(conn.execute("SELECT (SELECT COUNT(*) FROM alerts), (SELECT MAX(id) FROM alerts), (SELECT MAX(id) FROM documents)").fetchone())
    if _stats_cache.get("key") == key:
        return _stats_cache["data"]
    with _fill:
        if _stats_cache.get("key") != key:
            _stats_cache.update(key=key, data=_stats_now(one))
    return _stats_cache["data"]


@router.get("/api/manufacturer")
def manufacturer(name: str = Query(..., min_length=2)):
    """Alert history for a maker, grouping spelling variants of the same company.
    Variants are returned so every merge is visible, never silent."""
    target = normalise_maker(name)
    if not target:
        raise HTTPException(400, "Manufacturer name too short")
    makers = [r[0] for r in conn.execute("SELECT DISTINCT manufacturer FROM alerts WHERE manufacturer != ''")]
    core = _core(target)

    def same_company(m: str) -> bool:
        n = normalise_maker(m)
        # Both the distinctive core ("paksons") and the full name must agree, so a shared
        # industry word can't merge "Paksons Pharmaceuticals" with "Konis Pharmaceuticals".
        return fuzz.ratio(_core(n), core) >= 90 and fuzz.token_sort_ratio(n, target) >= 85

    variants = [m for m in makers if same_company(m)]
    if not variants:
        return {"name": name, "total": 0, "variants": [], "by_year": [], "alerts": []}
    marks = ",".join("?" * len(variants))
    items = rows(f"SELECT * FROM alerts WHERE manufacturer IN ({marks}) ORDER BY alert_month DESC", variants)
    by_year: dict[str, int] = {}
    for a in items:
        by_year[a["alert_month"][:4]] = by_year.get(a["alert_month"][:4], 0) + 1
    return {
        "name": max(variants, key=lambda v: sum(1 for a in items if a["manufacturer"] == v)),
        "total": len(items),
        "spurious": sum(1 for a in items if a["category"] == "spurious"),
        "variants": variants,
        "by_year": [{"year": y, "n": n} for y, n in sorted(by_year.items())],
        "alerts": items[:100],
    }


@router.get("/api/insights")
def insights_endpoint():
    """National picture: where failures are found, what kind, which drug groups."""
    import insights

    n = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    if _insights_cache.get("n") != n:
        with _fill:  # single flight: a burst of cold requests computes once, the rest wait for it
            if _insights_cache.get("n") != n:
                _insights_cache.update(n=n, data=insights.national(conn))
    return _insights_cache["data"]


@router.get("/api/sources")
def sources():
    docs = rows("SELECT title, source, alert_month, published, COALESCE(pdf_url, url) AS url, rows FROM documents ORDER BY published DESC")
    return {"sources": SOURCES, "documents": docs}


@on_startup
def _nightly_ingest():
    """Re-read every regulator source once a night. Off with KINCARE_NIGHTLY=0 (tests, offline demos)."""
    import os
    import threading
    import time

    if os.environ.get("KINCARE_NIGHTLY") == "0":
        return
    if not conn.execute("SELECT 1 FROM ingest_runs LIMIT 1").fetchone():
        # first boot: the database was just built, record it as the baseline instead of re-downloading everything
        n = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        conn.execute("INSERT INTO ingest_runs (trigger, started_at, finished_at, status, alerts_before, alerts_after) VALUES ('baseline',?,?,'ok',?,?)",
                     (now(), now(), n, n))

    def loop():
        while True:
            time.sleep(max(60, (_next_nightly() - datetime.now(timezone.utc)).total_seconds()))
            _refresh("nightly")

    threading.Thread(target=loop, daemon=True).start()


@router.post("/api/ingest/run")
def ingest_run(tasks: BackgroundTasks, _: dict = Depends(require("ingest.run"))):
    """Fetch newly published CDSCO PDFs and load them (also run nightly)."""
    tasks.add_task(_refresh)
    return {"started": True}
