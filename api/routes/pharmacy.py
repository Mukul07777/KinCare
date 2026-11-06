"""Pharmacy: sales (who bought which batch) and buyer notification."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from matcher import match, normalise_batch

import roles

from core import _phone, candidates, conn, require, rows

router = APIRouter()


# ---- pharmacy sales (who bought which batch) ----

class SaleIn(BaseModel):
    pharmacy: str | None = None
    city: str | None = None
    customer: str | None = None
    phone: str | None = None
    language: str = "hi"
    product: str | None = None
    batch: str
    sold_at: str | None = None


@router.put("/api/sales")
def sales_replace(items: list[SaleIn], who: dict = Depends(require("sales.manage"))):
    dev = who["account"]
    conn.execute("DELETE FROM sales WHERE device = ?", (dev,))
    for s in items:
        conn.execute(
            "INSERT INTO sales (device, pharmacy, city, customer, phone, language, product, batch, batch_norm, sold_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (dev, s.pharmacy, s.city, s.customer, _phone(s.phone) if s.phone else None, s.language, s.product, s.batch, normalise_batch(s.batch), s.sold_at),
        )
    conn.commit()
    return {"ok": True, "count": len(items)}


@router.get("/api/sales")
def sales_list(who: dict = Depends(require("sales.manage"))):
    return rows("SELECT * FROM sales WHERE device = ? ORDER BY id", (who["account"],))


@router.post("/api/pharmacy/notify")
def pharmacy_notify(batch: str = Query(...), who: dict = Depends(require("buyers.notify"))):
    """Notify every customer this pharmacy sold a flagged batch to."""
    import checkin
    import notify

    dev = who["account"]
    buyers = rows("SELECT * FROM sales WHERE device = ? AND batch_norm = ? AND phone IS NOT NULL", (dev, normalise_batch(batch)))
    hit = match(candidates(batch), batch)
    if not hit:
        raise HTTPException(404, "No published alert names this batch")
    alert = hit[0]["alert"]
    sent = []
    for b in buyers:
        lang = b["language"] if b["language"] in ("hi", "en") else "hi"
        token = checkin.create(conn, name=b["customer"], phone=b["phone"], language=lang, batch=b["batch"], alert_id=alert["id"])
        for channel, fn, body in (
            ("whatsapp", notify.send_whatsapp, notify.whatsapp_text(alert, b["batch"], b["customer"], lang, checkin.link(token))),
            ("voice", None, notify.voice_script(alert, b["batch"], b["customer"], lang)),
        ):
            try:
                status, pid = fn(b["phone"], body) if fn else notify.place_call(b["phone"], body, lang)
            except Exception as e:
                status, pid = "failed", str(e)[:200]
            conn.execute(
                "INSERT INTO notifications (channel, name, phone, language, batch, alert_id, message, status, provider_id) VALUES (?,?,?,?,?,?,?,?,?)",
                (channel, b["customer"], b["phone"], lang, b["batch"], alert["id"], body, status, pid),
            )
            sent.append({"channel": channel, "customer": b["customer"], "status": status, "message": body, "language": lang})
    roles.audit(conn, dev, "buyers.notify", batch, f"{len(buyers)} buyers", roles.PHARMACIST)
    conn.commit()
    return {"buyers": len(buyers), "notifications": sent}
