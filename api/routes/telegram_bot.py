"""Telegram: the free chat + alert channel (link, webhook, polling, photos)."""
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request

import telegram
import vault

from core import conn, current_account, on_startup

router = APIRouter()


# ---- Telegram ----

def _tg_lang(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    return "hi" if re.search(r"\b(kya|hai|ki|ka|ke|dawa|dawai|kitne|kitna|aaj|le li|kaun|kab|mera|meri|batao|bukhar|beta)\b", text.lower()) else "en"


TG_BUTTONS = ["✅ दवा ले ली", "आज कौन सी दवा?", "📞 परिवार को बुलाओ"]


def _tg_photo_task(chat_id: int, dev: str, file_id: str):
    image = telegram.download(file_id)
    lang = (conn.execute("SELECT language FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ? AND m.language IS NOT NULL ORDER BY m.id DESC LIMIT 1",
                         (dev,)).fetchone() or ["hi"])[0]
    reply, f = strip_photo_reply(image, lang) if image else ("Photo download nahi ho paayi. Dobara bhejein.", {})
    member = default_member(dev)
    conn.execute("INSERT INTO dadi_chat (device, member, role, text, channel) VALUES (?,?,?,?,?)", (dev, member, "me", vault.seal("📷 Strip photo", "dadi_chat", "text"), "telegram"))
    conn.execute("INSERT INTO dadi_chat (device, member, role, text, kind, data, channel) VALUES (?,?,?,?,?,?,?)",
                 (dev, member, "kincare", vault.seal(reply.replace("*", ""), "dadi_chat", "text"), "batch_alert" if f.get("verdict") == "alert_found" else "batch_clean" if f.get("verdict") else "help",
                  vault.seal(json.dumps({"batch": f.get("batch")}), "dadi_chat", "data"), "telegram"))
    conn.commit()
    telegram.send(chat_id, reply.replace("*", ""), TG_BUTTONS)


def telegram_handle(update: dict) -> str | None:
    if photo := telegram.incoming_photo(update):
        chat_id, file_id = photo
        dev = telegram.device_of(conn, chat_id)
        if not dev:
            telegram.send(chat_id, "Open KinCare and press “Connect Telegram” first, then send the strip photo again.")
            return "unlinked"
        telegram.send(chat_id, "📷 Photo mil gayi, batch padh rahe hain…")
        import threading

        threading.Thread(target=_tg_photo_task, args=(chat_id, dev, file_id), daemon=True).start()  # OCR takes a few seconds
        return "photo"
    got = telegram.incoming(update)
    if not got:
        return None
    chat_id, text, first = got
    if text.startswith("/start"):
        code = text.split(maxsplit=1)[1].strip() if " " in text else ""
        r = telegram.claim(conn, code, chat_id, first) if code else None
        if not r:
            reply = "Namaste! Open KinCare and press “Connect Telegram” to link this chat. 🙏"
        elif r["role"] == "caregiver":
            reply = "✅ Linked. You'll get alerts here when someone you look after misses a dose, logs a worrying reading or presses SOS."
        else:
            reply = ("✅ जुड़ गया! अब आप यहाँ KinCare से बात कर सकते हैं।\n"
                     "• 📷 दवा की पत्ती (strip) की फ़ोटो भेजें: बैच जाँच देंगे\n• बैच नंबर भेजें, जैसे AT25-0938A\n"
                     "• दवा लेने के बाद: 1 या दवा ले ली\n• पूछें: आज कौन सी दवा?\n"
                     "• रीडिंग भेजें: BP 130/85\n• दवा की कीमत: डोलो 650 कितने की है?\n• परिवार को बुलाना हो: बेटे को बुलाओ\n\n"
                     "दवा का समय होने पर हम यहीं याद दिलाएँगे।")
        telegram.send(chat_id, reply, TG_BUTTONS if r and r["role"] == "self" else None)
        return reply
    dev = telegram.device_of(conn, chat_id)
    if not dev:
        reply = "This chat only receives alerts. To talk to KinCare, open Dadi mode in the app and press “Connect Telegram”."
        telegram.send(chat_id, reply)
        return reply
    clean = text.replace("📞", "").replace("✅", "").strip()
    a = dadi_turn(dev, clean, _tg_lang(clean), default_member(dev), "telegram")
    telegram.send(chat_id, a["say"], TG_BUTTONS)
    return a["say"]


@router.get("/api/telegram/info")
def telegram_info(account: str = Depends(current_account)):
    dev = account
    return {"ready": telegram.ready() and bool(telegram.bot_name()), "bot": telegram.bot_name(), "linked": len(telegram.chats(conn, dev))}


@router.post("/api/telegram/link")
def telegram_link(role: str = Query("self"), account: str = Depends(current_account)):
    if not telegram.ready() or not telegram.bot_name():
        raise HTTPException(503, "Telegram isn't set up on this server. Add TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_NAME (free from @BotFather).")
    code = telegram.link_code(conn, account, "caregiver" if role == "caregiver" else "self")
    return {"url": telegram.link_url(code), "code": code}


@router.delete("/api/telegram/link")
def telegram_unlink(account: str = Depends(current_account)):
    return {"removed": telegram.unlink(conn, account)}


@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    import os

    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if not secret or request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        raise HTTPException(401, "Bad secret")
    telegram_handle(await request.json())
    return {"ok": True}


@on_startup
def _telegram_poll():
    """No webhook configured: long-poll, so the bot works from a laptop with no public URL."""
    import os
    import threading

    if telegram.ready() and not os.environ.get("TELEGRAM_WEBHOOK_SECRET"):
        threading.Thread(target=telegram.poll, args=(telegram_handle,), daemon=True).start()


# Imported last, used only when a request runs: these modules import from this one too.
from routes.dadi import dadi_turn, default_member  # noqa: E402
from routes.whatsapp_bot import strip_photo_reply  # noqa: E402
