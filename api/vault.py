"""Encryption at rest for the most sensitive free text: chat messages, doctor messages, diagnoses.

AES-256-GCM, a fresh 96-bit nonce per value, and the table + column as associated data, so a ciphertext copied into
another column does not decrypt. Stored as "enc1:<base64url(nonce || ciphertext)>"; rows written before encryption
existed are read as plain text and encrypted once at startup (migrate).

Key: KINCARE_DATA_KEY (base64url of 32 bytes, or any long secret string; set it on the server and keep it out of the database backups), else a key
generated once into data/data.key next to the database (file mode 600). Losing the key loses these fields.
"""
import base64
import hashlib
import os
import secrets
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from db import DB_PATH

PREFIX = "enc1:"
FIELDS = {"dadi_chat": ("text", "data"), "doctor_messages": ("text",), "plans": ("diagnosis",)}
KEY_FILE = Path(os.environ.get("KINCARE_DATA_KEY_FILE", DB_PATH.parent / "data.key"))
_aead: AESGCM | None = None


def _key() -> AESGCM:
    global _aead
    if _aead is None:
        raw = os.environ.get("KINCARE_DATA_KEY")
        if raw:
            try:
                key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            except ValueError:
                key = b""
            if len(key) != 32:  # any other secret string (e.g. Render's generateValue): derive the 256-bit key from it
                key = hashlib.sha256(raw.encode()).digest()
        elif KEY_FILE.exists():
            key = KEY_FILE.read_bytes()
        else:
            key = secrets.token_bytes(32)
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
        if len(key) != 32:
            raise ValueError("data.key must hold 32 bytes")
        _aead = AESGCM(key)
    return _aead


def seal(value: str | None, table: str, column: str) -> str | None:
    if value is None or value.startswith(PREFIX):
        return value
    nonce = secrets.token_bytes(12)
    ct = _key().encrypt(nonce, value.encode(), f"{table}.{column}".encode())
    return PREFIX + base64.urlsafe_b64encode(nonce + ct).decode()


def open_(value: str | None, table: str, column: str) -> str | None:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        return value  # plain text from before encryption, or NULL
    blob = base64.urlsafe_b64decode(value[len(PREFIX):])
    return _key().decrypt(blob[:12], blob[12:], f"{table}.{column}".encode()).decode()


def open_row(table: str, row: dict) -> dict:
    for col in FIELDS.get(table, ()):
        if col in row:
            row[col] = open_(row[col], table, col)
    return row


def migrate(conn: sqlite3.Connection) -> int:
    """Encrypt every value still stored in plain text. Safe to run on every start."""
    n = 0
    for table, cols in FIELDS.items():
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone():
            continue
        for col in cols:
            for rid, v in conn.execute(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} NOT LIKE ?", (PREFIX + "%",)).fetchall():
                conn.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (seal(v, table, col), rid))
                n += 1
    conn.commit()
    return n
