"""Telegram: the free chat channel. No per-message fee, no 24-hour window, no template approval.

WhatsApp Cloud API charges for every message outside the 24-hour window, so KinCare uses Telegram's Bot API
for chat and alerts: an elder can talk to KinCare there (same answers as Dadi mode), and caregivers get missed-dose
and urgent-vitals alerts there, all free at any volume.

Setup: talk to @BotFather on Telegram, /newbot, copy the token.
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_NAME (the bot's username, without @).
Optional TELEGRAM_WEBHOOK_SECRET: set it when you register a webhook (production). Without it KinCare long-polls
getUpdates in a background thread, so it works on a laptop with no public URL (hackathon demo).

Linking: KinCare makes a one-time code for a device, the person opens t.me/<bot>?start=<code>, Telegram sends
"/start <code>" and the chat is tied to that device. Nobody can message a person who hasn't pressed Start.
"""
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

API = "https://api.telegram.org"
LINK_TTL = timedelta(hours=24)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tg_links (
    chat_id INTEGER NOT NULL,
    device TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'self',   -- self: the elder talks to KinCare; caregiver: receives alerts
    name TEXT,
    linked_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, device)
);
CREATE INDEX IF NOT EXISTS idx_tg_device ON tg_links(device);
CREATE TABLE IF NOT EXISTS tg_codes (
    code TEXT PRIMARY KEY,
    device TEXT NOT NULL,
    role TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def ready() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def bot_name() -> str | None:
    return os.environ.get("TELEGRAM_BOT_NAME") or None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def link_code(conn: sqlite3.Connection, device: str, role: str = "self") -> str:
    code = secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")  # Telegram start params: [A-Za-z0-9_-], <= 64
    conn.execute("INSERT INTO tg_codes (code, device, role, expires_at) VALUES (?,?,?,?)", (code, device, role, (_now() + LINK_TTL).isoformat()))
    conn.commit()
    return code


def link_url(code: str) -> str | None:
    return f"https://t.me/{bot_name()}?start={code}" if bot_name() else None


def claim(conn: sqlite3.Connection, code: str, chat_id: int, name: str | None) -> dict | None:
    """'/start <code>' arrived: tie this chat to the code's device. One use."""
    r = conn.execute("SELECT * FROM tg_codes WHERE code = ?", (code,)).fetchone()
    if not r or datetime.fromisoformat(r["expires_at"]) < _now():
        return None
    conn.execute("DELETE FROM tg_codes WHERE code = ?", (code,))
    conn.execute("INSERT INTO tg_links (chat_id, device, role, name, linked_at) VALUES (?,?,?,?,?) "
                 "ON CONFLICT(chat_id, device) DO UPDATE SET role = excluded.role, name = excluded.name",
                 (chat_id, r["device"], r["role"], name, _now().isoformat()))
    conn.commit()
    return {"device": r["device"], "role": r["role"]}


def chats(conn: sqlite3.Connection, device: str, role: str | None = None) -> list[int]:
    q = "SELECT chat_id FROM tg_links WHERE device = ?" + (" AND role = ?" if role else "")
    return [r[0] for r in conn.execute(q, (device, role) if role else (device,))]


def device_of(conn: sqlite3.Connection, chat_id: int) -> str | None:
    """The elder device a chat talks for (a 'self' link), newest first."""
    r = conn.execute("SELECT device FROM tg_links WHERE chat_id = ? AND role = 'self' ORDER BY linked_at DESC LIMIT 1", (chat_id,)).fetchone()
    return r[0] if r else None


def unlink(conn: sqlite3.Connection, device: str) -> int:
    n = conn.execute("DELETE FROM tg_links WHERE device = ?", (device,)).rowcount
    conn.commit()
    return n


def send(chat_id: int, text: str, buttons: list[str] | None = None) -> bool:
    """Plain text with optional one-tap reply buttons (big, for older thumbs)."""
    if not ready():
        return False
    body: dict = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if buttons:
        body["reply_markup"] = {"keyboard": [[{"text": b}] for b in buttons], "resize_keyboard": True}
    try:
        r = requests.post(f"{API}/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage", json=body, timeout=15)
    except requests.RequestException as e:
        print("telegram:", e)
        return False
    if not r.ok:
        print("telegram:", r.status_code, r.text[:200])
    return r.ok


def send_device(conn: sqlite3.Connection, device: str, text: str, role: str | None = None, buttons: list[str] | None = None) -> int:
    return sum(send(c, text, buttons) for c in chats(conn, device, role))


def incoming(update: dict) -> tuple[int, str, str | None] | None:
    """(chat_id, text, first name) from one update, or None for anything that isn't a text message."""
    m = update.get("message") or update.get("edited_message") or {}
    if not m.get("text") or not m.get("chat"):
        return None
    return m["chat"]["id"], m["text"].strip(), (m.get("from") or {}).get("first_name")


def incoming_photo(update: dict) -> tuple[int, str] | None:
    """(chat_id, file_id) of the largest size of a photo (or an image sent as a file)."""
    m = update.get("message") or {}
    if not m.get("chat"):
        return None
    if m.get("photo"):
        return m["chat"]["id"], m["photo"][-1]["file_id"]
    d = m.get("document") or {}
    if d.get("mime_type", "").startswith("image/"):
        return m["chat"]["id"], d["file_id"]
    return None


def download(file_id: str) -> bytes | None:
    """getFile gives a path; the bytes come from the file endpoint with the same token. Max 10 MB."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    try:
        r = requests.get(f"{API}/bot{tok}/getFile", params={"file_id": file_id}, timeout=20)
        r.raise_for_status()
        img = requests.get(f"{API}/file/bot{tok}/{r.json()['result']['file_path']}", timeout=30)
        img.raise_for_status()
    except (requests.RequestException, KeyError, ValueError) as e:
        print("telegram download:", e)
        return None
    return img.content if len(img.content) <= 10_000_000 else None


def poll(handle, stop=None) -> None:
    """Long-poll getUpdates forever (no webhook needed). `handle(update)` answers each one."""
    import time

    offset = 0
    url = f"{API}/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
    try:
        requests.post(f"{url}/deleteWebhook", timeout=15)  # getUpdates doesn't work while a webhook is set
    except requests.RequestException:
        pass
    while not (stop and stop()):
        try:
            r = requests.get(f"{url}/getUpdates", params={"offset": offset, "timeout": 50}, timeout=60)
            for u in r.json().get("result", []):
                offset = u["update_id"] + 1
                try:
                    handle(u)
                except Exception as e:  # one bad message never stops the bot
                    print("telegram handle:", e)
        except Exception as e:
            print("telegram poll:", e)
            time.sleep(5)
