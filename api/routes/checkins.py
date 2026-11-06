"""Post-recall check-ins: how patients feel after a flagged batch, PvPI export."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from matcher import normalise_batch

from core import conn, now, rows

router = APIRouter()


# ---- post-recall check-ins ----

class CheckinIn(BaseModel):
    feeling: str  # "ok" | "unwell"
    symptoms: list[str] = []
    bp_sys: int | None = None
    bp_dia: int | None = None
    note: str | None = None


def _checkin_row(token: str) -> dict:
    r = conn.execute("SELECT * FROM checkins WHERE token = ?", (token,)).fetchone()
    if not r:
        raise HTTPException(404, "This check-in link is not valid")
    return dict(r)


@router.get("/api/checkin/{token}")
def checkin_get(token: str):
    import checkin

    c = _checkin_row(token)
    a = rows("SELECT product_name, brand, category, alert_month, reason, alert_url FROM alerts WHERE id = ?", (c["alert_id"],))
    return {"name": c["name"], "batch": c["batch"], "language": c["language"], "responded": bool(c["responded_at"]),
            "alert": a[0] if a else None, "symptoms": [{"key": k, "en": v[0], "hi": v[1]} for k, v in checkin.SYMPTOMS.items()]}


@router.post("/api/checkin/{token}")
def checkin_post(token: str, body: CheckinIn):
    import checkin

    _checkin_row(token)
    symptoms = [s for s in body.symptoms if s in checkin.SYMPTOMS]
    for v, lo, hi_ in ((body.bp_sys, 50, 260), (body.bp_dia, 30, 180)):
        if v is not None and not lo <= v <= hi_:
            raise HTTPException(400, "Blood pressure reading looks wrong")
    level = checkin.triage(body.feeling, symptoms, body.bp_sys, body.bp_dia)
    conn.execute(
        "UPDATE checkins SET responded_at = ?, feeling = ?, symptoms = ?, bp_sys = ?, bp_dia = ?, note = ?, triage = ? WHERE token = ?",
        (now(), body.feeling, ",".join(symptoms), body.bp_sys, body.bp_dia, (body.note or "")[:500], level, token),
    )
    if symptoms:  # check-in answers also feed Early Signal
        batch = conn.execute("SELECT batch FROM checkins WHERE token = ?", (token,)).fetchone()[0]
        conn.execute(
            "INSERT OR REPLACE INTO reports (device, batch, batch_norm, symptoms, origin) VALUES (?, ?, ?, ?, 'checkin')",
            (f"checkin:{token}", batch, normalise_batch(batch), ",".join(symptoms)),
        )
    conn.commit()
    return {"triage": level}


@router.get("/api/checkins")
def checkins_list():
    items = rows(
        """SELECT c.*, a.product_name, a.brand, a.manufacturer, a.category FROM checkins c
           LEFT JOIN alerts a ON a.id = c.alert_id
           ORDER BY c.responded_at IS NULL, CASE c.triage WHEN 'urgent' THEN 0 WHEN 'review' THEN 1 ELSE 2 END, c.responded_at DESC LIMIT 200"""
    )
    return {"items": items, "responded": sum(1 for i in items if i["responded_at"]), "urgent": sum(1 for i in items if i["triage"] == "urgent")}


@router.post("/api/checkins/{cid}/reviewed")
def checkin_reviewed(cid: int):
    conn.execute("UPDATE checkins SET reviewed = 1 WHERE id = ?", (cid,))
    conn.commit()
    return {"ok": True}


@router.get("/api/checkins/pvpi.csv")
def checkins_pvpi():
    """Responses with symptoms, laid out like the fields of a PvPI suspected adverse reaction form."""
    import csv
    import io

    from fastapi.responses import Response

    import checkin

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["patient_initials", "reaction", "reaction_onset_reported", "suspected_medicine", "batch_no", "manufacturer",
                "regulator_alert", "bp_reading", "triage", "reporter_note"])
    for c in checkins_list()["items"]:
        if not c["symptoms"] and c["feeling"] != "unwell":
            continue
        initials = "".join(p[0] for p in (c["name"] or "").split()[:2]).upper()
        reactions = "; ".join(checkin.SYMPTOMS[s][0] for s in (c["symptoms"] or "").split(",") if s in checkin.SYMPTOMS) or "Feels unwell"
        w.writerow([initials, reactions, c["responded_at"], c["product_name"], c["batch"], c["manufacturer"],
                    f"{c['category']} alert", f"{c['bp_sys']}/{c['bp_dia']}" if c["bp_sys"] else "", c["triage"], c["note"]])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=kincare-pvpi-reports.csv"})
