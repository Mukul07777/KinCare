"""SOS: emergency contacts, medical card, one-tap alert."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import conn, current_account, rows

router = APIRouter()


# ---- SOS / doctor emergency ----
class ContactIn(BaseModel):
    name: str
    phone: str
    relation: str | None = None


class SosIn(BaseModel):
    member: str = "Me"
    lat: float | None = None
    lng: float | None = None


@router.get("/api/sos/contacts")
def sos_contacts(account: str = Depends(current_account)):
    return rows("SELECT id, name, phone, relation FROM contacts WHERE device = ? ORDER BY id", (account,))


@router.post("/api/sos/contacts")
def sos_contact_add(c: ContactIn, account: str = Depends(current_account)):
    dev = account
    phone = re.sub(r"[^\d+]", "", c.phone)
    if len(phone.lstrip("+")) == 10:
        phone = "+91" + phone.lstrip("+")
    if not re.fullmatch(r"\+\d{10,15}", phone):
        raise HTTPException(400, "Enter a phone number like +91 98xxxxxxxx")
    if conn.execute("SELECT COUNT(*) FROM contacts WHERE device = ?", (dev,)).fetchone()[0] >= 5:
        raise HTTPException(400, "Up to 5 emergency contacts")
    conn.execute("INSERT INTO contacts (device, name, phone, relation) VALUES (?, ?, ?, ?)",
                 (dev, c.name.strip()[:40] or "Contact", phone, (c.relation or "").strip()[:20] or None))
    conn.commit()
    return {"ok": True}


@router.delete("/api/sos/contacts/{cid}")
def sos_contact_del(cid: int, account: str = Depends(current_account)):
    conn.execute("DELETE FROM contacts WHERE id = ? AND device = ?", (cid, account))
    conn.commit()
    return {"ok": True}


@router.get("/api/sos/card")
def sos_card(member: str = "Me", account: str = Depends(current_account)):
    import sos

    return sos.card(conn, account, member)


@router.post("/api/sos")
def sos_trigger(b: SosIn, account: str = Depends(current_account)):
    import sos

    dev = account
    c = sos.card(conn, dev, b.member)
    text = sos.message(c, b.lat, b.lng)
    contacts = rows("SELECT name, phone FROM contacts WHERE device = ?", (dev,))
    deliveries = sos.deliver(contacts, text)
    for name in tell_caregivers(dev, b.member, "sos", f"🚨 SOS from {b.member}", text, "sos"):
        deliveries.append({"name": name, "phone": "KinCare caregiver", "status": "caregiver", "link": None})
    cur = conn.execute("INSERT INTO sos_events (device, member, lat, lng, message, delivered) VALUES (?, ?, ?, ?, ?, ?)",
                       (dev, b.member, b.lat, b.lng, text, sum(d["status"] == "sent" for d in deliveries)))
    conn.commit()
    return {"id": cur.lastrowid, "message": text, "deliveries": deliveries}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.family import tell_caregivers  # noqa: E402
