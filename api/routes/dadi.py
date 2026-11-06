"""Dadi chat: one conversation, spoken or typed, in the app or on Telegram."""
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import vault

from core import _plans, conn, current_account, now, rows, run_check

router = APIRouter()


# ---- Dadi chat: one conversation, spoken or typed, in the app or on Telegram ----

def default_member(dev: str) -> str:
    """Who is talking on this device: the family member someone looks after, else 'Me'."""
    r = conn.execute("SELECT member FROM care_links WHERE elder_device = ? AND revoked_at IS NULL ORDER BY id DESC LIMIT 1", (dev,)).fetchone()
    return r[0] if r else "Me"


@router.get("/api/dadi/me")
def dadi_me(account: str = Depends(current_account)):
    dev = account
    members = [r[0] for r in conn.execute(
        "SELECT member FROM plans WHERE device = ? UNION SELECT member FROM care_links WHERE elder_device = ? AND revoked_at IS NULL", (dev, dev))]
    return {"member": default_member(dev), "members": sorted(set(members) | {"Me"}, key=lambda m: (m != "Me", m))}


class DadiIn(BaseModel):
    text: str
    lang: str = "hi"
    member: str = "Me"


def _mark_taken_device(dev: str, member: str | None, at: datetime | None = None) -> dict | None:
    """'Dawa le li': tick the latest dose that is due and not taken today (this member first)."""
    import care

    at = at or datetime.now()
    day = at.date()
    soon = at + timedelta(minutes=45)  # taking it a little early still counts
    hm = soon.strftime("%H:%M") if soon.date() == day else "23:59"
    due = []
    for p in _plans(dev):
        for m in p["medicines"]:
            for d in care.doses_for(m, p["start_date"], day):
                if d["time"] <= hm and not conn.execute("SELECT 1 FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (m["id"], day.isoformat(), d["slot"])).fetchone():
                    due.append((p["member"] == member, d["time"], {"med_id": m["id"], "slot": d["slot"], "name": m["name"], "member": p["member"], "time": d["time"]}))
    if not due:
        return None
    r = max(due, key=lambda x: (x[0], x[1]))[2]
    conn.execute("INSERT INTO doses (med_id, day, slot, taken_at) VALUES (?,?,?,?) ON CONFLICT(med_id, day, slot) DO UPDATE SET taken_at = excluded.taken_at",
                 (r["med_id"], day.isoformat(), r["slot"], now()))
    conn.commit()
    return r


def dadi_turn(dev: str, text: str, lang: str, member: str = "Me", channel: str = "app") -> dict:
    import voice

    text = text.strip()[:300]
    hi = lang != "en"
    conn.execute("INSERT INTO dadi_chat (device, member, role, text, channel) VALUES (?,?,?,?,?)", (dev, member, "me", vault.seal(text, "dadi_chat", "text"), channel))
    a = None
    v = voice.vitals_in(text)
    if voice._has(f"{text.lower()} {voice.translit(text.lower())}", *voice.EMERGENCY):
        pass  # emergencies always go to the 108 answer below, whatever else the sentence says
    elif voice.is_taken(text) or text.strip() in ("1", "✅"):  # WhatsApp habit: reply 1 after the dose
        r = _mark_taken_device(dev, member)
        say = ((f"बहुत अच्छे! {r['member']} की {r['name']} ({r['time']}) दर्ज कर ली।" if hi else f"Well done! {r['name']} ({r['time']}) for {r['member']} is ticked.")
               if r else ("अभी कोई दवा बाकी नहीं है। अगली बार याद दिला दूँगी।" if hi else "No dose is due right now. I'll remind you at the next one."))
        a = {"kind": "taken" if r else "nothing_due", "say": say, "show": say, "data": {"dose": r}}
    elif v:
        try:
            res = vitals_add(VitalsIn(member=member, source="voice", **v), dev)
            parts = [f"BP {v['bp_sys']}/{v['bp_dia']}" if "bp_sys" in v else "", f"pulse {v['pulse']}" if "pulse" in v else "",
                     f"oxygen {v['spo2']}%" if "spo2" in v else "", f"{v['temp_c']}°C" if "temp_c" in v else ""]
            got = ", ".join(p for p in parts if p)
            say = (f"नोट कर लिया: {got}। " if hi else f"Saved: {got}. ") + (res["hi"] if hi else res["en"])
            if told := res.get("told"):
                say += f" मैंने {', '.join(told)} को बता दिया है।" if hi else f" I've told {', '.join(told)}."
            kind = f"vitals_{res['level']}"
        except HTTPException as e:
            res, kind = None, "help"
            say = "यह रीडिंग सही नहीं लग रही। एक बार फिर से नापिए।" if hi else f"{e.detail}. Please measure again."
        a = {"kind": kind, "say": say, "show": say, "data": {"vitals": v, "assessment": res}}
    elif voice.is_family(text):
        who = conn.execute("SELECT elder_name FROM care_links WHERE elder_device = ? AND member = ? AND revoked_at IS NULL AND elder_name IS NOT NULL LIMIT 1",
                           (dev, member)).fetchone()
        name = who[0] if who else member
        told = tell_caregivers(dev, member, None, f"{name} wants to talk to you", f"“{text}”. Please give them a call.", "family")
        say = ((f"मैंने {', '.join(told)} को बता दिया है। वो जल्दी फ़ोन करेंगे।" if hi else f"I've told {', '.join(told)}. They'll call you soon.")
               if told else ("अभी कोई परिवार वाला जुड़ा नहीं है। 'परिवार' में जाकर बेटे या बेटी को जोड़िए।" if hi else "No family member is linked yet. Add one in Family."))
        a = {"kind": "family" if told else "family_none", "say": say, "show": say, "data": {"told": told}}
    if a is None:
        a = voice.answer(conn, text, "hi" if hi else "en", run_check, care_today(None, dev))
        if a["kind"] == "emergency":
            told = tell_caregivers(dev, member, "sos", f"🚨 {member} may need urgent help", f"They told KinCare: “{text}”. Call them now. If you can't reach them, call 108.", "sos-voice")
            if told:
                a["say"] += f" मैंने {', '.join(told)} को भी बता दिया है।" if hi else f" I've also alerted {', '.join(told)}."
                a["show"] = a["say"]
            a["data"] = {**a["data"], "told": told}
    conn.execute("INSERT INTO dadi_chat (device, member, role, text, kind, data, channel) VALUES (?,?,?,?,?,?,?)",
                 (dev, member, "kincare", vault.seal(a["show"], "dadi_chat", "text"), a["kind"],
                  vault.seal(json.dumps(a["data"], default=str), "dadi_chat", "data"), channel))
    conn.commit()
    return a


@router.post("/api/dadi/chat")
def dadi_chat(b: DadiIn, account: str = Depends(current_account)):
    if not b.text.strip():
        raise HTTPException(400, "Ask a question")
    return dadi_turn(account, b.text, "en" if b.lang == "en" else "hi", b.member.strip()[:20] or "Me")


@router.get("/api/dadi/history")
def dadi_history(limit: int = Query(60, le=200), account: str = Depends(current_account)):
    msgs = rows("SELECT id, member, role, text, kind, data, channel, at FROM dadi_chat WHERE device = ? ORDER BY id DESC LIMIT ?", (account, limit))
    for m in msgs:
        vault.open_row("dadi_chat", m)
        m["data"] = json.loads(m["data"]) if m["data"] else {}
    return msgs[::-1]


@router.delete("/api/dadi/history")
def dadi_clear(account: str = Depends(current_account)):
    conn.execute("DELETE FROM dadi_chat WHERE device = ?", (account,))
    conn.commit()
    return {"ok": True}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.care_plan import VitalsIn, care_today, vitals_add  # noqa: E402
from routes.family import tell_caregivers  # noqa: E402
