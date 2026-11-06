"""Phone notifications (Web Push) for doses, refills and recalls, even with KinCare closed.

Keys: set VAPID_PRIVATE_KEY_FILE / VAPID_PUBLIC_KEY, or KinCare makes a key pair once under data/.
Without the pywebpush package every send is a no-op and the app falls back to WhatsApp / in-page alerts.
"""
import base64
import json
import os
import sqlite3
from pathlib import Path

from db import DB_PATH

KEY_FILE = Path(os.environ.get("VAPID_PRIVATE_KEY_FILE", DB_PATH.parent / "vapid_private.pem"))
CLAIMS = {"sub": os.environ.get("VAPID_SUB", "mailto:team@kincare.app")}

SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint TEXT PRIMARY KEY,
    device TEXT NOT NULL,
    sub TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_push_device ON push_subs(device);
"""

_public: str | None = None


def ready() -> bool:
    try:
        import pywebpush  # noqa: F401
    except ImportError:
        return False
    return True


def public_key() -> str | None:
    """Browser applicationServerKey: base64url of the uncompressed P-256 point."""
    global _public
    if _public or not ready():
        return _public
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    if os.environ.get("VAPID_PUBLIC_KEY"):
        _public = os.environ["VAPID_PUBLIC_KEY"]
        return _public
    if KEY_FILE.exists():
        key = serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)
    else:
        key = ec.generate_private_key(ec.SECP256R1())
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    _public = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return _public


def subscribe(conn: sqlite3.Connection, device: str, sub: dict) -> None:
    conn.execute("INSERT OR REPLACE INTO push_subs (endpoint, device, sub) VALUES (?,?,?)", (sub["endpoint"], device, json.dumps(sub)))
    conn.commit()


def unsubscribe(conn: sqlite3.Connection, device: str, endpoint: str | None = None) -> None:
    if endpoint:
        conn.execute("DELETE FROM push_subs WHERE device = ? AND endpoint = ?", (device, endpoint))
    else:
        conn.execute("DELETE FROM push_subs WHERE device = ?", (device,))
    conn.commit()


def has_subs(conn: sqlite3.Connection, device: str) -> bool:
    return conn.execute("SELECT 1 FROM push_subs WHERE device = ?", (device,)).fetchone() is not None


def send(conn: sqlite3.Connection, device: str, title: str, body: str, url: str = "/care", tag: str | None = None) -> int:
    """Notify every browser this device turned notifications on in. Returns how many got it."""
    if not ready() or not public_key():
        return 0
    from pywebpush import WebPushException, webpush

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    sent = 0
    for r in conn.execute("SELECT endpoint, sub FROM push_subs WHERE device = ?", (device,)).fetchall():
        try:
            webpush(json.loads(r["sub"]), payload, vapid_private_key=str(KEY_FILE), vapid_claims=dict(CLAIMS), ttl=3600)
            sent += 1
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):  # browser dropped the subscription
                conn.execute("DELETE FROM push_subs WHERE endpoint = ?", (r["endpoint"],))
                conn.commit()
            else:
                print("push:", e)
    return sent
