"""A person's rights over their health data (India's DPDP Act, 2023): see everything held about them, and erase it.

Everything KinCare stores about a person hangs off their device id (or the account device id after phone login):
directly in every table with a `device` column, or one step away (a plan's medicines and doses, a caregiver link's
access log, the phone number used to log in).
"""
import sqlite3

import auth
import vault

DEVICE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
# Values a broken client could send for everyone at once; accepting them would pool strangers' health data.
SHARED_IDS = {"anonymous", "null", "undefined", "none", "device", "test"}


def valid_device_id(d: str | None) -> bool:
    return bool(d) and 2 <= len(d) <= 64 and set(d) <= DEVICE_ID_CHARS and d.lower() not in SHARED_IDS


def _rows(conn, sql: str, args=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _med_ids(conn, dev: str) -> list[int]:
    return [r[0] for r in conn.execute("SELECT m.id FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ?", (dev,))]


def _link_ids(conn, dev: str) -> list[int]:
    return [r[0] for r in conn.execute("SELECT id FROM care_links WHERE elder_device = ? OR caregiver_device = ?", (dev, dev))]


def _in(ids: list) -> tuple[str, list]:
    return ",".join("?" * len(ids)) or "NULL", ids


def export(conn: sqlite3.Connection, dev: str) -> dict:
    """Every row held about this device, table by table. Secrets (login code hashes, push keys) are left out."""
    out: dict = {}
    for t in auth._device_tables(conn):
        if t in ("push_subs", "tg_codes"):
            continue  # browser push keys and one-time link codes: credentials, not personal data
        rows = [vault.open_row(t, r) for r in _rows(conn, f"SELECT * FROM {t} WHERE device = ?", (dev,))]
        if rows:
            out[t] = rows
    meds = _med_ids(conn, dev)
    q, a = _in(meds)
    out["plan_medicines"] = _rows(conn, f"SELECT * FROM plan_meds WHERE id IN ({q})", a)
    out["doses_taken"] = _rows(conn, f"SELECT * FROM doses WHERE med_id IN ({q})", a)
    out["caregiver_links"] = _rows(conn, "SELECT * FROM care_links WHERE elder_device = ? OR caregiver_device = ?", (dev, dev))
    q, a = _in(_link_ids(conn, dev))
    out["caregiver_access_log"] = _rows(conn, f"SELECT * FROM care_access WHERE link_id IN ({q})", a)
    phone = auth.phone_of(conn, dev)
    if phone:
        out["login"] = {"phone": phone}
        out["messages_sent_to_your_phone"] = _rows(conn, "SELECT channel, message, status, at FROM notifications WHERE phone = ?", (phone,))
    return {k: v for k, v in out.items() if v}


def erase(conn: sqlite3.Connection, dev: str) -> dict:
    """Delete everything held about this device. Caregiver links end for both sides; the other person keeps nothing of yours."""
    counts: dict = {}

    def run(label: str, sql: str, args=()):
        n = conn.execute(sql, args).rowcount
        if n:
            counts[label] = counts.get(label, 0) + n

    meds = _med_ids(conn, dev)
    q, a = _in(meds)
    for t in ("doses", "reminders_sent"):
        run(t, f"DELETE FROM {t} WHERE med_id IN ({q})", a)
    run("plan_meds", f"DELETE FROM plan_meds WHERE id IN ({q})", a)
    q, a = _in(_link_ids(conn, dev))
    run("care_access", f"DELETE FROM care_access WHERE link_id IN ({q})", a)
    run("care_alerts_sent", f"DELETE FROM care_alerts_sent WHERE link_id IN ({q})", a)
    run("care_links", "DELETE FROM care_links WHERE elder_device = ? OR caregiver_device = ?", (dev, dev))
    run("care_invites", "DELETE FROM care_invites WHERE elder_device = ?", (dev,))
    phone = auth.phone_of(conn, dev)
    if phone:
        run("notifications", "DELETE FROM notifications WHERE phone = ?", (phone,))
        run("otps", "DELETE FROM otps WHERE phone = ?", (phone,))
        run("users", "DELETE FROM users WHERE phone = ?", (phone,))
    for t in auth._device_tables(conn):
        run(t, f"DELETE FROM {t} WHERE device = ?", (dev,))
    conn.commit()
    return counts


# Raw data kept only as long as it is useful (DPDP: storage limitation).
RETENTION = [
    ("vitals_live", "at", 7),   # 2-second samples; the 5-minute medians stay in vitals
    ("dadi_chat", "at", 180),
    ("otps", "created_at", 1),
    ("care_access", "at", 365),
]


def purge_old(conn: sqlite3.Connection) -> int:
    n = 0
    for table, col, days in RETENTION:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone():
            n += conn.execute(f"DELETE FROM {table} WHERE {col} < datetime('now', ?)", (f"-{days} days",)).rowcount
    conn.commit()
    return n
