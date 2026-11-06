"""Phone login with a one-time code on WhatsApp. One account per phone number, any number of devices.

KinCare keys everything by a device id. Logging in maps the phone to one *account device id*; a new phone that
logs in adopts that id, and anything it had created before is merged in. So a family's data follows them.

Codes: 6 digits, stored hashed, 10 minutes, 5 tries, at most 3 sends per number per 10 minutes.
Without a WhatsApp provider configured (local demo), the code is returned in the response and the UI says so.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    phone TEXT PRIMARY KEY,
    device TEXT NOT NULL UNIQUE,      -- the account's device id; every logged-in phone uses it
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS otps (
    id INTEGER PRIMARY KEY,
    phone TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otps_phone ON otps(phone, created_at);
"""

TTL = timedelta(minutes=10)
MAX_TRIES = 5
MAX_SENDS = 3
_SALT = os.environ.get("OTP_SECRET") or secrets.token_hex(16)  # per-process if unset: codes don't survive a restart


class AuthError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(phone: str, code: str) -> str:
    return hmac.new(_SALT.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def start(conn: sqlite3.Connection, phone: str) -> str:
    """Make a code for this phone. Raises AuthError when rate-limited."""
    since = (_now() - TTL).isoformat()
    sent = conn.execute("SELECT COUNT(*) FROM otps WHERE phone = ? AND created_at >= ?", (phone, since)).fetchone()[0]
    if sent >= MAX_SENDS:
        raise AuthError("Too many codes sent to this number. Try again in 10 minutes.")
    code = f"{secrets.randbelow(10**6):06d}"
    conn.execute("UPDATE otps SET used = 1 WHERE phone = ? AND used = 0", (phone,))  # only the newest code works
    conn.execute("INSERT INTO otps (phone, code_hash, expires_at, created_at) VALUES (?,?,?,?)",
                 (phone, _hash(phone, code), (_now() + TTL).isoformat(), _now().isoformat()))
    conn.commit()
    return code


def verify(conn: sqlite3.Connection, phone: str, code: str) -> None:
    r = conn.execute("SELECT * FROM otps WHERE phone = ? AND used = 0 ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    if not r:
        raise AuthError("Ask for a new code.")
    if datetime.fromisoformat(r["expires_at"]) < _now():
        raise AuthError("That code has expired. Ask for a new one.")
    if r["attempts"] >= MAX_TRIES:
        raise AuthError("Too many wrong tries. Ask for a new code.")
    conn.execute("UPDATE otps SET attempts = attempts + 1 WHERE id = ?", (r["id"],))
    if not hmac.compare_digest(r["code_hash"], _hash(phone, code.strip())):
        conn.commit()
        left = MAX_TRIES - r["attempts"] - 1
        raise AuthError(f"Wrong code. {left} {'try' if left == 1 else 'tries'} left." if left else "Too many wrong tries. Ask for a new code.")
    conn.execute("UPDATE otps SET used = 1 WHERE id = ?", (r["id"],))
    conn.commit()


def _device_tables(conn: sqlite3.Connection) -> list[str]:
    out = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        if t not in ("users", "otps") and any(c[1] == "device" for c in conn.execute(f"PRAGMA table_info({t})")):
            out.append(t)
    return out


def merge(conn: sqlite3.Connection, src: str, dst: str) -> int:
    """Move everything recorded under device `src` to the account device `dst`. Rows that would clash
    (e.g. the same batch already on the account's watchlist) keep the account's copy."""
    if src == dst:
        return 0
    moved = 0
    for t in _device_tables(conn):
        moved += conn.execute(f"UPDATE OR IGNORE {t} SET device = ? WHERE device = ?", (dst, src)).rowcount
        conn.execute(f"DELETE FROM {t} WHERE device = ?", (src,))
    # Caregiver links key the two sides separately; they follow the account too.
    for t, cols in (("care_links", ("elder_device", "caregiver_device")), ("care_invites", ("elder_device",))):
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (t,)).fetchone():
            for c in cols:
                moved += conn.execute(f"UPDATE {t} SET {c} = ? WHERE {c} = ?", (dst, src)).rowcount
    conn.commit()
    return moved


def login(conn: sqlite3.Connection, phone: str, current_device: str) -> dict:
    """After a verified code: the account device id this phone should use from now on."""
    u = conn.execute("SELECT device FROM users WHERE phone = ?", (phone,)).fetchone()
    if not u:
        conn.execute("INSERT INTO users (phone, device, created_at) VALUES (?,?,?)", (phone, current_device, _now().isoformat()))
        conn.commit()
        return {"device": current_device, "new": True, "merged": 0}
    return {"device": u["device"], "new": False, "merged": merge(conn, current_device, u["device"])}


def phone_of(conn: sqlite3.Connection, device: str) -> str | None:
    r = conn.execute("SELECT phone FROM users WHERE device = ?", (device,)).fetchone()
    return r[0] if r else None


def otp_text(code: str) -> str:
    return f"KinCare login code: *{code}*\nValid for 10 minutes. Never share it with anyone, not even KinCare staff."
