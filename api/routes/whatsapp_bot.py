"""WhatsApp (Meta Cloud API): join link, webhook, strip-photo replies, simulator."""
import json
import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile

import notify as notify_mod
import whatsapp

from core import _log_note, conn, now, require, rows, run_check

router = APIRouter()


# ---- WhatsApp (Meta Cloud API): join link + webhook ----

@router.get("/api/whatsapp/info")
def whatsapp_info():
    return {"provider": "meta" if whatsapp.ready() else "twilio" if notify_mod.whatsapp_ready() else None,
            "join_url": whatsapp.join_url(), "template": bool(__import__("os").environ.get("WHATSAPP_TEMPLATE"))}


@router.get("/api/whatsapp/webhook")
def whatsapp_verify(request: Request):
    """Meta calls this once when you save the webhook URL in the app dashboard."""
    import os
    from fastapi.responses import PlainTextResponse

    q = request.query_params
    if q.get("hub.mode") == "subscribe" and os.environ.get("WHATSAPP_VERIFY_TOKEN") and q.get("hub.verify_token") == os.environ["WHATSAPP_VERIFY_TOKEN"]:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403, "Verify token mismatch")


def _mark_taken_by_phone(phone: str) -> dict | None:
    """Tick the dose the patient was most recently reminded about (or the latest one due) today."""
    import care

    day = datetime.now().date()
    r = conn.execute("""SELECT rs.med_id, rs.slot, m.name, m.language, p.member FROM reminders_sent rs
                        JOIN plan_meds m ON m.id = rs.med_id JOIN plans p ON p.id = m.plan_id
                        WHERE m.phone = ? AND rs.day = ? AND NOT EXISTS (SELECT 1 FROM doses d WHERE d.med_id = rs.med_id AND d.day = rs.day AND d.slot = rs.slot)
                        ORDER BY rs.sent_at DESC LIMIT 1""", (phone, day.isoformat())).fetchone()
    if not r:
        hm = datetime.now().strftime("%H:%M")
        due = []
        for m in rows("SELECT m.*, p.member, p.start_date FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE m.phone = ?", (phone,)):
            for d in care.doses_for(m, m["start_date"], day):
                taken = conn.execute("SELECT 1 FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (m["id"], day.isoformat(), d["slot"])).fetchone()
                if d["time"] <= hm and not taken:
                    due.append((d["time"], {"med_id": m["id"], "slot": d["slot"], "name": m["name"], "language": m["language"], "member": m["member"]}))
        if not due:
            return None
        r = max(due, key=lambda x: x[0])[1]
    r = dict(r)
    conn.execute("INSERT INTO doses (med_id, day, slot, taken_at) VALUES (?,?,?,?) ON CONFLICT(med_id, day, slot) DO UPDATE SET taken_at = excluded.taken_at",
                 (r["med_id"], day.isoformat(), r["slot"], now()))
    conn.commit()
    return r


def whatsapp_reply(phone: str, text: str) -> str:
    """Answer one patient message. Replies go out inside the free 24-hour window the message just opened."""
    kind, batch = whatsapp.intent(text)
    lang = (conn.execute("SELECT language FROM plan_meds WHERE phone = ? AND language IS NOT NULL ORDER BY id DESC LIMIT 1", (phone,)).fetchone() or ["hi"])[0]
    hi = lang == "hi"
    if kind == "taken":
        r = _mark_taken_by_phone(phone)
        if r:
            return (f"✅ {r['member']} ki {r['name']} darj ho gayi. Shabaash!" if hi else f"✅ Marked {r['name']} as taken for {r['member']}. Well done!")
        return "Abhi koi khuraak baaki nahi hai. Agli baar yaad dilayenge." if hi else "No dose is due right now. We'll remind you at the next one."
    if kind == "batch":
        check = run_check(batch, None, None)
        if check["matches"]:
            return notify_mod.whatsapp_text(check["matches"][0]["alert"], batch, None, lang)
        return (f"Batch {batch}: kisi bhi sarkari (CDSCO / state) alert list mein nahi mila. Strip par expiry bhi dekh lein."
                if hi else f"Batch {batch}: not on any CDSCO or state alert list we track. Check the expiry on the strip too.")
    if kind == "hello":
        return ("Namaste! KinCare WhatsApp par shuru ho gaya.\n• Dawa lene ke baad *1* bhejein\n• Kisi bhi strip ka *batch number* bhejein, hum sarkari alert list mein check karenge"
                if hi else "Welcome to KinCare on WhatsApp.\n• Reply *1* after each dose\n• Send any strip's *batch number* and we'll check it against every regulator alert")
    return ("Dawa lene ke baad *1* bhejein, ya strip ka batch number bhejein (jaise AT25-0938A)."
            if hi else "Reply *1* after a dose, or send a batch number from a strip (e.g. AT25-0938A).")


def _expired(expiry: str | None) -> bool:
    """'10/2027', '10-27', 'OCT 2027' style strip expiry -> already past?"""
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{2,4})", expiry or "")
    if not m:
        return False
    mm, yy = int(m.group(1)), int(m.group(2))
    yy += 2000 if yy < 100 else 0
    return 1 <= mm <= 12 and (yy, mm) < (datetime.now().year, datetime.now().month)


def whatsapp_photo_reply(phone: str, image: bytes) -> tuple[str, dict]:
    """A strip photo sent on WhatsApp: read the batch with OCR, check it, answer in the patient's language."""
    lang = (conn.execute("SELECT language FROM plan_meds WHERE phone = ? AND language IS NOT NULL ORDER BY id DESC LIMIT 1", (phone,)).fetchone() or ["hi"])[0]
    return strip_photo_reply(image, lang)


def strip_photo_reply(image: bytes, lang: str = "hi") -> tuple[str, dict]:
    """Read the batch from a strip photo (OCR), check it against every alert, answer in Hindi or English."""
    import ocr

    hi = lang == "hi"
    try:
        f = ocr.scan(image)["fields"]  # includes the sideways read for batches printed along the edge
    except Exception as e:  # unreadable image
        print("whatsapp photo:", e)
        f = {"batch": None, "brand": None, "maker": None, "expiry": None}
    if not f["batch"]:
        return ("Photo mein batch number padh nahi paaye. Strip ke peeche jahan *B.No.* likha hai, uski saaf, paas se photo bhejein. Ya batch number type kar dein."
                if hi else "We couldn't read a batch number. Send a sharp, close photo of the back of the strip where *B.No.* is printed, or type the batch number."), f
    check = run_check(f["batch"], f["maker"], f["brand"])
    name = f["brand"] or ("Yeh dawa" if hi else "This medicine")
    if check["matches"]:
        reply = "📷 " + notify_mod.whatsapp_text(check["matches"][0]["alert"], f["batch"], None, lang)
    elif hi:
        reply = (f"📷 Photo se padha: *{name}*, batch *{f['batch']}*"
                 + (f", expiry {f['expiry']}" if f["expiry"] else "") + ".\n✅ Yeh batch kisi bhi sarkari (CDSCO / state) alert list mein nahi hai, aaj tak.")
    else:
        reply = (f"📷 Read from your photo: *{name}*, batch *{f['batch']}*"
                 + (f", expiry {f['expiry']}" if f["expiry"] else "") + ".\n✅ This batch is not on any CDSCO or state alert list, as of today.")
    if _expired(f["expiry"]):
        reply += ("\n⚠️ Lekin yeh dawa *expire ho chuki hai* ({}). Mat lijiye, chemist ko lauta dijiye.".format(f["expiry"])
                  if hi else "\n⚠️ But this medicine has *expired* ({}). Don't take it; return it to the chemist.".format(f["expiry"]))
    return reply, {**f, "verdict": check["verdict"]}


def _wa_photo_task(phone: str, media_id: str):
    image = whatsapp.download_media(media_id)
    reply = whatsapp_photo_reply(phone, image)[0] if image else "Photo download nahi ho paayi. Dobara bhejein."
    _log_note("whatsapp", None, phone, "hi", "", reply)
    conn.commit()


@router.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request, tasks: BackgroundTasks):
    raw = await request.body()
    if not whatsapp.signature_ok(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(401, "Bad signature")
    body = json.loads(raw or b"{}")
    handled = 0
    for phone, text in whatsapp.incoming(body):
        whatsapp.record_inbound(conn, phone, text)
        if not text:
            continue
        reply = whatsapp_reply(phone, text)
        _log_note("whatsapp", None, phone, "hi", "", reply)
        handled += 1
    # Photos: OCR after we've answered Meta, so the webhook stays fast.
    for phone, media_id, _caption in whatsapp.incoming_images(body):
        tasks.add_task(_wa_photo_task, phone, media_id)
        handled += 1
    conn.commit()
    return {"ok": True, "handled": handled}  # always 200 so Meta doesn't retry


@router.post("/api/admin/demo-reset")
def admin_demo_reset(_: dict = Depends(require("demo.seed"))):
    """Before each stage run: remove every labelled simulated row (holders, copied-code ring, seeded symptom reports).
    Real users' data is never touched; simulated rows all carry a sim- device or origin='simulated'."""
    import blast
    import packs

    blast.clear_demo(conn)
    # "Alerted" marks for holders that no longer exist (their simulated purchase or sale was just removed).
    conn.execute("""DELETE FROM blast_alerts WHERE
                    (holder LIKE 'plan:%' AND CAST(substr(holder, 6) AS INTEGER) NOT IN (SELECT id FROM plan_meds)) OR
                    (holder LIKE 'sale:%' AND CAST(substr(holder, 6) AS INTEGER) NOT IN (SELECT id FROM sales))""")
    ring = packs.clear_demo(conn)
    reports = conn.execute("DELETE FROM reports WHERE origin = 'simulated'").rowcount
    conn.commit()
    return {"ok": True, "copied_code_scans": ring, "symptom_reports": reports}


# The on-screen phone on /whatsapp acts as one fixed sandbox number, never a number the caller chooses: a chosen number
# would let anyone send "1" as someone else and tick their doses.
SANDBOX_PHONE = "+910000000000"


@router.post("/api/whatsapp/simulate")
async def whatsapp_simulate(text: str | None = Query(None), image: UploadFile | None = File(None)):
    """The same WhatsApp bot without Meta keys: for the on-screen phone on /whatsapp. Nothing is sent anywhere."""
    if image is not None:
        data = await image.read()
        if len(data) > 10_000_000:
            raise HTTPException(413, "Image too large")
        reply, fields = whatsapp_photo_reply(SANDBOX_PHONE, data)
        return {"reply": reply, "read": fields}
    if not (text or "").strip():
        raise HTTPException(400, "Send text or a photo")
    return {"reply": whatsapp_reply(SANDBOX_PHONE, text.strip()[:500])}
