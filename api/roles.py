"""Role-based access control. Every account is a patient; pharmacist, regulator and admin are granted, never assumed.

Roles map to permissions, endpoints ask for one permission (core.require). Caregivers and doctors are not roles:
their access comes from a consent link to one person (caregiver.py, doctor links) and is checked per record.
"""
import sqlite3

from datetime import datetime, timezone

PATIENT, PHARMACIST, REGULATOR, ADMIN = "patient", "pharmacist", "regulator", "admin"
REQUESTABLE = (PHARMACIST, REGULATOR)  # admin is only granted by an existing admin

PERMISSIONS: dict[str, tuple[str, ...]] = {
    # pharmacist: their own shop's sales register and its customers
    "sales.manage": (PHARMACIST,),
    "buyers.notify": (PHARMACIST,),
    "recall.run": (PHARMACIST, REGULATOR, ADMIN),
    # regulator: who holds a flagged batch (names, phones, next dose) across KinCare
    "controller.view": (REGULATOR, ADMIN),
    "holders.view": (REGULATOR, ADMIN),
    "holders.alert": (REGULATOR, ADMIN),
    "notifications.view": (REGULATOR, ADMIN),
    # admin only
    "recall.demo_contact": (ADMIN,),
    "demo.seed": (ADMIN,),
    "ingest.run": (ADMIN,),
    "roles.decide": (ADMIN,),
    "audit.view": (ADMIN,),
    "admin.view": (ADMIN,),
}

LABEL = {PHARMACIST: "Pharmacist", REGULATOR: "Drug regulator", ADMIN: "KinCare admin"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS role_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device TEXT NOT NULL,              -- account id (column named like every other per-account table)
    role TEXT NOT NULL,
    status TEXT NOT NULL,              -- pending | active | rejected | revoked
    org TEXT,                          -- pharmacy name / office
    licence TEXT,                      -- drug licence no. / employee id, checked by the admin
    requested_at TEXT NOT NULL,
    decided_at TEXT,
    decided_by TEXT
);
CREATE INDEX IF NOT EXISTS role_grants_device ON role_grants(device, status);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,               -- account id, or 'admin-token'
    role TEXT,
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def of(conn: sqlite3.Connection, account: str | None) -> set[str]:
    if not account:
        return set()
    return {PATIENT} | {r[0] for r in conn.execute("SELECT role FROM role_grants WHERE device = ? AND status = 'active'", (account,))}


def allowed(roles_held: set[str], permission: str) -> bool:
    return bool(roles_held & set(PERMISSIONS[permission]))


def permissions(roles_held: set[str]) -> list[str]:
    return sorted(p for p in PERMISSIONS if allowed(roles_held, p))


def audit(conn: sqlite3.Connection, actor: str, action: str, target: str | None = None, detail: str | None = None, role: str | None = None):
    conn.execute("INSERT INTO audit_log (at, actor, role, action, target, detail) VALUES (?,?,?,?,?,?)",
                 (_now(), actor, role, action, target, (detail or "")[:500] or None))


def mine(conn: sqlite3.Connection, account: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, role, status, org, licence, requested_at, decided_at FROM role_grants WHERE device = ? ORDER BY id DESC", (account,))]


def request(conn: sqlite3.Connection, account: str, role: str, org: str, licence: str, auto: bool = False) -> dict:
    if role not in REQUESTABLE:
        raise ValueError("This role can't be requested")
    open_ = conn.execute("SELECT id, status FROM role_grants WHERE device = ? AND role = ? AND status IN ('pending','active')",
                         (account, role)).fetchone()
    if open_:
        return {"id": open_[0], "status": open_[1]}
    status = "active" if auto else "pending"
    cur = conn.execute("INSERT INTO role_grants (device, role, status, org, licence, requested_at, decided_at, decided_by) VALUES (?,?,?,?,?,?,?,?)",
                       (account, role, status, org, licence, _now(), _now() if auto else None, "demo-auto" if auto else None))
    audit(conn, account, "role.request", role, f"{org} / {licence}" + (" (auto-approved: demo mode)" if auto else ""))
    conn.commit()
    return {"id": cur.lastrowid, "status": status}


def grant(conn: sqlite3.Connection, account: str, role: str, by: str, org: str | None = None) -> int:
    """Direct grant by an admin (the only way to make another admin)."""
    cur = conn.execute("INSERT INTO role_grants (device, role, status, org, requested_at, decided_at, decided_by) VALUES (?,?,'active',?,?,?,?)",
                       (account, role, org, _now(), _now(), by))
    audit(conn, by, "role.grant", role, account, ADMIN)
    conn.commit()
    return cur.lastrowid


def decide(conn: sqlite3.Connection, gid: int, decision: str, by: str) -> dict | None:
    """approve a pending request, reject it, or revoke an active role."""
    want = {"approve": ("pending", "active"), "reject": ("pending", "rejected"), "revoke": ("active", "revoked")}[decision]
    row = conn.execute("SELECT device, role, status FROM role_grants WHERE id = ?", (gid,)).fetchone()
    if not row or row[2] != want[0]:
        return None
    if row[0] == by and decision == "approve":
        raise PermissionError("You can't approve your own request")
    conn.execute("UPDATE role_grants SET status = ?, decided_at = ?, decided_by = ? WHERE id = ?", (want[1], _now(), by, gid))
    audit(conn, by, f"role.{decision}", row[1], row[0], role=ADMIN)
    conn.commit()
    return {"id": gid, "role": row[1], "status": want[1]}


def queue(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT g.id, g.role, g.status, g.org, g.licence, g.requested_at, g.decided_at, g.decided_by, u.phone
           FROM role_grants g LEFT JOIN users u ON u.device = g.device
           WHERE g.status IN ('pending','active') ORDER BY g.status = 'active', g.id DESC""")]


def log(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]
