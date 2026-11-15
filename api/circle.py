"""Care circle: one elder's health profile, shared by passcode with family and caretakers.

- The elder (the account that owns the profile) sets a profile ID + passcode and decides who stays in.
- A family member or caretaker unlocks the profile with ID + passcode and their name and email. Each person gets
  their own session token (stored hashed), so the elder sees who did what and can remove one person without
  changing the passcode for everyone.
- Elder at the centre: with "ask me first" on, medicine changes made by others wait for the elder's approval;
  either way the elder is emailed about every change, and about failed passcode attempts.
- Email reminders: an upcoming dose (to the elder and caretakers), a missed dose (to the whole circle) and
  doctor appointments (24 h and 2 h before, to the whole circle).

Medicines live in the same plans / plan_meds / doses tables as the rest of Carely, so the app's Care page,
Dadi mode, WhatsApp / Telegram reminders and recall checks all see the same schedule.
"""
import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone

import care
import mailer

SCHEMA = """
CREATE TABLE IF NOT EXISTS circle_profiles (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,              -- profile ID people type, e.g. KC-7HQ2PX
    owner_device TEXT NOT NULL,             -- the elder's account
    member TEXT NOT NULL DEFAULT 'Me',      -- which person on that account (same as plans.member)
    elder_name TEXT NOT NULL,
    elder_email TEXT,
    pass_salt TEXT NOT NULL,
    pass_hash TEXT NOT NULL,
    approve_changes INTEGER NOT NULL DEFAULT 1,
    failed INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (owner_device, member)
);
CREATE TABLE IF NOT EXISTS circle_members (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES circle_profiles(id),
    name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL,                     -- family | caretaker
    can_edit INTEGER NOT NULL DEFAULT 1,
    token_hash TEXT NOT NULL UNIQUE,
    joined_at TEXT NOT NULL,
    last_seen TEXT,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS circle_changes (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL,
    member_id INTEGER,
    action TEXT NOT NULL,                   -- add_med | edit_med | delete_med
    payload TEXT NOT NULL,
    status TEXT NOT NULL,                   -- pending | applied | rejected
    at TEXT NOT NULL,
    decided_at TEXT
);
CREATE TABLE IF NOT EXISTS circle_activity (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL,
    who TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_circle_activity ON circle_activity(profile_id, id);
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL,
    doctor TEXT NOT NULL,
    specialty TEXT,
    place TEXT,
    at TEXT NOT NULL,                       -- local time, YYYY-MM-DDTHH:MM
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'upcoming',-- upcoming | done | cancelled
    created_by TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_appt_profile ON appointments(profile_id, at);
CREATE TABLE IF NOT EXISTS circle_sent (
    profile_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (profile_id, key)
);
"""

ROLES = ("family", "caretaker")
MAX_FAILS = 5
LOCK = timedelta(minutes=15)
SESSION = timedelta(days=90)
UPCOMING_BEFORE = timedelta(minutes=15)   # "your dose is in 15 minutes"
MISSED_AFTER = timedelta(minutes=60)      # untaken an hour after its time
STALE = timedelta(hours=6)                # never email about a dose this old (e.g. server was down)
MED_FIELDS = ("name", "strength", "food", "morning", "noon", "night", "days", "as_needed")


class CircleError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- passcodes and sessions ----------

def check_passcode(p: str) -> str:
    p = (p or "").strip()
    if not 6 <= len(p) <= 32:
        raise CircleError("The passcode needs 6 to 32 characters.")
    if len(set(p)) <= 2 or p in "01234567890" or p in "9876543210" or p.lower() in ("password", "passcode", "kincare"):
        raise CircleError("That passcode is too easy to guess. Avoid repeated or sequential digits.")
    return p


def _hash(p: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 200_000).hex()


def _token_hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _new_code(conn) -> str:
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L: read aloud over the phone
    while True:
        code = "KC-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if not conn.execute("SELECT 1 FROM circle_profiles WHERE code = ?", (code,)).fetchone():
            return code


def log(conn, pid: int, who: str, action: str, detail: str | None = None) -> None:
    conn.execute("INSERT INTO circle_activity (profile_id, who, action, detail, at) VALUES (?,?,?,?,?)", (pid, who, action, (detail or "")[:300], _utc()))


def create_profile(conn, owner: str, member: str, elder_name: str, elder_email: str | None, passcode: str, approve_changes: bool) -> dict:
    p = check_passcode(passcode)
    if elder_email and not mailer.valid(elder_email):
        raise CircleError("That email address doesn't look right.")
    if conn.execute("SELECT 1 FROM circle_profiles WHERE owner_device = ? AND member = ?", (owner, member)).fetchone():
        raise CircleError(f"{member} already has a care profile. Change its passcode instead.", 409)
    salt = secrets.token_hex(16)
    code = _new_code(conn)
    cur = conn.execute("""INSERT INTO circle_profiles (code, owner_device, member, elder_name, elder_email, pass_salt, pass_hash, approve_changes, created_at)
                          VALUES (?,?,?,?,?,?,?,?,?)""",
                       (code, owner, member, elder_name.strip()[:60], (elder_email or "").strip() or None, salt, _hash(p, salt), int(approve_changes), _utc()))
    log(conn, cur.lastrowid, elder_name, "created", "Care profile created")
    conn.commit()
    return profile(conn, code)


def profile(conn, code: str) -> dict:
    r = conn.execute("SELECT * FROM circle_profiles WHERE code = ?", ((code or "").strip().upper(),)).fetchone()
    if not r:
        raise CircleError("No care profile with that ID.", 404)
    return dict(r)


def update_profile(conn, prof: dict, elder_name=None, elder_email=None, approve_changes=None, passcode=None, sign_out_all=False) -> dict:
    if elder_email and not mailer.valid(elder_email):
        raise CircleError("That email address doesn't look right.")
    sets = {}
    if elder_name:
        sets["elder_name"] = elder_name.strip()[:60]
    if elder_email is not None:
        sets["elder_email"] = elder_email.strip() or None
    if approve_changes is not None:
        sets["approve_changes"] = int(approve_changes)
    if passcode:
        salt = secrets.token_hex(16)
        sets.update(pass_salt=salt, pass_hash=_hash(check_passcode(passcode), salt), failed=0, locked_until=None)
    if sets:
        conn.execute(f"UPDATE circle_profiles SET {', '.join(k + ' = ?' for k in sets)} WHERE id = ?", (*sets.values(), prof["id"]))
    if sign_out_all:
        conn.execute("UPDATE circle_members SET revoked_at = ? WHERE profile_id = ? AND revoked_at IS NULL", (_utc(), prof["id"]))
    log(conn, prof["id"], prof["elder_name"], "settings", ", ".join(k for k in sets if not k.startswith("pass_")) + (" passcode changed" if passcode else "")
        + (", everyone signed out" if sign_out_all else ""))
    conn.commit()
    return profile(conn, prof["code"])


def unlock(conn, code: str, passcode: str, name: str, email: str | None, role: str) -> dict:
    """Passcode -> a personal session token for this circle member. Lockout after MAX_FAILS wrong tries."""
    prof = profile(conn, code)
    now = datetime.now(timezone.utc)
    if prof["locked_until"] and datetime.fromisoformat(prof["locked_until"]) > now:
        raise CircleError("Too many wrong passcodes. This profile is locked for 15 minutes.", 429)
    if not hmac.compare_digest(prof["pass_hash"], _hash((passcode or "").strip(), prof["pass_salt"])):
        fails = prof["failed"] + 1
        locked = (now + LOCK).isoformat() if fails >= MAX_FAILS else None
        conn.execute("UPDATE circle_profiles SET failed = ?, locked_until = ? WHERE id = ?", (0 if locked else fails, locked, prof["id"]))
        log(conn, prof["id"], (name or "someone").strip()[:40], "wrong_passcode", "locked for 15 min" if locked else f"attempt {fails}")
        if locked and prof["elder_email"]:
            mailer.send(conn, prof["elder_email"], "Carely: wrong passcode entered 5 times",
                        f"Someone ({(name or 'unknown').strip()[:40]}) entered a wrong passcode for your care profile {prof['code']} 5 times.\n"
                        "The profile is locked for 15 minutes. If this wasn't someone you know, change your passcode in Carely > Care circle.", "security")
        conn.commit()
        left = MAX_FAILS - fails
        raise CircleError("Wrong passcode. Locked for 15 minutes." if locked else f"Wrong passcode. {left} {'try' if left == 1 else 'tries'} left.", 401)
    name = (name or "").strip()[:40]
    if not name:
        raise CircleError("Tell the elder who you are: add your name.")
    if role not in ROLES:
        raise CircleError("Choose family or caretaker.")
    if email and not mailer.valid(email):
        raise CircleError("That email address doesn't look right.")
    token = secrets.token_urlsafe(32)
    conn.execute("UPDATE circle_profiles SET failed = 0, locked_until = NULL WHERE id = ?", (prof["id"],))
    cur = conn.execute("""INSERT INTO circle_members (profile_id, name, email, role, can_edit, token_hash, joined_at, last_seen, expires_at)
                          VALUES (?,?,?,?,?,?,?,?,?)""",
                       (prof["id"], name, (email or "").strip() or None, role, 1, _token_hash(token), _utc(), _utc(), (now + SESSION).isoformat()))
    log(conn, prof["id"], name, "joined", role)
    if prof["elder_email"]:
        mailer.send(conn, prof["elder_email"], f"Carely: {name} opened your care profile",
                    f"{name} ({role}) unlocked your care profile with your passcode.\n"
                    "They can now see your medicines, doses and appointments. You can remove them anytime in Carely > Care circle.", "security")
    conn.commit()
    return {"token": token, "member_id": cur.lastrowid, "profile": prof["code"]}


def member_for(conn, code: str, token: str | None) -> dict | None:
    if not token:
        return None
    r = conn.execute("""SELECT m.* FROM circle_members m JOIN circle_profiles p ON p.id = m.profile_id
                        WHERE m.token_hash = ? AND p.code = ? AND m.revoked_at IS NULL""", (_token_hash(token), (code or "").upper())).fetchone()
    if not r or datetime.fromisoformat(r["expires_at"]) < datetime.now(timezone.utc):
        return None
    conn.execute("UPDATE circle_members SET last_seen = ? WHERE id = ?", (_utc(), r["id"]))
    return dict(r)


def members(conn, pid: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, name, email, role, can_edit, joined_at, last_seen FROM circle_members WHERE profile_id = ? AND revoked_at IS NULL ORDER BY id", (pid,))]


# ---------- medicines ----------

def meds(conn, prof: dict) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT m.id, m.name, m.strength, m.food, m.morning, m.noon, m.night, m.days, m.as_needed, m.batch, p.start_date, p.doctor
           FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE p.device = ? AND p.member = ? ORDER BY m.id""",
        (prof["owner_device"], prof["member"]))]


def _med_payload(d: dict, partial: bool = False) -> dict:
    out = {k: d[k] for k in MED_FIELDS if k in d and d[k] is not None}
    if not partial and not (out.get("name") or "").strip():
        raise CircleError("Add the medicine's name.")
    for k in ("morning", "noon", "night"):
        if k in out:
            out[k] = 1 if out[k] else 0
    if "as_needed" in out:
        out["as_needed"] = int(bool(out["as_needed"]))
    if out.get("days") is not None and not 0 < int(out["days"]) <= 3650:
        raise CircleError("Days should be between 1 and 3650 (or empty for ongoing).")
    if not partial and not out.get("as_needed") and not any(out.get(k) for k in ("morning", "noon", "night")):
        raise CircleError("Pick at least one time (morning, noon, night) or mark it 'only when needed'.")
    for k in ("name", "strength", "food"):
        if k in out:
            out[k] = str(out[k]).strip()[:80]
    return out


def _own_med(conn, prof: dict, med_id: int) -> dict:
    r = conn.execute("SELECT m.* FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE m.id = ? AND p.device = ? AND p.member = ?",
                     (med_id, prof["owner_device"], prof["member"])).fetchone()
    if not r:
        raise CircleError("Medicine not found on this profile.", 404)
    return dict(r)


def _apply(conn, prof: dict, action: str, payload: dict) -> dict:
    if action == "add_med":
        plan = conn.execute("SELECT id FROM plans WHERE device = ? AND member = ? AND doctor = 'Care circle'", (prof["owner_device"], prof["member"])).fetchone()
        pid = plan[0] if plan else conn.execute("INSERT INTO plans (device, member, doctor, start_date, advice) VALUES (?,?,?,?,?)",
                                                (prof["owner_device"], prof["member"], "Care circle", date.today().isoformat(), "[]")).lastrowid
        m = {"strength": "", "food": "", "morning": 0, "noon": 0, "night": 0, "days": None, "as_needed": 0, **payload}
        cur = conn.execute("INSERT INTO plan_meds (plan_id, name, strength, food, morning, noon, night, days, as_needed) VALUES (?,?,?,?,?,?,?,?,?)",
                           (pid, *(m[k] for k in MED_FIELDS)))
        return {"med_id": cur.lastrowid}
    if action == "edit_med":
        _own_med(conn, prof, payload["med_id"])
        sets = {k: v for k, v in payload.items() if k in MED_FIELDS}
        if sets:
            conn.execute(f"UPDATE plan_meds SET {', '.join(k + ' = ?' for k in sets)} WHERE id = ?", (*sets.values(), payload["med_id"]))
        return {"med_id": payload["med_id"]}
    if action == "delete_med":
        _own_med(conn, prof, payload["med_id"])
        for t in ("doses", "reminders_sent"):
            conn.execute(f"DELETE FROM {t} WHERE med_id = ?", (payload["med_id"],))
        conn.execute("DELETE FROM plan_meds WHERE id = ?", (payload["med_id"],))
        return {"med_id": payload["med_id"]}
    raise CircleError("Unknown change.")


def _describe(action: str, payload: dict, old: dict | None = None) -> str:
    def times(m):
        t = [s for s in ("morning", "noon", "night") if m.get(s)]
        return "only when needed" if m.get("as_needed") else ", ".join(t) or "no times"
    name = payload.get("name") or (old or {}).get("name") or "a medicine"
    if action == "add_med":
        return f"Add {name} {payload.get('strength') or ''}".strip() + f" ({times(payload)})"
    if action == "delete_med":
        return f"Stop {name}"
    diff = [f"{k}: {old.get(k)!s} -> {v!s}" for k, v in payload.items() if k in MED_FIELDS and old and old.get(k) != v]
    return f"Change {name}: " + ("; ".join(diff) or "no change")


def change(conn, prof: dict, who: dict | None, action: str, payload: dict) -> dict:
    """who = circle member, or None for the elder. Others' changes wait for the elder when approve_changes is on."""
    if action == "add_med":
        payload = _med_payload(payload)
    elif action == "edit_med":
        payload = {**_med_payload(payload, partial=True), "med_id": int(payload["med_id"])}
    else:
        payload = {"med_id": int(payload["med_id"])}
    old = _own_med(conn, prof, payload["med_id"]) if "med_id" in payload else None
    desc = _describe(action, payload, old)
    name = who["name"] if who else prof["elder_name"]
    if who and not who["can_edit"]:
        raise CircleError(f"{prof['elder_name']} has given you view-only access.", 403)
    pending = bool(who) and bool(prof["approve_changes"])
    cur = conn.execute("INSERT INTO circle_changes (profile_id, member_id, action, payload, status, at, decided_at) VALUES (?,?,?,?,?,?,?)",
                       (prof["id"], who["id"] if who else None, action, json.dumps(payload), "pending" if pending else "applied", _utc(), None if pending else _utc()))
    result = {} if pending else _apply(conn, prof, action, payload)
    log(conn, prof["id"], name, "proposed" if pending else "changed", desc)
    if who and prof["elder_email"]:
        mailer.send(conn, prof["elder_email"],
                    f"Carely: {name} {'asks to change' if pending else 'changed'} your medicines",
                    f"{name} ({who['role']}): {desc}.\n"
                    + ("Nothing changes until you approve it in Carely > Care circle." if pending
                       else "If this is not right, open Carely > Care circle to undo it or remove their edit access."), "change")
    conn.commit()
    return {"change_id": cur.lastrowid, "status": "pending" if pending else "applied", "summary": desc, **result}


def decide(conn, prof: dict, change_id: int, approve: bool) -> dict:
    r = conn.execute("SELECT * FROM circle_changes WHERE id = ? AND profile_id = ? AND status = 'pending'", (change_id, prof["id"])).fetchone()
    if not r:
        raise CircleError("No pending change with that ID.", 404)
    payload = json.loads(r["payload"])
    result = _apply(conn, prof, r["action"], payload) if approve else {}
    conn.execute("UPDATE circle_changes SET status = ?, decided_at = ? WHERE id = ?", ("applied" if approve else "rejected", _utc(), change_id))
    desc = _describe(r["action"], payload)
    log(conn, prof["id"], prof["elder_name"], "approved" if approve else "declined", desc)
    m = conn.execute("SELECT name, email FROM circle_members WHERE id = ?", (r["member_id"],)).fetchone()
    if m and m["email"]:
        mailer.send(conn, m["email"], f"Carely: {prof['elder_name']} {'approved' if approve else 'declined'} your change",
                    f"{desc}: {'approved and now in the schedule' if approve else 'declined. Please talk to them about it'}.", "change")
    conn.commit()
    return {"status": "applied" if approve else "rejected", **result}


def pending_changes(conn, pid: int) -> list[dict]:
    out = []
    for r in conn.execute("""SELECT c.*, m.name AS member_name FROM circle_changes c LEFT JOIN circle_members m ON m.id = c.member_id
                             WHERE c.profile_id = ? AND c.status = 'pending' ORDER BY c.id""", (pid,)):
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        d["summary"] = _describe(d["action"], d["payload"])
        out.append(d)
    return out


def activity(conn, pid: int, limit: int = 40) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT who, action, detail, at FROM circle_activity WHERE profile_id = ? ORDER BY id DESC LIMIT ?", (pid, limit))]


# ---------- doses and adherence ----------

def _taken(conn, med_id: int, day: str, slot: str) -> str | None:
    r = conn.execute("SELECT taken_at FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (med_id, day, slot)).fetchone()
    return r[0] if r else None


def today(conn, prof: dict, at: datetime | None = None) -> list[dict]:
    at = at or datetime.now()
    hm, out = at.strftime("%H:%M"), []
    for m in meds(conn, prof):
        for d in care.doses_for(m, m["start_date"], at.date()):
            taken = _taken(conn, m["id"], at.date().isoformat(), d["slot"])
            due = datetime.combine(at.date(), datetime.strptime(d["time"], "%H:%M").time())
            state = "taken" if taken else "missed" if at >= due + MISSED_AFTER else "due" if at >= due else "upcoming"
            out.append({**d, "med_id": m["id"], "name": m["name"], "strength": m["strength"], "food": m["food"], "taken_at": taken, "state": state})
    return sorted(out, key=lambda x: (x["time"], x["name"]))


def mark(conn, prof: dict, who: dict | None, med_id: int, slot: str, taken: bool, day: str | None = None) -> dict:
    _own_med(conn, prof, med_id)
    if slot not in ("morning", "noon", "night"):
        raise CircleError("Slot must be morning, noon or night.")
    day = day or date.today().isoformat()
    if taken:
        conn.execute("INSERT INTO doses (med_id, day, slot, taken_at) VALUES (?,?,?,?) ON CONFLICT(med_id, day, slot) DO UPDATE SET taken_at = excluded.taken_at",
                     (med_id, day, slot, _utc()))
    else:
        conn.execute("DELETE FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (med_id, day, slot))
    if who:
        log(conn, prof["id"], who["name"], "ticked" if taken else "unticked", f"med {med_id} {day} {slot}")
    conn.commit()
    return {"ok": True}


def adherence(conn, prof: dict, days: int = 30, at: datetime | None = None) -> dict:
    """Share of scheduled doses ticked, per day and per medicine. Today's doses count only once their time has passed."""
    at = at or datetime.now()
    ms = meds(conn, prof)
    per_day, per_med = [], {m["id"]: {"med_id": m["id"], "name": m["name"], "due": 0, "taken": 0} for m in ms}
    for i in range(days - 1, -1, -1):
        d = at.date() - timedelta(days=i)
        due = taken = 0
        for m in ms:
            for dose in care.doses_for(m, m["start_date"], d):
                if d == at.date() and dose["time"] > at.strftime("%H:%M"):
                    continue
                ok = bool(_taken(conn, m["id"], d.isoformat(), dose["slot"]))
                due, taken = due + 1, taken + ok
                per_med[m["id"]]["due"] += 1
                per_med[m["id"]]["taken"] += ok
        per_day.append({"day": d.isoformat(), "due": due, "taken": taken, "pct": round(100 * taken / due) if due else None})

    def pct(rows):
        due = sum(r["due"] for r in rows)
        return round(100 * sum(r["taken"] for r in rows) / due) if due else None

    streak = 0
    for r in reversed(per_day):
        if r["due"] == 0:
            continue
        if r["taken"] < r["due"]:
            if r["day"] == at.date().isoformat():  # today isn't over: don't break the streak yet
                continue
            break
        streak += 1
    meds_out = [{**v, "pct": round(100 * v["taken"] / v["due"]) if v["due"] else None} for v in per_med.values()]
    return {"pct_7": pct(per_day[-7:]), "pct_30": pct(per_day), "streak_days": streak, "days": per_day,
            "medicines": sorted(meds_out, key=lambda v: (v["pct"] is None, v["pct"] or 0))}


# ---------- appointments ----------

def _appt_at(s: str) -> str:
    try:
        return datetime.fromisoformat(s.strip()).strftime("%Y-%m-%dT%H:%M")
    except (ValueError, AttributeError):
        raise CircleError("Give the appointment date and time as YYYY-MM-DDTHH:MM.")


def gcal_url(a: dict, elder: str) -> str:
    """One-tap "Add to Google Calendar" link (no API key, no OAuth: the user's own calendar adds it)."""
    from urllib.parse import urlencode

    start = datetime.fromisoformat(a["at"])
    fmt = "%Y%m%dT%H%M%S"
    return "https://calendar.google.com/calendar/render?" + urlencode({
        "action": "TEMPLATE", "text": f"{elder}: {a['doctor']}" + (f" ({a['specialty']})" if a.get("specialty") else ""),
        "dates": f"{start.strftime(fmt)}/{(start + timedelta(hours=1)).strftime(fmt)}", "ctz": "Asia/Kolkata",
        "location": a.get("place") or "", "details": (a.get("notes") or "") + " Bring the Carely medicine list."})


def appointments(conn, pid: int, include_past: bool = False) -> list[dict]:
    q = "SELECT * FROM appointments WHERE profile_id = ?" + ("" if include_past else " AND status = 'upcoming' AND at >= ?") + " ORDER BY at"
    args = (pid,) if include_past else (pid, (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"))
    return [dict(r) for r in conn.execute(q, args)]


def save_appointment(conn, prof: dict, who_name: str, data: dict, appt_id: int | None = None) -> dict:
    fields = {k: (str(data[k]).strip()[:200] if data.get(k) is not None else None) for k in ("doctor", "specialty", "place", "notes", "status") if k in data}
    if "at" in data and data["at"]:
        fields["at"] = _appt_at(data["at"])
    if fields.get("status") and fields["status"] not in ("upcoming", "done", "cancelled"):
        raise CircleError("Status must be upcoming, done or cancelled.")
    if appt_id is None:
        if not fields.get("doctor") or not fields.get("at"):
            raise CircleError("Add the doctor's name and the date and time.")
        cur = conn.execute("INSERT INTO appointments (profile_id, doctor, specialty, place, at, notes, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
                           (prof["id"], fields["doctor"], fields.get("specialty"), fields.get("place"), fields["at"], fields.get("notes"), who_name, _utc()))
        appt_id = cur.lastrowid
        log(conn, prof["id"], who_name, "appointment", f"{fields['doctor']} on {fields['at'].replace('T', ' ')}")
    else:
        if not conn.execute("SELECT 1 FROM appointments WHERE id = ? AND profile_id = ?", (appt_id, prof["id"])).fetchone():
            raise CircleError("Appointment not found.", 404)
        if fields:
            conn.execute(f"UPDATE appointments SET {', '.join(k + ' = ?' for k in fields)} WHERE id = ?", (*fields.values(), appt_id))
        if "at" in fields:  # moved: remind again for the new time
            conn.execute("DELETE FROM circle_sent WHERE profile_id = ? AND key LIKE ?", (prof["id"], f"appt%:{appt_id}"))
        log(conn, prof["id"], who_name, "appointment", f"updated #{appt_id}: " + ", ".join(fields))
    conn.commit()
    return dict(conn.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone())


def delete_appointment(conn, prof: dict, who_name: str, appt_id: int) -> dict:
    if not conn.execute("DELETE FROM appointments WHERE id = ? AND profile_id = ?", (appt_id, prof["id"])).rowcount:
        raise CircleError("Appointment not found.", 404)
    log(conn, prof["id"], who_name, "appointment", f"removed #{appt_id}")
    conn.commit()
    return {"ok": True}


# ---------- email reminders ----------

def _once(conn, pid: int, key: str) -> bool:
    try:
        conn.execute("INSERT INTO circle_sent (profile_id, key, at) VALUES (?,?,?)", (pid, key, _utc()))
        return True
    except sqlite3.IntegrityError:
        return False


def _recipients(conn, prof: dict, who: str) -> list[str]:
    """who: 'elder' | 'carers' (elder + caretakers) | 'all'."""
    out = [prof["elder_email"]] if prof["elder_email"] else []
    for m in members(conn, prof["id"]):
        if m["email"] and (who == "all" or (who == "carers" and m["role"] == "caretaker")):
            out.append(m["email"])
    return list(dict.fromkeys(out))


def run_reminders(conn, at: datetime | None = None) -> int:
    """Called every minute. Each reminder goes out once (circle_sent), and never for something hours stale."""
    at = at or datetime.now()
    sent = 0
    for prof in [dict(r) for r in conn.execute("SELECT * FROM circle_profiles")]:
        who = prof["elder_name"]
        for d in today(conn, prof, at):
            due = datetime.combine(at.date(), datetime.strptime(d["time"], "%H:%M").time())
            what = f"{d['name']} {d['strength'] or ''}".strip() + (f" ({d['food']})" if d["food"] else "")
            key = f"{at.date().isoformat()}:{d['med_id']}:{d['slot']}"
            if d["state"] == "upcoming" and due - UPCOMING_BEFORE <= at and _once(conn, prof["id"], "upcoming:" + key):
                for to in _recipients(conn, prof, "carers"):
                    sent += mailer.send(conn, to, f"Carely: {who}'s {d['time']} dose, {d['name']}",
                                        f"In 15 minutes, at {d['time']}, it is time for {who} to take {what}.\n"
                                        "Tick it in Carely once taken, so the family knows.", "dose_upcoming") in ("sent", "outbox")
            elif d["state"] == "missed" and at < due + STALE and _once(conn, prof["id"], "missed:" + key):
                for to in _recipients(conn, prof, "all"):
                    sent += mailer.send(conn, to, f"Carely: {who} hasn't taken {d['name']} yet",
                                        f"The {d['time']} dose of {what} is not ticked an hour later.\n"
                                        f"A gentle call to {who} may help. If it was taken, tick it in Carely > Care circle.\n"
                                        "Never give a double dose to catch up unless the doctor has said so.", "dose_missed") in ("sent", "outbox")
        for a in appointments(conn, prof["id"]):
            when = datetime.fromisoformat(a["at"])
            for label, before, key in (("tomorrow", timedelta(hours=24), "appt24"), ("in 2 hours", timedelta(hours=2), "appt2")):
                # The 24 h notice only before the 2 h window opens; a just-added appointment gets the nearer one only.
                if when - before <= at < when and not (key == "appt24" and at >= when - timedelta(hours=2)) and _once(conn, prof["id"], f"{key}:{a['id']}"):
                    text = (f"{who} has a doctor's appointment {label}: {when.strftime('%a %d %b, %I:%M %p')}\n"
                            f"Doctor: {a['doctor']}" + (f" ({a['specialty']})" if a["specialty"] else "") + "\n"
                            + (f"Where: {a['place']}\n" if a["place"] else "") + (f"Notes: {a['notes']}\n" if a["notes"] else "")
                            + "Bring the medicine list (Carely > Care circle > Print for doctor) and any recent BP/sugar readings.")
                    for to in _recipients(conn, prof, "all"):
                        sent += mailer.send(conn, to, f"Carely: {who}'s appointment {label} with {a['doctor']}", text, "appointment") in ("sent", "outbox")
    conn.commit()
    return sent
