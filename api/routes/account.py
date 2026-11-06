"""Account: phone login (one-time code), plan, billing (Stripe Checkout)."""
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

import auth
import entitlements
import roles
import sessions

from core import _phone, conn, current_account, demo_mode, now, on_startup, optional_account, principal, rate_limit, require, session_token, signed_in_account

router = APIRouter()


# ---- billing (Stripe Checkout) ----
class CheckoutIn(BaseModel):
    plan: str


def _active_plan(dev: str) -> dict | None:
    return entitlements.active_plan(conn, dev)


# ---- phone login (one-time code on WhatsApp) ----

class OtpStart(BaseModel):
    phone: str


class OtpVerify(BaseModel):
    phone: str
    code: str


def _secure(request: Request) -> bool:
    import os

    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https" or os.environ.get("COOKIE_SECURE") == "1"


def _give_session(request: Request, response: Response, account: str, kind: str) -> None:
    """New session in an HttpOnly cookie: page scripts can't read it, other sites can't send it on a POST (SameSite=Lax)."""
    token = sessions.create(conn, account, kind, request.headers.get("user-agent"))
    response.set_cookie(sessions.COOKIE, token, max_age=int(sessions.LIFETIME[kind].total_seconds()), httponly=True,
                        secure=_secure(request), samesite="lax", path="/")


def _info(s: dict | None) -> dict:
    p = auth.phone_of(conn, s["account"]) if s else None
    return {"session": bool(s), "signed_in": bool(s) and s["kind"] == "user", "masked": f"{p[:3]} ••••• {p[-4:]}" if p else None}


@router.post("/api/session")
def session_start(request: Request, response: Response):
    """Every visitor gets a private, server-made account on first visit. Nothing about it comes from the browser."""
    s = sessions.resolve(conn, session_token(request))
    if s:
        return _info(s)
    rate_limit(request, "session", 30, 60)
    account = sessions.new_account_id()
    _give_session(request, response, account, "guest")
    entitlements.seen(conn, account)
    return {"session": True, "signed_in": False, "masked": None}


@router.get("/api/session")
def session_get(request: Request):
    return _info(sessions.resolve(conn, session_token(request)))


@router.post("/api/auth/start")
def auth_start(b: OtpStart, request: Request, account: str = Depends(current_account)):
    import notify

    rate_limit(request, "otp-start", 5, 600)
    phone = _phone(b.phone)
    if not phone:
        raise HTTPException(400, "Enter your mobile number")
    if not notify.whatsapp_ready() and not demo_mode():
        # Showing the code on screen would let anyone sign in as any phone number and read their medical data.
        raise HTTPException(503, "Phone sign-in needs WhatsApp set up on this server (docs/setup/WHATSAPP_SETUP.md).")
    try:
        code = auth.start(conn, phone)
    except auth.AuthError as e:
        raise HTTPException(429, str(e))
    if notify.whatsapp_ready():
        status, _ = notify.send_whatsapp(phone, auth.otp_text(code))
        if status not in ("sent",):
            raise HTTPException(502, "Couldn't send the code on WhatsApp. Check the number and try again.")
        return {"sent": True, "channel": "whatsapp"}
    return {"sent": False, "channel": "demo", "demo_code": code}  # KINCARE_DEMO=1 only (a laptop running run.bat)


@router.post("/api/auth/verify")
def auth_verify(b: OtpVerify, request: Request, response: Response, account: str = Depends(current_account)):
    """Right code: the guest's data moves into the phone's account, and the guest session is replaced by a signed-in one."""
    rate_limit(request, "otp-verify", 10, 600)
    phone = _phone(b.phone)
    try:
        auth.verify(conn, phone, b.code)
    except auth.AuthError as e:
        raise HTTPException(401, str(e))
    r = auth.login(conn, phone, account)
    entitlements.seen(conn, r["device"])
    sessions.revoke(conn, session_token(request))  # the old guest token stops working (no session fixation)
    _give_session(request, response, r["device"], "user")
    return {"signed_in": True, "new": r["new"], "merged": r["merged"], "masked": f"{phone[:3]} ••••• {phone[-4:]}"}


@router.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    if tok := session_token(request):
        sessions.revoke(conn, tok)
    response.delete_cookie(sessions.COOKIE, path="/")
    return {"ok": True}


@router.get("/api/auth/sessions")
def auth_sessions(request: Request, account: str = Depends(current_account)):
    """Every browser / phone signed in to this account, so a lost phone can be signed out."""
    return sessions.active(conn, account, session_token(request))


@router.delete("/api/auth/sessions/{sid}")
def auth_session_end(sid: str, account: str = Depends(current_account)):
    if not sessions.revoke_id(conn, account, sid):
        raise HTTPException(404, "Session not found")
    return {"ok": True}


@router.post("/api/auth/logout-others")
def auth_logout_others(request: Request, account: str = Depends(current_account)):
    return {"ended": sessions.revoke_all(conn, account, except_token=session_token(request))}


@router.get("/api/auth/me")
def auth_me(request: Request, account: str = Depends(current_account)):
    p = auth.phone_of(conn, account)
    held = principal(request)["roles"]
    return {"phone": p, "masked": f"{p[:3]} ••••• {p[-4:]}" if p else None,
            "roles": sorted(held), "permissions": roles.permissions(held)}


# ---- roles: request one (pharmacist, regulator), an admin approves ----

class RoleIn(BaseModel):
    role: str
    org: str
    licence: str


@router.get("/api/roles/mine")
def roles_mine(account: str = Depends(current_account)):
    return roles.mine(conn, account)


@router.post("/api/roles/request")
def roles_request(b: RoleIn, request: Request, account: str = Depends(signed_in_account)):
    """Ask for a professional role. Needs a verified phone; an admin checks the licence and approves.
    On the laptop demo (KINCARE_DEMO=1) it is approved at once so the stage flow works."""
    rate_limit(request, "role", 10, 3600)
    org, licence = b.org.strip()[:120], b.licence.strip()[:60]
    if b.role not in roles.REQUESTABLE:
        raise HTTPException(400, "You can ask for the pharmacist or regulator role.")
    if len(org) < 2 or len(licence) < 3:
        raise HTTPException(400, "Give your pharmacy / office name and your licence or employee number.")
    return roles.request(conn, account, b.role, org, licence, auto=demo_mode())


class GrantIn(BaseModel):
    phone: str
    role: str


@router.get("/api/admin/roles")
def admin_roles(_: dict = Depends(require("roles.decide"))):
    out = roles.queue(conn)
    for r in out:
        r["phone"] = f"{r['phone'][:3]} ••••• {r['phone'][-4:]}" if r.get("phone") else None
    return out


@router.post("/api/admin/roles/{gid}/{decision}")
def admin_role_decide(gid: int, decision: str, who: dict = Depends(require("roles.decide"))):
    if decision not in ("approve", "reject", "revoke"):
        raise HTTPException(400, "approve, reject or revoke")
    try:
        r = roles.decide(conn, gid, decision, who["actor"])
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not r:
        raise HTTPException(409, "That request is not in a state you can do this to")
    return r


@router.post("/api/admin/roles/grant")
def admin_role_grant(b: GrantIn, who: dict = Depends(require("roles.decide"))):
    """Give a role to a signed-up phone directly (the only way to make another admin)."""
    if b.role not in (roles.PHARMACIST, roles.REGULATOR, roles.ADMIN):
        raise HTTPException(400, "Unknown role")
    acct = conn.execute("SELECT device FROM users WHERE phone = ?", (_phone(b.phone),)).fetchone()
    if not acct:
        raise HTTPException(404, "No one has signed in with that phone yet")
    if b.role in roles.of(conn, acct[0]):
        return {"ok": True, "already": True}
    roles.grant(conn, acct[0], b.role, who["actor"])
    return {"ok": True}


@router.get("/api/admin/audit")
def admin_audit(limit: int = 100, _: dict = Depends(require("audit.view"))):
    """Account ids never leave the server, even to admins: each one is shown as that person's masked phone."""
    def who(v: str | None) -> str | None:
        if not v or not v.startswith("acct_"):
            return v
        p = auth.phone_of(conn, v)
        return f"{p[:3]} ••••• {p[-4:]}" if p else "guest"

    out = roles.log(conn, min(max(limit, 1), 500))
    for a in out:
        a["actor"], a["target"] = who(a["actor"]), who(a["target"])
    return out


@router.get("/api/account/entitlement")
def account_entitlement(account: str = Depends(current_account)):
    """Plan, trial days left and limits for this device. Scans and recall alerts are free whatever this says."""
    return entitlements.of(conn, account)


@router.get("/api/billing/plans")
def billing_plans(account: str | None = Depends(optional_account)):
    import billing

    return {"ready": billing.ready(), "test_mode": billing.test_mode(), "currency": billing.CURRENCY,
            "plans": [{"id": k, **v} for k, v in billing.PLANS.items()], "free": billing.FREE,
            "active": _active_plan(account) if account else None}


@router.post("/api/billing/checkout")
def billing_checkout(body: CheckoutIn, account: str = Depends(current_account)):
    import billing

    dev = account
    if body.plan not in billing.PLANS:
        raise HTTPException(400, "Unknown plan")
    if not billing.ready():
        raise HTTPException(503, "Payments are not set up yet. Add STRIPE_SECRET_KEY (a free sk_test_ key works).")
    try:
        sid, url = billing.create_session(body.plan, dev)
    except Exception as e:
        raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or e}")
    conn.execute("INSERT INTO payments (device, plan, session_id, amount, currency) VALUES (?, ?, ?, ?, ?)",
                 (dev, body.plan, sid, billing.PLANS[body.plan]["amount"], billing.CURRENCY))
    conn.commit()
    return {"url": url}


def _mark_paid(session_id: str, email: str | None):
    conn.execute("UPDATE payments SET status = 'paid', paid_at = COALESCE(paid_at, ?), email = COALESCE(?, email) WHERE session_id = ?",
                 (now(), email, session_id))
    conn.commit()


@router.get("/api/billing/confirm")
def billing_confirm(session_id: str, account: str = Depends(current_account)):
    """Called by the success page. We ask Stripe directly; the URL alone proves nothing."""
    import billing

    dev = account
    row = conn.execute("SELECT device FROM payments WHERE session_id = ?", (session_id,)).fetchone()
    if not row or row[0] != dev:
        raise HTTPException(404, "Payment not found for this device")
    s = billing.fetch_session(session_id)
    if s["paid"]:
        _mark_paid(session_id, s["email"])
    return {"paid": s["paid"], "active": _active_plan(dev)}


@router.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    import billing

    try:
        ev = billing.parse_webhook(await request.body(), request.headers.get("stripe-signature", ""))
    except Exception:
        raise HTTPException(400, "Bad signature")
    if ev["type"] == "checkout.session.completed" and ev["data"]["object"].get("payment_status") in ("paid", "no_payment_required"):
        o = ev["data"]["object"]
        _mark_paid(o["id"], (o.get("customer_details") or {}).get("email"))
    return {"ok": True}


# ---- your data (DPDP Act 2023: right to access and right to erasure) ----

@router.get("/api/account/export")
def account_export(account: str = Depends(current_account)):
    """Everything KinCare holds about you, as one JSON file."""
    import privacy

    return {"generated_at": now(), "data": privacy.export(conn, account)}


@router.delete("/api/account")
def account_erase(account: str = Depends(current_account)):
    """Delete everything about you: prescriptions, doses, vitals, chats, caregiver links (both sides), login."""
    import privacy

    return {"deleted": privacy.erase(conn, account), "sessions_ended": sessions.revoke_all(conn, account)}


@on_startup
def _encrypt_old_rows():
    """Chats, doctor messages and diagnoses written before encryption existed get encrypted once (vault.py)."""
    import vault

    if n := vault.migrate(conn):
        print(f"vault: encrypted {n} older values")


@on_startup
def _retention_loop():
    """Once a day: drop raw data past its retention period (privacy.RETENTION)."""
    import privacy

    def loop():
        while True:
            try:
                privacy.purge_old(conn)
            except Exception as e:
                print("retention:", e)
            time.sleep(24 * 3600)

    threading.Thread(target=loop, daemon=True).start()
