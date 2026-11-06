"""Real WhatsApp through Meta's own WhatsApp Cloud API: free to set up, no middleman markup.

Cost model (India, per Meta, 2026): messages people send us are free, and replies inside the
24-hour window after their last message are free or near-free. A message outside that window
must use an approved template (Utility, about ₹0.115 + GST). So KinCare keeps the window open:
every reminder says "reply 1 when taken", the reply ticks the dose AND reopens the window.

Env: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID (from Meta > WhatsApp > API setup), WHATSAPP_NUMBER
(the business number, for the "say hi" join link), WHATSAPP_VERIFY_TOKEN (any string, for the
webhook), optional WHATSAPP_APP_SECRET (verifies webhook signatures), WHATSAPP_TEMPLATE
(approved Utility template with one body variable {{1}}, used outside the window).
"""
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

GRAPH = "https://graph.facebook.com/v21.0"
WINDOW = timedelta(hours=23, minutes=50)  # a little under 24 h, so a slow send never lands outside
PAID_CAP = 50          # paid (template) messages per number per month; past it, reminders go as free phone notifications
PAID_RATE_INR = 0.115 * 1.18  # Meta India Utility rate + GST, per delivered template message

SCHEMA = """
CREATE TABLE IF NOT EXISTS wa_paid (
    phone TEXT NOT NULL,
    month TEXT NOT NULL,             -- 2026-10
    n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (phone, month)
);
CREATE TABLE IF NOT EXISTS wa_inbound (
    phone TEXT PRIMARY KEY,          -- +91..., same format as the rest of KinCare
    last_at TEXT NOT NULL,
    last_text TEXT
);
"""


def ready() -> bool:
    return bool(os.environ.get("WHATSAPP_TOKEN") and os.environ.get("WHATSAPP_PHONE_ID"))


def join_url(text: str = "JOIN") -> str | None:
    """wa.me link that opens a chat with KinCare with a message typed in; sending it opens the free window."""
    n = re.sub(r"\D", "", os.environ.get("WHATSAPP_NUMBER", ""))
    return f"https://wa.me/{n}?text={requests.utils.quote(text)}" if n else None


def to_e164(wa_id: str) -> str:
    return "+" + re.sub(r"\D", "", wa_id)


def window_open(conn: sqlite3.Connection, phone: str, now: datetime | None = None) -> bool:
    r = conn.execute("SELECT last_at FROM wa_inbound WHERE phone = ?", (phone,)).fetchone()
    return bool(r) and (now or datetime.now(timezone.utc)) - datetime.fromisoformat(r[0]) < WINDOW


def record_inbound(conn: sqlite3.Connection, phone: str, text: str) -> None:
    conn.execute("INSERT INTO wa_inbound (phone, last_at, last_text) VALUES (?,?,?) ON CONFLICT(phone) DO UPDATE SET last_at = excluded.last_at, last_text = excluded.last_text",
                 (phone, datetime.now(timezone.utc).isoformat(), text[:200]))
    conn.commit()


def template_param(text: str) -> str:
    """Template variables can't hold newlines, tabs or 4+ spaces, and must stay short."""
    t = re.sub(r"\s*\n\s*", " · ", text).replace("\t", " ")
    t = re.sub(r" {4,}", " ", t)
    return t[:900]


def payload(phone: str, text: str, in_window: bool, lang: str = "en") -> dict:
    to = re.sub(r"\D", "", phone)
    template = os.environ.get("WHATSAPP_TEMPLATE")
    if in_window or not template:
        # Without a template, free text is the only option; Meta drops it outside the window (error 131047).
        return {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000], "preview_url": True}}
    return {"messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {"name": template, "language": {"code": os.environ.get("WHATSAPP_TEMPLATE_LANG", "en")},
                         "components": [{"type": "body", "parameters": [{"type": "text", "text": template_param(text)}]}]}}


def paid_this_month(conn: sqlite3.Connection, phone: str) -> int:
    r = conn.execute("SELECT n FROM wa_paid WHERE phone = ? AND month = ?", (phone, datetime.now().strftime("%Y-%m"))).fetchone()
    return r[0] if r else 0


def send(conn: sqlite3.Connection, phone: str, text: str, urgent: bool = False) -> tuple[str, str | None]:
    """('sent', id), ('failed', None) or ('capped', None). Free text inside the window, the paid template outside it.

    Paid sends stop at PAID_CAP per number per month so a plan can never cost more than it earns;
    urgent messages (recalls, SOS) always go."""
    open_ = window_open(conn, phone)
    paid = not open_ and bool(os.environ.get("WHATSAPP_TEMPLATE"))
    if paid and not urgent and paid_this_month(conn, phone) >= PAID_CAP:
        return "capped", None
    body = payload(phone, text, open_)
    try:
        r = requests.post(f"{GRAPH}/{os.environ['WHATSAPP_PHONE_ID']}/messages", json=body,
                          headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"}, timeout=20)
    except requests.RequestException as e:
        print("whatsapp:", e)
        return "failed", None
    if not r.ok:
        print("whatsapp:", r.status_code, r.text[:300])
        return "failed", None
    if paid:
        conn.execute("INSERT INTO wa_paid (phone, month, n) VALUES (?,?,1) ON CONFLICT(phone, month) DO UPDATE SET n = n + 1",
                     (phone, datetime.now().strftime("%Y-%m")))
        conn.commit()
    return "sent", (r.json().get("messages") or [{}])[0].get("id")


def signature_ok(raw: bytes, header: str | None) -> bool:
    secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not secret:
        # Unsigned webhooks are accepted only on a demo laptop; anywhere else anyone could post "1" as any phone.
        return os.environ.get("KINCARE_DEMO") == "1"
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


def incoming(body: dict) -> list[tuple[str, str]]:
    """(phone, text) for every text or button message in a webhook call. Status callbacks are ignored."""
    out = []
    for entry in body.get("entry", []):
        for ch in entry.get("changes", []):
            for m in ch.get("value", {}).get("messages", []) or []:
                text = (m.get("text") or {}).get("body") or (m.get("button") or {}).get("text") \
                    or ((m.get("interactive") or {}).get("button_reply") or {}).get("title") or ""
                if m.get("from"):
                    out.append((to_e164(m["from"]), text.strip()))
    return out


def incoming_images(body: dict) -> list[tuple[str, str, str]]:
    """(phone, media_id, caption) for every photo in a webhook call: a strip photographed and sent to KinCare."""
    out = []
    for entry in body.get("entry", []):
        for ch in entry.get("changes", []):
            for m in ch.get("value", {}).get("messages", []) or []:
                media = m.get("image") or (m.get("document") if (m.get("document") or {}).get("mime_type", "").startswith("image/") else None)
                if m.get("from") and media and media.get("id"):
                    out.append((to_e164(m["from"]), media["id"], (media.get("caption") or "").strip()))
    return out


def download_media(media_id: str) -> bytes | None:
    """Fetch a photo the patient sent: Graph API gives a short-lived URL, which needs the same token."""
    auth = {"Authorization": f"Bearer {os.environ.get('WHATSAPP_TOKEN', '')}"}
    try:
        meta = requests.get(f"{GRAPH}/{media_id}", headers=auth, timeout=20)
        meta.raise_for_status()
        img = requests.get(meta.json()["url"], headers=auth, timeout=30)
        img.raise_for_status()
    except (requests.RequestException, KeyError, ValueError) as e:
        print("whatsapp media:", e)
        return None
    return img.content if len(img.content) <= 10_000_000 else None


TAKEN = re.compile(r"^\s*(1|ok|okay|done|taken|took|le li|le liya|li|haan|ha|yes|✅|👍)\s*[.!]*\s*$", re.I)
GREETING = re.compile(r"^\s*(hi|hii+|hello|hey|join|start|namaste|नमस्ते)\b", re.I)
BATCH = re.compile(r"(?:batch|b\.?\s*no\.?|check)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/\-.]{3,19})\s*$", re.I)


def intent(text: str) -> tuple[str, str | None]:
    """What a patient's message means: taken / hello / batch check / other."""
    if TAKEN.match(text):
        return "taken", None
    if GREETING.match(text):
        return "hello", None
    m = BATCH.search(text.strip())
    if m and re.search(r"\d", m.group(1)):
        return "batch", m.group(1).upper()
    return "other", None
