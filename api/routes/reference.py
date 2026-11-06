"""Real reference data: BIDMC ICU recordings (PhysioNet)."""
import json

from fastapi import APIRouter, HTTPException

from core import conn, rows

router = APIRouter()


# ---- real reference data: BIDMC ICU recordings (PhysioNet) ----

@router.get("/api/reference/records")
def reference_records():
    """53 real ICU patients, most eventful first, plus how the camera-pulse algorithm scored on their pleth."""
    recs = rows("SELECT id, age, gender, location, seconds, summary, validation FROM reference_records ORDER BY id")
    for r in recs:
        r["summary"], r["validation"] = json.loads(r["summary"]), json.loads(r["validation"] or "{}")
    s = lambda r: r["summary"]["seconds_spo2_below_92"] * 3 + r["summary"]["seconds_pulse_above_100"]
    recs.sort(key=s, reverse=True)
    v = [r["validation"] for r in recs if r["validation"].get("estimated")]
    est = sum(x["estimated"] for x in v)
    return {
        "dataset": {"name": "BIDMC PPG and Respiration Dataset", "url": "https://physionet.org/content/bidmc/1.0.0/",
                    "license": "ODC-By 1.0", "cite": "Pimentel MAF et al. IEEE Trans Biomed Eng 2016;64(8):1914-23"},
        "records": recs,
        "validation": {
            "records": len(v), "windows": sum(x["windows"] for x in v), "estimated": est,
            "mae": round(sum(x["abs_error_sum"] for x in v) / est, 2) if est else None,
            "within5": round(sum(x["within5"] for x in v) / est, 3) if est else None,
        } if v and "abs_error_sum" in v[0] else None,
    }


@router.get("/api/reference/records/{rid}")
def reference_record(rid: str):
    r = conn.execute("SELECT * FROM reference_records WHERE id = ?", (rid,)).fetchone()
    if not r:
        raise HTTPException(404, "Record not found. Run: python -m ingest.bidmc")
    numerics = json.loads(r["numerics"])
    # Where the replay can jump to: the second with the worst oxygen, else the fastest pulse.
    worst = min(range(len(numerics)), key=lambda i: (numerics[i]["spo2"] or 101, -(numerics[i]["pulse"] or 0)))
    return {"id": r["id"], "age": r["age"], "gender": r["gender"], "location": r["location"], "hz": r["hz"],
            "numerics": numerics, "pleth": json.loads(r["pleth"]), "worst_second": max(worst - 20, 0),
            "summary": json.loads(r["summary"])}
