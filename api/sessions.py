"""Who is calling: a server-issued session, never an id the browser makes up.

A session is a random 256-bit token. The server stores only its SHA-256 hash, so a copy of the database cannot be used
to log in as anyone. The browser keeps the token in an HttpOnly cookie (scripts on the page can't read it); API clients
may send it as `Authorization: Bearer <token>` instead.

Every row of personal data is keyed by an *account id*: a random id the server creates and never sends to the client.
A visitor who hasn't signed in gets a guest account; signing in with a phone moves the guest's data into the phone's
account (auth.merge) and replaces the guest session with a signed-in one.

Lifetimes: guest sessions 90 days, signed-in sessions 30 days, both sliding (extended while in use), revocable any time.
"""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

COOKIE = "kincare_session"
LIFETIME = {"guest": timedelta(days=90), "user": timedelta(days=30)}
TOUCH_EVERY = timedelta(hours=1)  # last_seen / expiry are rewritten at most once an hour per session

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,              -- public handle, for "signed-in devices" (not a credential)
    token_hash TEXT NOT NULL UNIQUE,  -- sha256 of the token; the token itself is never stored
    account TEXT NOT NULL,
    kind TEXT NOT NULL,               -- guest | user
    label TEXT,                       -- "Chrome on Android", for the devices list
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_account_id() -> str:
    return "acct_" + secrets.token_hex(16)


def label_of(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    browser = next((b for k, b in (("edg/", "Edge"), ("chrome", "Chrome"), ("firefox", "Firefox"), ("safari", "Safari")) if k in ua), "Browser")
    os_ = next((o for k, o in (("android", "Android"), ("iphone", "iPhone"), ("ipad", "iPad"), ("windows", "Windows"), ("mac os", "Mac"), ("linux", "Linux")) if k in ua), "")
    return f"{browser} on {os_}" if os_ else browser


def create(conn: sqlite3.Connection, account: str, kind: str = "guest", user_agent: str | None = None) -> str:
    """A new session for this account. Returns the token (shown once, to be put in the cookie)."""
    token = secrets.token_urlsafe(32)  # 256 bits
    now = _now()
    conn.execute("INSERT INTO sessions (id, token_hash, account, kind, label, created_at, last_seen, expires_at) VALUES (?,?,?,?,?,?,?,?)",
                 ("ses_" + secrets.token_hex(8), _hash(token), account, kind, label_of(user_agent), now.isoformat(), now.isoformat(),
                  (now + LIFETIME[kind]).isoformat()))
    conn.commit()
    return token


def resolve(conn: sqlite3.Connection, token: str | None) -> dict | None:
    """The live session for a token, or None (missing, unknown, expired or revoked)."""
    if not token or len(token) > 100:
        return None
    r = conn.execute("SELECT * FROM sessions WHERE token_hash = ?", (_hash(token),)).fetchone()
    if not r or r["revoked_at"]:
        return None
    now = _now()
    if datetime.fromisoformat(r["expires_at"]) < now:
        return None
    if now - datetime.fromisoformat(r["last_seen"]) > TOUCH_EVERY:  # sliding expiry
        conn.execute("UPDATE sessions SET last_seen = ?, expires_at = ? WHERE id = ?",
                     (now.isoformat(), (now + LIFETIME[r["kind"]]).isoformat(), r["id"]))
        conn.commit()
    return dict(r)


def revoke(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL", (_now().isoformat(), _hash(token)))
    conn.commit()


def revoke_id(conn: sqlite3.Connection, account: str, sid: str) -> bool:
    n = conn.execute("UPDATE sessions SET revoked_at = ? WHERE id = ? AND account = ? AND revoked_at IS NULL", (_now().isoformat(), sid, account)).rowcount
    conn.commit()
    return bool(n)


def revoke_all(conn: sqlite3.Connection, account: str, except_token: str | None = None) -> int:
    keep = _hash(except_token) if except_token else ""
    n = conn.execute("UPDATE sessions SET revoked_at = ? WHERE account = ? AND revoked_at IS NULL AND token_hash != ?",
                     (_now().isoformat(), account, keep)).rowcount
    conn.commit()
    return n


def active(conn: sqlite3.Connection, account: str, current_token: str | None = None) -> list[dict]:
    cur = _hash(current_token) if current_token else ""
    rows = conn.execute("SELECT id, kind, label, created_at, last_seen, token_hash FROM sessions WHERE account = ? AND revoked_at IS NULL AND expires_at > ? "
                        "ORDER BY last_seen DESC", (account, _now().isoformat())).fetchall()
    return [{k: r[k] for k in ("id", "kind", "label", "created_at", "last_seen")} | {"current": r["token_hash"] == cur} for r in rows]
