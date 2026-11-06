"""Doctor connect: time-limited links, doctor view, messages."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import doctor as doctor_mod
import vault

from core import conn, current_account, now, rows, signed_in_account

router = APIRouter()


# ---- doctor connect ----

class LinkIn(BaseModel):
    member: str = "Me"
    doctor: str | None = None
    hours: int = 72


class MessageIn(BaseModel):
    kind: str = "note"
    text: str
    doctor: str | None = None


class PatientMessageIn(BaseModel):
    token: str
    kind: str = "note"
    text: str


def _doctor_link(token: str) -> dict:
    lk = doctor_mod.link(conn, token)
    if not lk:
        raise HTTPException(410, "This link has expired or was turned off by the patient")
    return lk


def _messages(token: str | None = None, dev: str | None = None, member: str | None = None, since: int = 0) -> list[dict]:
    if token:
        out = rows("SELECT * FROM doctor_messages WHERE token = ? AND id > ? ORDER BY id", (token, since))
    else:
        out = rows("SELECT * FROM doctor_messages WHERE device = ?" + (" AND member = ?" if member else "") + " ORDER BY id DESC LIMIT 50",
                   (dev, member) if member else (dev,))
    return [vault.open_row("doctor_messages", m) for m in out]


@router.post("/api/doctor/links")
def doctor_link_add(b: LinkIn, account: str = Depends(signed_in_account)):
    if not 1 <= b.hours <= 24 * 30:
        raise HTTPException(400, "Link can last 1 hour to 30 days")
    return doctor_mod.new_link(conn, account, b.member, (b.doctor or "").strip()[:80] or None, b.hours)


@router.get("/api/doctor/links")
def doctor_links(account: str = Depends(current_account)):
    links = rows("""SELECT token, member, doctor, created_at, expires_at, last_seen FROM doctor_links
                    WHERE device = ? AND revoked = 0 AND expires_at > ? ORDER BY created_at DESC""", (account, now()))
    return [{**lk, "room": doctor_mod.room(lk["token"])} for lk in links]


@router.delete("/api/doctor/links/{token}")
def doctor_link_revoke(token: str, account: str = Depends(current_account)):
    conn.execute("UPDATE doctor_links SET revoked = 1 WHERE token = ? AND device = ?", (token, account))
    conn.commit()
    return {"ok": True}


@router.get("/api/doctor/{token}")
def doctor_view(token: str):
    """The doctor's console: who, latest vitals, NEWS2, 24 h live stats, medicines, adherence, SOS, messages."""
    import care
    import sos

    lk = _doctor_link(token)
    dev, member = lk["device"], lk["member"]
    conn.execute("UPDATE doctor_links SET last_seen = ? WHERE token = ?", (now(), token))
    conn.commit()
    cur = doctor_mod.latest(conn, dev, member)
    report = care_report(member, account=dev)
    return {
        "member": member, "doctor": lk["doctor"], "expires_at": lk["expires_at"], "room": doctor_mod.room(token),
        "latest": cur,
        "assessment": care.assess(cur["temp_c"], cur["bp_sys"], cur["bp_dia"], cur["pulse"], cur["spo2"]),
        "news2": doctor_mod.news2(cur["temp_c"], cur["bp_sys"], cur["pulse"], cur["spo2"]),
        "stats_24h": doctor_mod.live_stats(conn, dev, member),
        "vitals": report["vitals"], "plans": report["plans"], "adherence": report["adherence"],
        "sos": rows("SELECT id, lat, lng, at, resolved_at FROM sos_events WHERE device = ? AND member = ? ORDER BY at DESC LIMIT 5", (dev, member)),
        "messages": _messages(token),
    }


@router.get("/api/doctor/{token}/live")
def doctor_live(token: str, since: int = 0, msg_since: int = 0):
    """Polled every 2 s by the console: new live samples and new messages."""
    lk = _doctor_link(token)
    dev, member = lk["device"], lk["member"]
    samples = rows("SELECT id, at, pulse, spo2, source FROM vitals_live WHERE device = ? AND member = ? AND id > ? ORDER BY id DESC LIMIT 300",
                   (dev, member, since))[::-1]
    last = conn.execute("SELECT at, source FROM vitals_live WHERE device = ? AND member = ? ORDER BY id DESC LIMIT 1", (dev, member)).fetchone()
    cur = doctor_mod.latest(conn, dev, member)
    conn.execute("UPDATE doctor_links SET last_seen = ? WHERE token = ?", (now(), token))
    conn.commit()
    return {"samples": samples, "online": bool(last) and last["at"] >= _ago(15), "source": last["source"] if last else None,
            "latest": cur, "news2": doctor_mod.news2(cur["temp_c"], cur["bp_sys"], cur["pulse"], cur["spo2"]),
            "messages": _messages(token, since=msg_since)}


@router.get("/api/doctor/{token}/interactions")
def doctor_interactions(token: str):
    return care_interactions(None, account=_doctor_link(token)["device"])


@router.post("/api/doctor/{token}/messages")
def doctor_message(token: str, b: MessageIn):
    """Doctor writes to the patient. 'advice' also joins the patient's daily reminders."""
    lk = _doctor_link(token)
    text = b.text.strip()
    if b.kind not in doctor_mod.KINDS or not 0 < len(text) <= 1000:
        raise HTTPException(400, "Write a message of up to 1000 characters")
    if b.doctor and not lk["doctor"]:
        conn.execute("UPDATE doctor_links SET doctor = ? WHERE token = ?", (b.doctor.strip()[:80], token))
    cur = conn.execute("INSERT INTO doctor_messages (token, device, member, author, kind, text, at) VALUES (?,?,?,?,?,?,?)",
                       (token, lk["device"], lk["member"], "doctor", b.kind, vault.seal(text, "doctor_messages", "text"), now()))
    added_to_plan = False
    if b.kind == "advice":
        p = conn.execute("SELECT id, advice FROM plans WHERE device = ? AND member = ? ORDER BY id DESC LIMIT 1",
                         (lk["device"], lk["member"])).fetchone()
        if p:
            advice = json.loads(p["advice"] or "[]")
            if text not in advice:
                conn.execute("UPDATE plans SET advice = ? WHERE id = ?", (json.dumps(advice + [text]), p["id"]))
            added_to_plan = True
    conn.commit()
    return {"id": cur.lastrowid, "added_to_plan": added_to_plan}


@router.get("/api/care/messages")
def care_messages(member: str | None = None, account: str = Depends(current_account)):
    msgs = _messages(dev=account, member=member)
    return {"messages": msgs, "unread": sum(1 for m in msgs if m["author"] == "doctor" and not m["read_at"])}


@router.post("/api/care/messages")
def care_message_send(b: PatientMessageIn, account: str = Depends(current_account)):
    dev = account
    lk = doctor_mod.link(conn, b.token)
    text = b.text.strip()
    if not lk or lk["device"] != dev:
        raise HTTPException(404, "Doctor link not found")
    if b.kind not in ("note", "call") or not 0 < len(text) <= 1000:
        raise HTTPException(400, "Write a message of up to 1000 characters")
    cur = conn.execute("INSERT INTO doctor_messages (token, device, member, author, kind, text, at) VALUES (?,?,?,?,?,?,?)",
                       (b.token, dev, lk["member"], "patient", b.kind, vault.seal(text, "doctor_messages", "text"), now()))
    conn.commit()
    return {"id": cur.lastrowid}


@router.post("/api/care/messages/read")
def care_messages_read(account: str = Depends(current_account)):
    conn.execute("UPDATE doctor_messages SET read_at = ? WHERE device = ? AND author = 'doctor' AND read_at IS NULL",
                 (now(), account))
    conn.commit()
    return {"ok": True}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.care_plan import care_interactions, care_report  # noqa: E402
from routes.live_vitals import _ago  # noqa: E402
