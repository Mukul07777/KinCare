"""Care: vitals, prescriptions, doses, reminders, refills, interactions, doctor report."""
import json
import threading
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

import entitlements
import telegram
from matcher import match
import vault

from core import _log_note, _phone, _plans, alert_device, candidates, conn, current_account, now, on_startup, rows, run_check

router = APIRouter()


# ---- care: vitals, prescriptions, dose reminders, report ----

class VitalsIn(BaseModel):
    member: str = "Me"
    temp_c: float | None = None
    bp_sys: int | None = None
    bp_dia: int | None = None
    pulse: int | None = None
    spo2: int | None = None
    source: str = "manual"  # later: "health_connect", "healthkit"
    note: str | None = None


@router.post("/api/care/vitals")
def vitals_add(v: VitalsIn, account: str = Depends(current_account)):
    import care

    dev = account
    for val, lo, hi_, label in ((v.temp_c, 30, 45, "Temperature"), (v.bp_sys, 50, 260, "BP"), (v.bp_dia, 30, 180, "BP"),
                                (v.pulse, 25, 250, "Pulse"), (v.spo2, 50, 100, "Oxygen")):
        if val is not None and not lo <= val <= hi_:
            raise HTTPException(400, f"{label} reading looks wrong")
    if all(x is None for x in (v.temp_c, v.bp_sys, v.pulse, v.spo2)):
        raise HTTPException(400, "Enter at least one reading")
    a = care.assess(v.temp_c, v.bp_sys, v.bp_dia, v.pulse, v.spo2)
    conn.execute(
        "INSERT INTO vitals (device, member, temp_c, bp_sys, bp_dia, pulse, spo2, source, level, note) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (dev, v.member, v.temp_c, v.bp_sys, v.bp_dia, v.pulse, v.spo2, v.source, a["level"], v.note),
    )
    conn.commit()
    if a["level"] == "urgent":  # caregivers allowed to see vitals hear about it at once
        a["told"] = tell_caregivers(dev, v.member, "vitals", f"⚠️ {v.member}: worrying reading", f"{', '.join(a['reasons'])}. {a['en']}", "vitals")
    return a


@router.get("/api/care/vitals")
def vitals_list(member: str | None = None, account: str = Depends(current_account)):
    dev = account
    if member:
        return rows("SELECT * FROM vitals WHERE device = ? AND member = ? ORDER BY at DESC LIMIT 60", (dev, member))
    return rows("SELECT * FROM vitals WHERE device = ? ORDER BY at DESC LIMIT 60", (dev,))


@router.post("/api/care/prescription/scan")
async def prescription_scan(image: UploadFile = File(...)):
    """OCR a doctor's prescription into medicines + advice for the patient to confirm."""
    import care
    import ocr

    data = await image.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 12 MB)")
    try:
        lines = ocr.read_lines(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    text = "\n".join(l["text"] for l in lines)
    return {**care.parse_prescription(text), "lines": [l["text"] for l in lines]}


class PlanMed(BaseModel):
    name: str
    strength: str = ""
    food: str = ""
    morning: int = 0
    noon: int = 0
    night: int = 0
    days: int | None = None
    as_needed: bool = False
    batch: str | None = None


class PlanIn(BaseModel):
    member: str = "Me"
    doctor: str | None = None
    diagnosis: str | None = None
    start_date: str | None = None
    advice: list[str] = []
    medicines: list[PlanMed]


@router.post("/api/care/plans")
def plan_add(p: PlanIn, account: str = Depends(current_account)):
    dev = account
    if not p.medicines:
        raise HTTPException(400, "Add at least one medicine from the prescription")
    ok, why = entitlements.can_add_member(conn, dev, p.member)
    if not ok:
        raise HTTPException(402, why)
    start = p.start_date or datetime.now().date().isoformat()
    cur = conn.execute("INSERT INTO plans (device, member, doctor, diagnosis, start_date, advice) VALUES (?,?,?,?,?,?)",
                       (dev, p.member, p.doctor, vault.seal(p.diagnosis, "plans", "diagnosis"), start, json.dumps(p.advice)))
    for m in p.medicines:
        conn.execute("INSERT INTO plan_meds (plan_id, name, strength, food, morning, noon, night, days, as_needed, batch) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (cur.lastrowid, m.name, m.strength, m.food, m.morning, m.noon, m.night, m.days, int(m.as_needed), m.batch))
    conn.commit()
    # Prescribed medicines with a batch number are watched for recalls too.
    flagged = [m.batch for m in p.medicines if m.batch and match(candidates(m.batch), m.batch, None, m.name)]
    return {"id": cur.lastrowid, "flagged_batches": flagged}


@router.get("/api/care/plans")
def plans_list(account: str = Depends(current_account)):
    return _plans(account)


@router.delete("/api/care/plans/{pid}")
def plan_delete(pid: int, account: str = Depends(current_account)):
    dev = account
    if not conn.execute("SELECT 1 FROM plans WHERE id = ? AND device = ?", (pid, dev)).fetchone():
        raise HTTPException(404, "Plan not found")
    conn.execute("DELETE FROM doses WHERE med_id IN (SELECT id FROM plan_meds WHERE plan_id = ?)", (pid,))
    conn.execute("DELETE FROM plan_meds WHERE plan_id = ?", (pid,))
    conn.execute("DELETE FROM plans WHERE id = ?", (pid,))
    conn.commit()
    return {"ok": True}


@router.get("/api/care/today")
def care_today(day: str | None = None, account: str = Depends(current_account)):
    import care

    dev = account
    on = datetime.fromisoformat(day).date() if day else datetime.now().date()
    out = []
    for p in _plans(dev):
        for m in p["medicines"]:
            for d in care.doses_for(m, p["start_date"], on):
                taken = conn.execute("SELECT taken_at FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (m["id"], on.isoformat(), d["slot"])).fetchone()
                out.append({**d, "med_id": m["id"], "name": m["name"], "strength": m["strength"], "food": m["food"],
                            "member": p["member"], "taken_at": taken["taken_at"] if taken else None})
    out.sort(key=lambda x: (x["time"], x["member"]))
    advice = sorted({a for p in _plans(dev) for a in p["advice"]})
    return {"day": on.isoformat(), "doses": out, "advice": advice}


class DoseIn(BaseModel):
    med_id: int
    slot: str
    day: str | None = None
    taken: bool = True


@router.post("/api/care/doses")
def dose_mark(d: DoseIn, account: str = Depends(current_account)):
    dev = account
    owner = conn.execute("SELECT 1 FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE m.id = ? AND p.device = ?", (d.med_id, dev)).fetchone()
    if not owner or d.slot not in ("morning", "noon", "night"):
        raise HTTPException(404, "Dose not found")
    day = d.day or datetime.now().date().isoformat()
    if d.taken:
        conn.execute("INSERT INTO doses (med_id, day, slot, taken_at) VALUES (?,?,?,?) ON CONFLICT(med_id, day, slot) DO UPDATE SET taken_at = excluded.taken_at",
                     (d.med_id, day, d.slot, now()))
    else:
        conn.execute("DELETE FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (d.med_id, day, d.slot))
    conn.commit()
    return {"ok": True}


class PurchaseIn(BaseModel):
    med_id: int
    batch: str
    maker: str | None = None
    expiry: str | None = None
    pharmacy: str | None = None
    phone: str | None = None
    language: str = "hi"
    qty: int | None = None  # tablets bought; empty = one pack of the matched brand


@router.post("/api/care/purchase")
def purchase(b: PurchaseIn, account: str = Depends(current_account)):
    """Patient bought a prescribed medicine: check the batch, then tell them when to take it."""
    import care
    import notify

    dev = account
    med = conn.execute("SELECT m.*, p.member, p.start_date FROM plan_meds m JOIN plans p ON p.id = m.plan_id WHERE m.id = ? AND p.device = ?",
                       (b.med_id, dev)).fetchone()
    if not med:
        raise HTTPException(404, "Medicine not found in your plans")
    phone = _phone(b.phone)
    lang = b.language if b.language in ("hi", "en") else "hi"
    if b.qty is not None and not 0 < b.qty <= 1000:
        raise HTTPException(400, "Tablets bought should be between 1 and 1000")
    # WhatsApp *reminders* need Basic+ (or a trial, or a paying pharmacy that covers this customer).
    # A recall alert on this purchase goes to the number whatever the plan: safety is never paywalled.
    wa_ok, sponsor = entitlements.whatsapp_reminders_ok(conn, dev, phone) if phone else (False, None)
    reminder_phone = phone if wa_ok else None
    whatsapp_state = f"sponsored:{sponsor}" if sponsor else "on" if wa_ok else "upgrade" if phone else "off"
    # A refill adds to what is still left from the last purchase.
    before = _refill(dict(med))
    qty = (b.qty or _pack_qty(med["name"], med["strength"]) or 0) + (before["left"] if before else 0)
    conn.execute("UPDATE plan_meds SET batch = ?, maker = ?, expiry = ?, pharmacy = ?, phone = ?, language = ?, bought_at = ?, qty = ?, refill_sent_at = NULL WHERE id = ?",
                 (b.batch.strip(), b.maker, b.expiry, b.pharmacy, reminder_phone, lang, now(), qty or None, b.med_id))
    med = {**dict(med), "batch": b.batch.strip()}
    check = run_check(b.batch, b.maker, med["name"])

    if check["matches"]:
        alert = check["matches"][0]["alert"]
        status = _log_note("whatsapp", med["member"], phone, lang, b.batch, notify.whatsapp_text(alert, b.batch, med["member"], lang), alert["id"])
        alert_device(dev, f"⛔ Don't take {med['name']}: batch {b.batch.strip()} is flagged",
                  f"{alert['product_name']}: {'spurious' if alert['category'] == 'spurious' else 'not of standard quality'} ({alert['alert_month']}). Speak to your pharmacist.",
                  "/care", f"recall-{b.med_id}")
        conn.commit()
        return {"verdict": "alert_found", "check": check, "due_now": False, "next_time": None, "message_status": status, "whatsapp": whatsapp_state}

    today = datetime.now()
    hm = today.strftime("%H:%M")
    doses = care.doses_for(med, med["start_date"], today.date())
    taken = {r["slot"] for r in conn.execute("SELECT slot FROM doses WHERE med_id = ? AND day = ?", (b.med_id, today.date().isoformat()))}
    pending = [d for d in doses if d["slot"] not in taken]
    due_now = any(d["time"] <= hm for d in pending)
    upcoming = [d["time"] for d in pending if d["time"] > hm]
    next_time = upcoming[0] if upcoming else None
    # The purchase message already says "take it now", so don't also send catch-up reminders for past slots.
    for d in pending:
        if d["time"] <= hm:
            conn.execute("INSERT OR IGNORE INTO reminders_sent (med_id, day, slot, sent_at) VALUES (?,?,?,?)", (b.med_id, today.date().isoformat(), d["slot"], now()))
    status = _log_note("whatsapp", med["member"], reminder_phone, lang, b.batch, notify.purchase_text(med, med["member"], due_now, next_time, lang))
    telegram.send_device(conn, dev, notify.purchase_text(med, med["member"], due_now, next_time, lang), role="self", buttons=TG_BUTTONS)
    conn.commit()
    return {"verdict": "no_alert_found", "check": check, "due_now": due_now, "next_time": next_time, "message_status": status, "whatsapp": whatsapp_state}


def _pack_qty(name: str, strength: str | None) -> float | None:
    """Tablets in one pack of the brand this prescription line most likely means (Indian Medicine Dataset)."""
    import prices

    r, _ = prices.match_plan_med(conn, name, strength)
    return r["qty"] if r and r["unit"] == "tablet" else None


def _refill(m: dict) -> dict | None:
    """Tablets left from the last purchase: bought minus doses ticked since."""
    import care

    if not m.get("qty") or not m.get("bought_at"):
        return None
    taken = conn.execute("SELECT COUNT(*) FROM doses WHERE med_id = ? AND taken_at > ?", (m["id"], m["bought_at"])).fetchone()[0]
    return care.refill_status(m, m["start_date"], m["qty"], taken, datetime.now().date())


def _cheaper_clean(m: dict) -> str | None:
    """'Telmisoft 40 Tablet, ₹0.65 a tablet' when a clean-record brand of the same salts costs less."""
    import prices

    r, _ = prices.match_plan_med(conn, m["name"], m.get("strength"))
    if not r or not r["unit_price"]:
        return None
    alt = prices.alternatives(conn, r["id"], limit=0)
    best = alt and alt["cheapest_clean"]
    return f"{best['name']}, ₹{best['unit_price']:.2f} a tablet" if best and best["unit_price"] < r["unit_price"] else None


def send_due_reminders() -> int:
    """WhatsApp / phone notification for every bought medicine whose dose time has arrived today and is not yet taken."""
    import care
    import notify

    day = datetime.now().date()
    hm = datetime.now().strftime("%H:%M")
    sent = 0
    for m in rows("""SELECT m.*, p.member, p.start_date, p.device FROM plan_meds m JOIN plans p ON p.id = m.plan_id
                     WHERE (m.bought_at IS NOT NULL AND (m.phone IS NOT NULL OR p.device IN (SELECT device FROM push_subs)))
                        OR p.device IN (SELECT device FROM tg_links WHERE role = 'self')"""):
        lang = m["language"] or "hi"
        for d in care.doses_for(m, m["start_date"], day):
            if d["time"] > hm:
                continue
            done = conn.execute("SELECT 1 FROM doses WHERE med_id = ? AND day = ? AND slot = ? UNION SELECT 1 FROM reminders_sent WHERE med_id = ? AND day = ? AND slot = ?",
                                (m["id"], day.isoformat(), d["slot"]) * 2).fetchone()
            if done:
                continue
            conn.execute("INSERT INTO reminders_sent (med_id, day, slot, sent_at) VALUES (?,?,?,?)", (m["id"], day.isoformat(), d["slot"], now()))
            text = notify.dose_text(m, m["member"], d["time"], lang)
            if m["phone"] and m["bought_at"]:
                _log_note("whatsapp", m["member"], m["phone"], lang, m["batch"], text, urgent=False)
            # Same tag as the in-page reminder, so an open tab and a push never show twice. Telegram: reply with the button to tick it.
            alert_device(m["device"], f"⏰ Time for {m['name']}", text.removeprefix("KinCare: "), "/care", f"dose-{m['id']}-{d['slot']}-{day.isoformat()}",
                         buttons=TG_BUTTONS)
            sent += 1
        # Refill: once per purchase, when about REFILL_DAYS of tablets are left.
        r = _refill(m)
        if r and r["low"] and not m["refill_sent_at"]:
            conn.execute("UPDATE plan_meds SET refill_sent_at = ? WHERE id = ?", (now(), m["id"]))
            text = notify.refill_text(m, m["member"], r["left"], r["days_left"], _cheaper_clean(m), lang)
            if m["phone"]:
                _log_note("whatsapp", m["member"], m["phone"], lang, m["batch"], text, urgent=False)
            alert_device(m["device"], f"💊 {m['name']}: {r['left']} left", text.removeprefix("KinCare: "), "/care", f"refill-{m['id']}")
            sent += 1
    conn.commit()
    return sent


@router.post("/api/care/reminders/run")
def reminders_run():
    return {"sent": send_due_reminders()}


@on_startup
def _reminder_loop():
    import threading
    import time

    def loop():
        while True:
            try:
                send_due_reminders()
            except Exception as e:  # keep the loop alive; next minute retries
                print("reminder loop:", e)
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()


@on_startup
def _warm_fda_labels():
    """Fetch the openFDA label of every common Indian brand's salt once, in the background, so the first
    interaction check (the /demo prescription step) never waits on a slow api.fda.gov call (one took 15 s)."""
    import threading

    import interactions

    def warm():
        for g in sorted(set(interactions.BRANDS.values())):
            try:
                interactions._label(conn, g)
            except Exception as e:  # offline or rate-limited: the request path fetches it later
                print("fda warm:", g, e)

    threading.Thread(target=warm, daemon=True).start()


@on_startup
def _medicine_index():
    """Trigram index for medicine search (90 ms -> 8 ms a query); ~10 s to build once, searches use LIKE until then."""
    import threading

    import prices

    threading.Thread(target=lambda: prices.ensure_fts(conn), daemon=True).start()


@on_startup
def _warm_caches():
    """Fill every derived-data cache before the first visitor, so nobody (or no burst of judges' phones) pays for it."""
    import quality

    def warm():
        for fn in (stats, datasets, insights_endpoint, recall_gap, lambda: controller_overview(None),
                   lambda: quality.cached(conn, candidates)):
            try:
                fn()
            except Exception as e:  # a cold cache is only slower, never wrong
                print("cache warm:", e)

    threading.Thread(target=warm, daemon=True).start()


@router.get("/api/care/refills")
def care_refills(account: str = Depends(current_account)):
    """Bought medicines with tablets left, days left and whether it's time to refill."""
    out = []
    for p in _plans(account):
        for m in p["medicines"]:
            r = _refill({**m, "start_date": p["start_date"]})
            if r:
                out.append({**r, "med_id": m["id"], "name": m["name"], "strength": m["strength"], "member": p["member"],
                            "reminded_at": m["refill_sent_at"]})
    return sorted(out, key=lambda x: x["days_left"])


@router.get("/api/care/interactions")
def care_interactions(names: str | None = None, account: str = Depends(current_account)):
    """Pairs of the patient's medicines that mention each other on their official label."""
    import interactions

    meds = [n.strip() for n in names.split(",")] if names else [m["name"] for p in _plans(account) for m in p["medicines"]]
    return interactions.check(conn, [m for m in meds if m])


@router.get("/api/care/report")
def care_report(member: str = "Me", account: str = Depends(current_account)):
    """Everything a doctor needs at the follow-up visit, for one family member."""
    import care

    dev = account
    plans = _plans(dev, member)
    adherence = []
    today = datetime.now().date()
    for p in plans:
        start = datetime.fromisoformat(p["start_date"]).date()
        for m in p["medicines"]:
            due = taken = 0
            d = start
            while d <= today:
                for s in care.doses_for(m, p["start_date"], d):
                    due += 1
                    taken += bool(conn.execute("SELECT 1 FROM doses WHERE med_id = ? AND day = ? AND slot = ?", (m["id"], d.isoformat(), s["slot"])).fetchone())
                d = date.fromordinal(d.toordinal() + 1)
            adherence.append({"name": m["name"], "due": due, "taken": taken})
    return {"member": member, "generated_at": now(), "vitals": vitals_list(member, account), "plans": plans, "adherence": adherence}


# Imported last, used only when a request runs: these modules import from this one too.
from routes.alerts import insights_endpoint, stats  # noqa: E402
from routes.blast_radius import recall_gap  # noqa: E402
from routes.family import tell_caregivers  # noqa: E402
from routes.live_vitals import datasets  # noqa: E402
from routes.regulator import controller_overview  # noqa: E402
from routes.telegram_bot import TG_BUTTONS  # noqa: E402
