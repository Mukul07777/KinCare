"""Early Signal: symptom reports per batch, signals and CSV export."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from matcher import normalise_batch

from core import conn, current_account

router = APIRouter()


# ---- Early Signal: symptom reports per batch ----
class ReportIn(BaseModel):
    batch: str
    brand: str | None = None
    maker: str | None = None
    city: str | None = None
    symptoms: list[str]
    onset_days: int | None = None


@router.post("/api/reports")
def report_add(r: ReportIn, account: str = Depends(current_account)):
    import checkin

    dev = account
    key = normalise_batch(r.batch)
    symptoms = sorted({s for s in r.symptoms if s in checkin.SYMPTOMS})
    if len(key) < 3:
        raise HTTPException(400, "Batch number looks too short")
    if not symptoms:
        raise HTTPException(400, "Pick at least one symptom")
    clip = lambda v: (v or "").strip()[:80] or None
    # One report per device per batch; a second report replaces the first, so one phone can't stuff a signal.
    conn.execute(
        """INSERT OR REPLACE INTO reports (device, batch, batch_norm, brand, maker, city, symptoms, onset_days)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (dev, r.batch.strip()[:40], key, clip(r.brand), clip(r.maker), clip(r.city and r.city.title()), ",".join(symptoms), r.onset_days),
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM reports WHERE batch_norm = ?", (key,)).fetchone()[0]
    return {"ok": True, "reports_for_batch": n}


@router.get("/api/signals")
def signals_list():
    import checkin
    import signals

    return {**signals.summary(conn), "signals": signals.detect(conn),
            "symptoms": [{"key": k, "en": v[0], "hi": v[1]} for k, v in checkin.SYMPTOMS.items()]}


@router.get("/api/signals.csv")
def signals_csv():
    """Signals as a draft for PvPI / the state drug controller to decide on lab testing."""
    import csv
    import io

    import signals
    from fastapi.responses import Response

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["batch", "brand", "manufacturer", "level", "reports", "cities", "first_report", "symptoms (n, PRR)", "regulator_listed", "simulated"])
    for s in signals.detect(conn):
        sym = "; ".join(f"{x['en']} ({x['n']}{', PRR ' + str(x['prr']) if x['prr'] else ''})" for x in s["symptoms"])
        reg = s["regulator"]["alert_month"] if s["regulator"] else "not listed"
        w.writerow([s["batch"], s["brand"] or "", s["maker"] or "", s["level"], s["reports"], " / ".join(s["cities"]),
                    s["first_report"], sym, reg, "yes" if s["simulated"] else "no"])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=kincare-signals.csv"})
