"""Caregivers: a son in Bengaluru sees whether Papa in Patna took his BP tablet, with Papa's say-so.

Consent rules this module never breaks:
- Nothing is shared until the elder makes an invite and picks exactly what it covers (doses, vitals, SOS).
- A caregiver sees only those scopes, only for that one family member.
- Every time a caregiver opens the elder's data it is written to an access log the elder can read.
- Either side can end the link at any time; ending it is immediate and logged. Data stays with the elder.
- Caregivers can see and nudge. They can never add, change or delete a medicine, dose or reading.
"""
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone

import care
import vault

SCOPES = {
    "doses": "Medicines and whether each dose was taken",
    "vitals": "BP, pulse, oxygen and temperature readings",
    "sos": "Emergency alerts with location",
}
INVITE_TTL = timedelta(hours=48)
MISSED_AFTER = timedelta(minutes=60)  # a dose not ticked this long after its time tells the caregiver

SCHEMA = """
CREATE TABLE IF NOT EXISTS care_invites (
    code TEXT PRIMARY KEY,
    elder_device TEXT NOT NULL,
    member TEXT NOT NULL DEFAULT 'Me',
    elder_name TEXT,
    scopes TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE TABLE IF NOT EXISTS care_links (
    id INTEGER PRIMARY KEY,
    elder_device TEXT NOT NULL,
    member TEXT NOT NULL DEFAULT 'Me',
    elder_name TEXT,
    caregiver_device TEXT NOT NULL,
    caregiver_name TEXT NOT NULL,
    relation TEXT,
    scopes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    revoked_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_links_elder ON care_links(elder_device);
CREATE INDEX IF NOT EXISTS idx_links_cg ON care_links(caregiver_device);
CREATE TABLE IF NOT EXISTS care_access (
    id INTEGER PRIMARY KEY,
    link_id INTEGER NOT NULL,
    action TEXT NOT NULL,        -- viewed / nudged / linked / revoked / alerted
    detail TEXT,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_alerts_sent (
    link_id INTEGER NOT NULL,
    key TEXT NOT NULL,           -- missed-<med>-<day>-<slot>, vitals-<id>
    at TEXT NOT NULL,
    PRIMARY KEY (link_id, key)
);
"""


class ConsentError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(conn: sqlite3.Connection, link_id: int, action: str, detail: str | None = None) -> None:
    conn.execute("INSERT INTO care_access (link_id, action, detail, at) VALUES (?,?,?,?)", (link_id, action, detail, _now()))


def invite(conn: sqlite3.Connection, elder_device: str, member: str, elder_name: str | None, scopes: list[str]) -> dict:
    scopes = [s for s in dict.fromkeys(scopes) if s in SCOPES]
    if not scopes:
        raise ConsentError("Choose at least one thing to share")
    # Short, unambiguous, easy to read out on a phone call: no 0/O, 1/I.
    code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    expires = datetime.now(timezone.utc) + INVITE_TTL
    conn.execute("INSERT INTO care_invites (code, elder_device, member, elder_name, scopes, expires_at) VALUES (?,?,?,?,?,?)",
                 (code, elder_device, member, (elder_name or "").strip()[:40] or None, json.dumps(scopes), expires.isoformat()))
    conn.commit()
    return {"code": code, "expires_at": expires.isoformat(), "scopes": scopes}


def preview(conn: sqlite3.Connection, code: str) -> dict:
    """What a caregiver is about to accept, shown before they press Accept."""
    r = conn.execute("SELECT * FROM care_invites WHERE code = ?", (code.strip().upper(),)).fetchone()
    if not r or r["used_at"] or datetime.fromisoformat(r["expires_at"]) < datetime.now(timezone.utc):
        raise ConsentError("This code is wrong, used or expired. Ask for a new one.")
    return {"code": r["code"], "elder_name": r["elder_name"] or r["member"], "member": r["member"],
            "scopes": [{"key": s, "label": SCOPES[s]} for s in json.loads(r["scopes"])], "expires_at": r["expires_at"]}


def accept(conn: sqlite3.Connection, code: str, caregiver_device: str, name: str, relation: str | None) -> dict:
    p = preview(conn, code)
    r = conn.execute("SELECT * FROM care_invites WHERE code = ?", (p["code"],)).fetchone()
    if r["elder_device"] == caregiver_device:
        raise ConsentError("Open this code on the caregiver's phone, not the elder's")
    name = name.strip()[:40]
    if not name:
        raise ConsentError("Enter your name so they know who is looking after them")
    conn.execute("UPDATE care_invites SET used_at = ? WHERE code = ?", (_now(), r["code"]))
    # One live link per caregiver per elder: accepting again replaces the scopes.
    conn.execute("UPDATE care_links SET revoked_at = ?, revoked_by = 'replaced' WHERE elder_device = ? AND member = ? AND caregiver_device = ? AND revoked_at IS NULL",
                 (_now(), r["elder_device"], r["member"], caregiver_device))
    cur = conn.execute("INSERT INTO care_links (elder_device, member, elder_name, caregiver_device, caregiver_name, relation, scopes, created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (r["elder_device"], r["member"], r["elder_name"], caregiver_device, name, (relation or "").strip()[:20] or None, r["scopes"], _now()))
    log(conn, cur.lastrowid, "linked", f"{name} can see: " + ", ".join(json.loads(r["scopes"])))
    conn.commit()
    return {"link_id": cur.lastrowid, "elder_name": p["elder_name"]}


def _link_row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["scopes"] = json.loads(d["scopes"])
    return d


def links(conn: sqlite3.Connection, device: str) -> dict:
    """Both sides of one device: who looks after me, and whom I look after."""
    mine = [_link_row(r) for r in conn.execute("SELECT * FROM care_links WHERE elder_device = ? AND revoked_at IS NULL ORDER BY id DESC", (device,))]
    for l in mine:
        l["last_seen"] = (conn.execute("SELECT MAX(at) FROM care_access WHERE link_id = ? AND action = 'viewed'", (l["id"],)).fetchone() or [None])[0]
    watching = [_link_row(r) for r in conn.execute("SELECT * FROM care_links WHERE caregiver_device = ? AND revoked_at IS NULL ORDER BY id DESC", (device,))]
    return {"caregivers": mine, "watching": watching}


def get_link(conn: sqlite3.Connection, link_id: int, device: str, side: str = "caregiver") -> dict:
    col = "caregiver_device" if side == "caregiver" else "elder_device"
    r = conn.execute(f"SELECT * FROM care_links WHERE id = ? AND {col} = ? AND revoked_at IS NULL", (link_id, device)).fetchone()
    if not r:
        raise ConsentError("This link has ended or isn't yours")
    return _link_row(r)


def revoke(conn: sqlite3.Connection, link_id: int, device: str) -> dict:
    r = conn.execute("SELECT * FROM care_links WHERE id = ? AND (elder_device = ? OR caregiver_device = ?) AND revoked_at IS NULL", (link_id, device, device)).fetchone()
    if not r:
        raise ConsentError("This link has already ended")
    by = "elder" if r["elder_device"] == device else "caregiver"
    conn.execute("UPDATE care_links SET revoked_at = ?, revoked_by = ? WHERE id = ?", (_now(), by, link_id))
    log(conn, link_id, "revoked", f"ended by the {by}")
    conn.commit()
    return {"ok": True, "by": by}


def access_log(conn: sqlite3.Connection, elder_device: str, limit: int = 40) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT a.action, a.detail, a.at, l.caregiver_name, l.relation FROM care_access a JOIN care_links l ON l.id = a.link_id
           WHERE l.elder_device = ? ORDER BY a.id DESC LIMIT ?""", (elder_device, limit))]


# ---- what a caregiver sees ----

def _meds(conn, device: str, member: str) -> list[dict]:
    return [vault.open_row("plans", dict(r)) for r in conn.execute(
        "SELECT m.*, p.start_date, p.doctor, p.diagnosis FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ? AND p.member = ?", (device, member))]


def _taken(conn, med_id: int, day: str, slot: str) -> str | None:
    r = conn.execute("SELECT taken_at FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (med_id, day, slot)).fetchone()
    return r[0] if r else None


def doses_on(conn, meds: list[dict], on: date, now_hm: str | None) -> list[dict]:
    out = []
    for m in meds:
        for d in care.doses_for(m, m["start_date"], on):
            t = _taken(conn, m["id"], on.isoformat(), d["slot"])
            state = "taken" if t else ("due" if now_hm is None or d["time"] > now_hm else "missed")
            out.append({**d, "med_id": m["id"], "name": m["name"], "strength": m["strength"], "food": m["food"], "taken_at": t, "state": state})
    return sorted(out, key=lambda x: x["time"])


def dashboard(conn: sqlite3.Connection, link: dict, days: int = 7) -> dict:
    """Only what the elder agreed to share. Missing scopes come back as null, never as empty data."""
    dev, member, scopes = link["elder_device"], link["member"], link["scopes"]
    today = datetime.now().date()
    out = {"link": {k: link[k] for k in ("id", "member", "elder_name", "caregiver_name", "relation", "scopes", "created_at")},
           "doses": None, "vitals": None, "sos": None}
    if "doses" in scopes:
        meds = _meds(conn, dev, member)
        week = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            ds = doses_on(conn, meds, d, datetime.now().strftime("%H:%M") if i == 0 else "99:99")
            done = [x for x in ds if x["state"] != "due"]
            week.append({"day": d.isoformat(), "due": len(done), "taken": sum(x["state"] == "taken" for x in done),
                         "missed": [f"{x['name']} ({x['slot']})" for x in done if x["state"] == "missed"]})
        due = sum(w["due"] for w in week)
        taken = sum(w["taken"] for w in week)
        out["doses"] = {
            "today": doses_on(conn, meds, today, datetime.now().strftime("%H:%M")),
            "week": week,
            "adherence": round(100 * taken / due) if due else None,
            "medicines": [{"name": m["name"], "strength": m["strength"], "food": m["food"], "doctor": m["doctor"], "diagnosis": m["diagnosis"],
                           "schedule": "-".join(str(m[s] or 0) for s in ("morning", "noon", "night")), "as_needed": bool(m["as_needed"])} for m in meds],
        }
    if "vitals" in scopes:
        v = [dict(r) for r in conn.execute("SELECT id, at, temp_c, bp_sys, bp_dia, pulse, spo2, level, source FROM vitals WHERE device = ? AND member = ? ORDER BY at DESC LIMIT 30", (dev, member))]
        out["vitals"] = {"latest": v[0] if v else None, "history": v}
    if "sos" in scopes:
        s = conn.execute("SELECT at, lat, lng, resolved_at FROM sos_events WHERE device = ? AND (member = ? OR member IS NULL) ORDER BY id DESC LIMIT 1", (dev, member)).fetchone()
        out["sos"] = {"last": dict(s) if s else None}
    return out


# ---- alerts to caregivers ----

def live_links(conn, elder_device: str, member: str, scope: str) -> list[dict]:
    return [l for l in (_link_row(r) for r in conn.execute(
        "SELECT * FROM care_links WHERE elder_device = ? AND member = ? AND revoked_at IS NULL", (elder_device, member))) if scope in l["scopes"]]


def once(conn, link_id: int, key: str) -> bool:
    """True the first time a (link, key) alert is due; never sends the same alert twice."""
    try:
        conn.execute("INSERT INTO care_alerts_sent (link_id, key, at) VALUES (?,?,?)", (link_id, key, _now()))
        return True
    except sqlite3.IntegrityError:
        return False


def missed_doses(conn: sqlite3.Connection, at: datetime | None = None) -> list[tuple[dict, dict]]:
    """(link, dose) for every dose that is MISSED_AFTER overdue today and hasn't been told to that caregiver yet."""
    at = at or datetime.now()
    today = at.date()
    cut = at - MISSED_AFTER
    if cut.date() < today:  # just after midnight: nothing of the new day can be an hour late yet
        return []
    cutoff = cut.strftime("%H:%M")
    out = []
    pairs = conn.execute("SELECT DISTINCT elder_device, member FROM care_links WHERE revoked_at IS NULL").fetchall()
    for dev, member in pairs:
        ls = live_links(conn, dev, member, "doses")
        if not ls:
            continue
        for d in doses_on(conn, _meds(conn, dev, member), today, cutoff):
            if d["state"] != "missed":
                continue
            for l in ls:
                if once(conn, l["id"], f"missed-{d['med_id']}-{today.isoformat()}-{d['slot']}"):
                    out.append((l, d))
    conn.commit()
    return out
