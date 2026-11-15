"""Care circle API: passcode-shared elder profile, medicines, adherence, appointments, email reminders.

Two kinds of caller reach /api/circle/p/{code}/...:
- the elder (owner), with their normal KinCare session;
- a family member or caretaker, with the X-Circle-Token they got from /api/circle/unlock (passcode).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import circle
import gemini
import mailer
import sessions
from core import conn, current_account, on_startup, rate_limit, session_token

router = APIRouter()
conn.executescript(circle.SCHEMA)
conn.executescript(mailer.SCHEMA)


def _err(fn, *a, **k):
    try:
        return fn(*a, **k)
    except circle.CircleError as e:
        raise HTTPException(e.status, str(e))


def _owned(code: str, account: str) -> dict:
    prof = _err(circle.profile, conn, code)
    if prof["owner_device"] != account:
        raise HTTPException(404, "No care profile with that ID.")
    return prof


def actor(code: str, request: Request) -> tuple[dict, dict | None]:
    """(profile, circle member). member is None when the elder themself is calling."""
    prof = _err(circle.profile, conn, code)
    m = circle.member_for(conn, prof["code"], request.headers.get("x-circle-token"))
    if m:
        return prof, m
    s = sessions.resolve(conn, session_token(request))
    if s and s["account"] == prof["owner_device"]:
        return prof, None
    raise HTTPException(401, "Unlock this care profile with its passcode first.")


def _public(prof: dict) -> dict:
    return {k: prof[k] for k in ("code", "member", "elder_name", "elder_email", "approve_changes", "created_at")}


# ---------- the elder: create, settings, members, approvals ----------

class ProfileIn(BaseModel):
    member: str = "Me"
    elder_name: str
    elder_email: str | None = None
    passcode: str
    approve_changes: bool = True


class ProfileUpdate(BaseModel):
    elder_name: str | None = None
    elder_email: str | None = None
    approve_changes: bool | None = None
    passcode: str | None = None
    sign_out_all: bool = False


@router.post("/api/circle/profiles")
def circle_create(b: ProfileIn, account: str = Depends(current_account)):
    return _public(_err(circle.create_profile, conn, account, b.member.strip()[:20] or "Me", b.elder_name, b.elder_email, b.passcode, b.approve_changes))


@router.get("/api/circle/profiles")
def circle_mine(account: str = Depends(current_account)):
    out = []
    for r in conn.execute("SELECT * FROM circle_profiles WHERE owner_device = ? ORDER BY id", (account,)).fetchall():
        p = dict(r)
        out.append({**_public(p), "members": circle.members(conn, p["id"]), "pending": circle.pending_changes(conn, p["id"]),
                    "activity": circle.activity(conn, p["id"], 20)})
    return out


@router.put("/api/circle/profiles/{code}")
def circle_update(code: str, b: ProfileUpdate, account: str = Depends(current_account)):
    prof = _owned(code, account)
    return _public(_err(circle.update_profile, conn, prof, b.elder_name, b.elder_email, b.approve_changes, b.passcode, b.sign_out_all))


class MemberUpdate(BaseModel):
    can_edit: bool


@router.put("/api/circle/profiles/{code}/members/{mid}")
def circle_member_update(code: str, mid: int, b: MemberUpdate, account: str = Depends(current_account)):
    prof = _owned(code, account)
    if not conn.execute("UPDATE circle_members SET can_edit = ? WHERE id = ? AND profile_id = ? AND revoked_at IS NULL", (int(b.can_edit), mid, prof["id"])).rowcount:
        raise HTTPException(404, "Member not found")
    circle.log(conn, prof["id"], prof["elder_name"], "permission", f"member {mid}: {'can edit' if b.can_edit else 'view only'}")
    conn.commit()
    return {"ok": True}


@router.delete("/api/circle/profiles/{code}/members/{mid}")
def circle_member_remove(code: str, mid: int, account: str = Depends(current_account)):
    prof = _owned(code, account)
    r = conn.execute("SELECT name FROM circle_members WHERE id = ? AND profile_id = ? AND revoked_at IS NULL", (mid, prof["id"])).fetchone()
    if not r:
        raise HTTPException(404, "Member not found")
    conn.execute("UPDATE circle_members SET revoked_at = ? WHERE id = ?", (circle._utc(), mid))
    circle.log(conn, prof["id"], prof["elder_name"], "removed", r["name"])
    conn.commit()
    return {"ok": True}


class DecideIn(BaseModel):
    approve: bool


@router.post("/api/circle/profiles/{code}/changes/{cid}")
def circle_decide(code: str, cid: int, b: DecideIn, account: str = Depends(current_account)):
    return _err(circle.decide, conn, _owned(code, account), cid, b.approve)


# ---------- family / caretaker: unlock with the passcode ----------

class UnlockIn(BaseModel):
    code: str
    passcode: str
    name: str
    email: str | None = None
    role: str = "family"


@router.post("/api/circle/unlock")
def circle_unlock(b: UnlockIn, request: Request):
    rate_limit(request, "circle-unlock", 10, 600)  # on top of the per-profile lockout
    return _err(circle.unlock, conn, b.code, b.passcode, b.name, b.email, b.role)


@router.post("/api/circle/p/{code}/leave")
def circle_leave(code: str, request: Request):
    prof, m = actor(code, request)
    if m:
        conn.execute("UPDATE circle_members SET revoked_at = ? WHERE id = ?", (circle._utc(), m["id"]))
        circle.log(conn, prof["id"], m["name"], "left")
        conn.commit()
    return {"ok": True}


# ---------- shared profile: everyone in the circle ----------

@router.get("/api/circle/p/{code}")
def circle_view(code: str, request: Request):
    prof, m = actor(code, request)
    return {
        "profile": {k: prof[k] for k in ("code", "elder_name", "approve_changes")},
        "you": {"name": m["name"], "role": m["role"], "can_edit": bool(m["can_edit"])} if m else {"name": prof["elder_name"], "role": "elder", "can_edit": True},
        "medicines": circle.meds(conn, prof),
        "today": circle.today(conn, prof),
        "adherence": circle.adherence(conn, prof, 30),
        "appointments": [{**a, "gcal": circle.gcal_url(a, prof["elder_name"])} for a in circle.appointments(conn, prof["id"])],
        "pending": circle.pending_changes(conn, prof["id"]),
        "circle": [{"name": x["name"], "role": x["role"]} for x in circle.members(conn, prof["id"])],
        "activity": circle.activity(conn, prof["id"], 15),
    }


class MedIn(BaseModel):
    name: str | None = None
    strength: str | None = None
    food: str | None = None
    morning: bool | None = None
    noon: bool | None = None
    night: bool | None = None
    days: int | None = None
    as_needed: bool | None = None


@router.post("/api/circle/p/{code}/meds")
def circle_med_add(code: str, b: MedIn, request: Request):
    prof, m = actor(code, request)
    return _err(circle.change, conn, prof, m, "add_med", b.model_dump(exclude_none=True))


@router.put("/api/circle/p/{code}/meds/{med_id}")
def circle_med_edit(code: str, med_id: int, b: MedIn, request: Request):
    prof, m = actor(code, request)
    return _err(circle.change, conn, prof, m, "edit_med", {**b.model_dump(exclude_none=True), "med_id": med_id})


@router.delete("/api/circle/p/{code}/meds/{med_id}")
def circle_med_delete(code: str, med_id: int, request: Request):
    prof, m = actor(code, request)
    return _err(circle.change, conn, prof, m, "delete_med", {"med_id": med_id})


class TickIn(BaseModel):
    med_id: int
    slot: str
    taken: bool = True
    day: str | None = None


@router.post("/api/circle/p/{code}/doses")
def circle_tick(code: str, b: TickIn, request: Request):
    prof, m = actor(code, request)
    return _err(circle.mark, conn, prof, m, b.med_id, b.slot, b.taken, b.day)


@router.get("/api/circle/p/{code}/adherence")
def circle_adherence(code: str, request: Request, days: int = 30):
    prof, _ = actor(code, request)
    return circle.adherence(conn, prof, max(1, min(days, 90)))


class ApptIn(BaseModel):
    doctor: str | None = None
    specialty: str | None = None
    place: str | None = None
    at: str | None = None
    notes: str | None = None
    status: str | None = None


@router.get("/api/circle/p/{code}/appointments")
def circle_appts(code: str, request: Request, past: bool = False):
    prof, _ = actor(code, request)
    return circle.appointments(conn, prof["id"], include_past=past)


@router.post("/api/circle/p/{code}/appointments")
def circle_appt_add(code: str, b: ApptIn, request: Request):
    prof, m = actor(code, request)
    return _err(circle.save_appointment, conn, prof, m["name"] if m else prof["elder_name"], b.model_dump(exclude_none=True))


@router.put("/api/circle/p/{code}/appointments/{aid}")
def circle_appt_edit(code: str, aid: int, b: ApptIn, request: Request):
    prof, m = actor(code, request)
    return _err(circle.save_appointment, conn, prof, m["name"] if m else prof["elder_name"], b.model_dump(exclude_none=True), aid)


@router.delete("/api/circle/p/{code}/appointments/{aid}")
def circle_appt_delete(code: str, aid: int, request: Request):
    prof, m = actor(code, request)
    return _err(circle.delete_appointment, conn, prof, m["name"] if m else prof["elder_name"], aid)


@router.get("/api/circle/p/{code}/summary")
def circle_summary(code: str, request: Request):
    """One page to show the doctor: medicines, timings, adherence, next appointment."""
    prof, _ = actor(code, request)
    a = circle.adherence(conn, prof, 30)
    lines = [f"{prof['elder_name']}: medicines and adherence (KinCare)", ""]
    for med in circle.meds(conn, prof):
        t = "only when needed" if med["as_needed"] else ", ".join(s for s in ("morning", "noon", "night") if med[s])
        lines.append(f"- {med['name']} {med['strength'] or ''} | {t}{' | ' + med['food'] if med['food'] else ''}".replace("  ", " "))
    lines += ["", f"Doses taken: {a['pct_7'] if a['pct_7'] is not None else '-'}% last 7 days, {a['pct_30'] if a['pct_30'] is not None else '-'}% last 30 days"]
    for med in a["medicines"]:
        if med["pct"] is not None and med["pct"] < 80:
            lines.append(f"  Often missed: {med['name']} ({med['pct']}%)")
    nxt = circle.appointments(conn, prof["id"])
    if nxt:
        lines += ["", f"Next appointment: {nxt[0]['doctor']}, {nxt[0]['at'].replace('T', ' ')}"]
    return {"text": "\n".join(lines)}


@router.get("/api/circle/p/{code}/note")
def circle_note(code: str, request: Request, lang: str = "en"):
    """Gemini's plain-language weekly note for the elder (rules-based without a key)."""
    prof, _ = actor(code, request)
    rate_limit(request, "gemini", 20, 600)
    return gemini.care_note(prof["elder_name"], circle.adherence(conn, prof, 30), circle.appointments(conn, prof["id"]), "hi" if lang == "hi" else "en")


@router.get("/api/circle/email/status")
def email_status():
    return {"email": mailer.provider(), "gemini": gemini.ready()}


@on_startup
def _circle_reminder_loop():
    import threading
    import time

    def loop():
        while True:
            try:
                circle.run_reminders(conn)
            except Exception as e:  # keep the loop alive; next minute retries
                print("circle reminders:", e)
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()
