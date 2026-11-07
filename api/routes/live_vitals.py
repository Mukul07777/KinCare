"""Live vitals (watch, oximeter, camera pulse) and the /status page."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import doctor as doctor_mod

from core import _STARTED, _fill, _next_nightly, _timings, candidates, conn, current_account, now, rows

router = APIRouter()


# ---- live vitals (Bluetooth watch / oximeter, camera pulse, simulator) ----

class LiveSample(BaseModel):
    pulse: int | None = None
    spo2: int | None = None


class LiveIn(BaseModel):
    member: str = "Me"
    source: str
    samples: list[LiveSample]


def _ago(seconds: int) -> str:
    return datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - seconds, timezone.utc).isoformat()


@router.post("/api/care/live")
def live_add(b: LiveIn, account: str = Depends(current_account)):
    """A batch of live samples (sent every ~2 s). Every 5 min one median reading lands in the vitals history."""
    import care

    dev = account
    if b.source not in doctor_mod.SOURCES:
        raise HTTPException(400, "Unknown source")
    if not 0 < len(b.samples) <= 120:
        raise HTTPException(400, "Send 1 to 120 samples")
    at = now()
    good = [s for s in b.samples if (s.pulse is None or 25 <= s.pulse <= 250) and (s.spo2 is None or 50 <= s.spo2 <= 100)
            and (s.pulse is not None or s.spo2 is not None)]
    conn.executemany("INSERT INTO vitals_live (device, member, at, pulse, spo2, source) VALUES (?,?,?,?,?,?)",
                     [(dev, b.member, at, s.pulse, s.spo2, b.source) for s in good])
    # Judge on the median of the last 30 s, so one noisy beat never raises an alarm.
    recent = rows("SELECT pulse, spo2 FROM vitals_live WHERE device = ? AND member = ? AND at >= ?", (dev, b.member, _ago(30)))
    pulse = doctor_mod.median([r["pulse"] for r in recent])
    spo2 = doctor_mod.median([r["spo2"] for r in recent])
    pulse, spo2 = (round(pulse) if pulse else None), (round(spo2) if spo2 else None)
    a = care.assess(None, None, None, pulse, spo2)
    saved = False
    if (pulse or spo2) and not conn.execute("SELECT 1 FROM vitals WHERE device = ? AND member = ? AND source = ? AND at >= ?",
                                            (dev, b.member, b.source, _ago(300))).fetchone():
        conn.execute("INSERT INTO vitals (device, member, pulse, spo2, source, level, note) VALUES (?,?,?,?,?,?,?)",
                     (dev, b.member, pulse, spo2, b.source, a["level"], "30 s median from live stream"))
        saved = True
        if a["level"] == "urgent":  # at most once per 5 min, like the history row
            tell_caregivers(dev, b.member, "vitals", f"⚠️ {b.member}: worrying live reading", f"{', '.join(a['reasons'])}. {a['en']}", "vitals-live")
    conn.commit()
    return {"accepted": len(good), "pulse": pulse, "spo2": spo2, "assessment": a, "saved_to_history": saved}


def _pct(xs: list[float], p: float) -> float | None:
    return round(xs[min(len(xs) - 1, int(len(xs) * p))], 1) if xs else None


@router.get("/api/status")
def status(refresh_quality: bool = False):
    """Everything a judge or an engineer would ask about the running system, measured live, nothing typed in."""
    import os
    from pathlib import Path

    import db
    import quality

    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    lat = sorted(ms for _, ms, _ in _timings)
    by_route: dict[str, list[float]] = {}
    for path, ms, _ in _timings:
        by_route.setdefault(path, []).append(ms)
    routes = sorted(by_route.items(), key=lambda kv: -_pct(sorted(kv[1]), 0.95))[:10]  # slowest first
    api_dir = Path(__file__).resolve().parent.parent  # routes/ -> api/
    tests = sum(open(f, encoding="utf-8").read().count("\ndef test_") for f in (api_dir / "tests").glob("test_*.py"))
    runs = rows("SELECT trigger, started_at, finished_at, status, alerts_before, alerts_after, error FROM ingest_runs ORDER BY id DESC LIMIT 5")
    return {
        "ok": True,
        "uptime_s": int((datetime.now(timezone.utc) - _STARTED).total_seconds()),
        "data": {
            "alerts": one("SELECT COUNT(*) FROM alerts"),
            "spurious": one("SELECT COUNT(*) FROM alerts WHERE category = 'spurious'"),
            "documents": one("SELECT COUNT(*) FROM documents"),
            "makers": one("SELECT COUNT(DISTINCT manufacturer) FROM alerts"),
            "medicines": one("SELECT COUNT(*) FROM medicines"),
            "latest_list": one("SELECT MAX(alert_month) FROM alerts"),
            "first_list": one("SELECT MIN(alert_month) FROM alerts"),
            "db_mb": round(os.path.getsize(db.DB_PATH) / 1e6, 1),
            "journal": one("PRAGMA journal_mode"),
        },
        "ingest": {"next_nightly": _next_nightly().isoformat(), "runs": runs},
        "quality": quality.cached(conn, candidates, refresh=refresh_quality),
        "strip_ocr": _strip_bench(),
        "latency": {
            "requests": len(lat),
            "p50_ms": _pct(lat, 0.5), "p95_ms": _pct(lat, 0.95), "p99_ms": _pct(lat, 0.99),
            # 503 = a feature not configured on this server (e.g. no Stripe key): a clear answer, not a crash.
            "server_errors": sum(1 for _, _, s in _timings if s >= 500 and s != 503),
            "routes": [{"path": p, "n": len(v), "p50_ms": _pct(sorted(v), 0.5), "p95_ms": _pct(sorted(v), 0.95)} for p, v in routes],
        },
        "tests": tests,
    }


@router.get("/api/datasets")
def datasets():
    """Live counts of every dataset behind KinCare (see docs/DATASETS.md), for the home page.
    Recounted only when a table grows: COUNT(DISTINCT salt_key) over 2.46 lakh rows cost ~150 ms on every home-page load."""
    one = lambda sql: conn.execute(sql).fetchone()[0]
    key = tuple(conn.execute("SELECT (SELECT MAX(id) FROM alerts), (SELECT MAX(id) FROM medicines), (SELECT COUNT(*) FROM reference_records)").fetchone())
    if _datasets_cache.get("key") == key:
        return _datasets_cache["data"]
    with _fill:
        if _datasets_cache.get("key") != key:
            _datasets_cache.update(key=key, data=_datasets_now(one))
    return _datasets_cache["data"]


def _datasets_now(one) -> dict:
    return ({
        "alerts": one("SELECT COUNT(*) FROM alerts"),
        "alert_makers": one("SELECT COUNT(DISTINCT manufacturer) FROM alerts"),
        "medicines": one("SELECT COUNT(*) FROM medicines"),
        "salts": one("SELECT COUNT(DISTINCT salt_key) FROM medicines"),
        "icu_patients": one("SELECT COUNT(*) FROM reference_records"),
    })


_datasets_cache: dict = {}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.family import tell_caregivers  # noqa: E402


def _strip_bench() -> dict | None:
    """Last `python bench_strips.py` run: OCR accuracy per photo set (real phone photos vs synthetic demo prints)."""
    import json as _json

    from db import DB_PATH

    f = DB_PATH.parent / "strip_bench.json"
    try:
        r = _json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"generated_at": r["generated_at"], "sets": r["sets"]}
