"""Caregivers with consent: invites, links, dashboard, nudges, alerts to caregivers."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import caregiver as caregiver_mod
import push
import telegram
import vault

from core import conn, current_account, on_startup, rate_limit, signed_in_account

router = APIRouter()

conn.executescript(caregiver_mod.SCHEMA)
conn.executescript(telegram.SCHEMA)
conn.execute("""CREATE TABLE IF NOT EXISTS dadi_chat (
    id INTEGER PRIMARY KEY, device TEXT NOT NULL, member TEXT NOT NULL DEFAULT 'Me', role TEXT NOT NULL, text TEXT NOT NULL,
    kind TEXT, data TEXT, channel TEXT DEFAULT 'app', at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_dadi_device ON dadi_chat(device, id)")
WEB = __import__("os").environ.get("PUBLIC_WEB_URL", "http://localhost:3000").rstrip("/")


def _who(link: dict) -> str:
    return link["elder_name"] or link["member"]


def tell_caregivers(dev: str, member: str, scope: str | None, title: str, text: str, tag: str) -> list[str]:
    """Push + Telegram to every caregiver the elder allowed for this scope (None = any live link). Logged for the elder."""
    told = []
    for r in conn.execute("SELECT * FROM care_links WHERE elder_device = ? AND member = ? AND revoked_at IS NULL", (dev, member)).fetchall():
        l = caregiver_mod._link_row(r)
        if scope and scope not in l["scopes"]:
            continue
        push.send(conn, l["caregiver_device"], title, text, f"/family?link={l['id']}", f"{tag}-{l['id']}")
        telegram.send_device(conn, l["caregiver_device"], f"{title}\n{text}\n\n{WEB}/family?link={l['id']}")
        caregiver_mod.log(conn, l["id"], "alerted", title)
        told.append(l["caregiver_name"])
    conn.commit()
    return told


def send_caregiver_alerts() -> int:
    """Doses still not ticked an hour after their time: tell the caregivers who may see doses."""
    n = 0
    for l, d in caregiver_mod.missed_doses(conn):
        title = f"{_who(l)} hasn't taken {d['name']}"
        text = f"The {d['time']} {d['slot']} dose isn't ticked yet. A gentle call may help. You can send a reminder from KinCare."
        push.send(conn, l["caregiver_device"], title, text, f"/family?link={l['id']}", f"missed-{d['med_id']}-{d['slot']}")
        telegram.send_device(conn, l["caregiver_device"], f"⏰ {title}\n{text}\n\n{WEB}/family?link={l['id']}")
        caregiver_mod.log(conn, l["id"], "alerted", title)
        n += 1
    conn.commit()
    return n


@on_startup
def _caregiver_loop():
    import threading
    import time

    def loop():
        while True:
            try:
                send_caregiver_alerts()
            except Exception as e:
                print("caregiver loop:", e)
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()


class InviteIn(BaseModel):
    member: str = "Me"
    elder_name: str | None = None
    scopes: list[str] = ["doses", "vitals", "sos"]


class AcceptIn(BaseModel):
    code: str
    name: str
    relation: str | None = None


def _consent(fn, *a):
    try:
        return fn(*a)
    except caregiver_mod.ConsentError as e:
        raise HTTPException(400, str(e))


@router.get("/api/caregiver/scopes")
def caregiver_scopes():
    return [{"key": k, "label": v} for k, v in caregiver_mod.SCOPES.items()]


@router.post("/api/caregiver/invite")
def caregiver_invite(b: InviteIn, account: str = Depends(signed_in_account)):
    """The elder (or whoever holds their phone, with them) chooses exactly what to share."""
    r = _consent(caregiver_mod.invite, conn, account, b.member.strip()[:20] or "Me", b.elder_name, b.scopes)
    return {**r, "url": f"{WEB}/family?code={r['code']}"}


@router.get("/api/caregiver/invite/{code}")
def caregiver_invite_preview(code: str, request: Request):
    rate_limit(request, "invite", 20, 600)  # 6-letter codes: guessing one takes ~10^9 tries
    return _consent(caregiver_mod.preview, conn, code)


@router.post("/api/caregiver/accept")
def caregiver_accept(b: AcceptIn, request: Request, account: str = Depends(signed_in_account)):
    rate_limit(request, "invite", 20, 600)
    dev = account
    r = _consent(caregiver_mod.accept, conn, b.code, dev, b.name, b.relation)
    l = caregiver_mod.get_link(conn, r["link_id"], dev)
    msg = f"{l['caregiver_name']} ({l['relation'] or 'family'}) can now see: " + ", ".join(l["scopes"]) + ". You can stop this anytime in KinCare > Family."
    push.send(conn, l["elder_device"], "Someone is looking after you", msg, "/family", f"linked-{l['id']}")
    telegram.send_device(conn, l["elder_device"], "🤝 " + msg, role="self")
    return r


@router.get("/api/caregiver/links")
def caregiver_links(account: str = Depends(current_account)):
    return caregiver_mod.links(conn, account)


@router.delete("/api/caregiver/links/{lid}")
def caregiver_revoke(lid: int, account: str = Depends(current_account)):
    return _consent(caregiver_mod.revoke, conn, lid, account)


@router.get("/api/caregiver/access")
def caregiver_access(account: str = Depends(current_account)):
    """The elder's view: every time a caregiver looked, nudged or was alerted."""
    return caregiver_mod.access_log(conn, account)


@router.get("/api/caregiver/elder/{lid}")
def caregiver_elder(lid: int, account: str = Depends(current_account)):
    l = _consent(caregiver_mod.get_link, conn, lid, account)
    # One "viewed" row per 10 minutes, so the elder's log stays readable while the page refreshes.
    last = conn.execute("SELECT MAX(at) FROM care_access WHERE link_id = ? AND action = 'viewed'", (lid,)).fetchone()[0]
    if not last or datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(minutes=10):
        caregiver_mod.log(conn, lid, "viewed", ", ".join(l["scopes"]))
        conn.commit()
    return caregiver_mod.dashboard(conn, l)


class NudgeIn(BaseModel):
    text: str | None = None


@router.post("/api/caregiver/elder/{lid}/nudge")
def caregiver_nudge(lid: int, b: NudgeIn, account: str = Depends(current_account)):
    """A caregiver's reminder reaches the elder as a phone notification, on Telegram and in the Dadi chat."""
    l = _consent(caregiver_mod.get_link, conn, lid, account)
    recent = conn.execute("SELECT COUNT(*) FROM care_access WHERE link_id = ? AND action = 'nudged' AND at > ?",
                          (lid, (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())).fetchone()[0]
    if recent >= 5:
        raise HTTPException(429, "That's 5 reminders this hour. Try calling instead.")
    text = (b.text or "").strip()[:200] or "Please take your medicine and tick it in KinCare."
    say = f"{l['caregiver_name']}: {text}"
    pushed = push.send(conn, l["elder_device"], f"Message from {l['caregiver_name']}", text, "/dadi", f"nudge-{lid}")
    tg = telegram.send_device(conn, l["elder_device"], f"💬 {say}", role="self", buttons=TG_BUTTONS)
    conn.execute("INSERT INTO dadi_chat (device, member, role, text, kind, channel) VALUES (?,?,?,?,?,?)",
                 (l["elder_device"], l["member"], "family", vault.seal(say, "dadi_chat", "text"), "nudge", "app"))
    caregiver_mod.log(conn, lid, "nudged", text)
    conn.commit()
    return {"phone": pushed, "telegram": tg, "in_app": True}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.telegram_bot import TG_BUTTONS  # noqa: E402
