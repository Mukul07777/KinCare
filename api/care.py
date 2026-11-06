"""Care: vitals, doctor's prescription, dose reminders, report.

Rules this module never breaks:
- It never suggests, changes or doses a medicine. Medicines come only from a
  doctor's prescription that the patient confirms.
- Vitals produce one of three messages: fine / see a doctor / get urgent help.
"""
import re
from datetime import date, timedelta

# ---- vitals ----

def assess(temp_c: float | None, sys_: int | None, dia: int | None, pulse: int | None, spo2: int | None) -> dict:
    """Conservative red-flag thresholds (adult). Only says *when* to get care, never *what* to take."""
    urgent, doctor = [], []
    if temp_c is not None:
        if temp_c >= 40.0 or temp_c < 35.0:
            urgent.append(f"Temperature {temp_c:.1f}°C")
        elif temp_c >= 38.0:
            doctor.append(f"Fever {temp_c:.1f}°C")
    if sys_ is not None:
        if sys_ >= 180 or sys_ < 90:
            urgent.append(f"BP {sys_}/{dia or '?'}")
        elif sys_ >= 140:
            doctor.append(f"High BP {sys_}/{dia or '?'}")
    if dia is not None and dia >= 120 and not any(u.startswith("BP") for u in urgent):
        urgent.append(f"BP {sys_ or '?'}/{dia}")
    if spo2 is not None:
        if spo2 < 92:
            urgent.append(f"Oxygen {spo2}%")
        elif spo2 < 95:
            doctor.append(f"Low oxygen {spo2}%")
    if pulse is not None:
        if pulse > 130 or pulse < 45:
            urgent.append(f"Pulse {pulse}")
        elif pulse > 100 or pulse < 55:
            doctor.append(f"Pulse {pulse}")

    if urgent:
        return {"level": "urgent", "reasons": urgent + doctor,
                "en": "Get medical help now. Call your doctor, or 108 in an emergency.",
                "hi": "तुरंत डॉक्टरी मदद लें। अपने डॉक्टर को या आपातकाल में 108 पर फ़ोन करें।"}
    if doctor:
        return {"level": "doctor", "reasons": doctor,
                "en": "Please see a doctor today. Do not start any medicine without their advice.",
                "hi": "कृपया आज डॉक्टर को दिखाएँ। उनकी सलाह के बिना कोई दवा शुरू न करें।"}
    return {"level": "ok", "reasons": [], "en": "Readings look within the usual range. Keep resting and stay hydrated.",
            "hi": "रीडिंग सामान्य दायरे में है। आराम करें और पानी पीते रहें।"}


# ---- prescription parsing ----

FORM = r"(?:tab(?:let)?s?|cap(?:sule)?s?|syp|syrup|susp|inj(?:ection)?|drops?|oint(?:ment)?|cream|gel)\.?"
FREQ = {  # (morning, noon, night)
    "od": (1, 0, 0), "qd": (1, 0, 0), "once daily": (1, 0, 0), "hs": (0, 0, 1), "at night": (0, 0, 1), "bedtime": (0, 0, 1),
    "bd": (1, 0, 1), "bid": (1, 0, 1), "twice daily": (1, 0, 1), "tds": (1, 1, 1), "tid": (1, 1, 1), "thrice daily": (1, 1, 1),
    "sos": (0, 0, 0), "prn": (0, 0, 0),
}
ADVICE = [
    (r"\brest\b|bed ?rest", "Rest", "आराम करें"),
    (r"fluid|water|hydrat|ors\b", "Drink plenty of fluids", "ख़ूब पानी/तरल लें"),
    (r"steam", "Steam inhalation", "भाप लें"),
    (r"gargle", "Warm salt-water gargles", "गुनगुने नमक-पानी से गरारे"),
    (r"light diet|soft diet|avoid (oily|spicy)", "Light diet", "हल्का खाना"),
    (r"follow ?up|review after|revisit", "Follow-up visit", "दोबारा दिखाएँ"),
    (r"monitor (temp|bp|sugar)|check (temp|bp|sugar)", "Keep monitoring readings", "रीडिंग नापते रहें"),
]


def parse_prescription(text: str) -> dict:
    meds, advice = [], []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        low = line.lower()
        m = re.search(rf"\b{FORM}\s+([A-Za-z][A-Za-z0-9\-]*(?:\s+[A-Za-z0-9\-]+)?)", line, re.I)
        pattern = re.search(r"\b([01])\s*[-–]\s*([01])\s*[-–]\s*([01])\b", line)
        freq = next((v for k, v in FREQ.items() if re.search(rf"\b{k}\b", low)), None)
        if m and (pattern or freq is not None or re.search(r"\d+\s*(mg|ml|mcg)", low)):
            name = re.sub(r"\s+\d+\s*(mg|ml|mcg)?$", "", m.group(1)).strip()
            dose = re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g)\b", line, re.I)
            days = re.search(r"(?:x|for)\s*(\d{1,2})\s*(?:days?|d)\b|\b(\d{1,2})\s*days?\b", low)
            sched = tuple(int(x) for x in pattern.groups()) if pattern else (freq or (1, 0, 0))
            meds.append({
                "name": name.title(),
                "strength": dose.group(0) if dose else "",
                "morning": sched[0], "noon": sched[1], "night": sched[2],
                # "pc" = post cibum (after food), "ac" = ante cibum (before food)
                "food": "after food" if re.search(r"after (food|meals?)|\bpc\b", low)
                        else "before food" if re.search(r"before (food|meals?)|\bac\b|empty stomach", low) else "",
                "days": int(next(g for g in days.groups() if g)) if days else None,
                "as_needed": bool(re.search(r"\bsos\b|\bprn\b|if needed|when required", low)),
                "line": line,
            })
            continue
        for pat, en, hi in ADVICE:
            if re.search(pat, low) and en not in [a["en"] for a in advice]:
                advice.append({"en": en, "hi": hi})
    return {"medicines": meds, "advice": advice}


SLOTS = [("morning", "08:00"), ("noon", "14:00"), ("night", "21:00")]


def doses_for(med: dict, start: str, on: date) -> list[dict]:
    """Doses due on a given day for one prescribed medicine."""
    s = date.fromisoformat(start)
    if on < s or (med["days"] and on >= s + timedelta(days=med["days"])) or med["as_needed"]:
        return []
    return [{"slot": slot, "time": t} for slot, t in SLOTS if med[slot]]


# ---- refills ----

REFILL_DAYS = 3  # warn when this many days of tablets are left


def refill_status(med: dict, start: str, qty: float, taken: int, on: date) -> dict | None:
    """Tablets left from the last purchase, and whether to remind about a refill.

    No reminder when the course ends before the tablets run out, or for as-needed medicines."""
    per_day = (med["morning"] or 0) + (med["noon"] or 0) + (med["night"] or 0)
    if not qty or not per_day or med["as_needed"]:
        return None
    left = max(qty - taken, 0)
    days_left = left / per_day
    course_left = None
    if med["days"]:
        course_left = max((date.fromisoformat(start) + timedelta(days=med["days"]) - on).days, 0)
    needed = course_left is None or left < course_left * per_day
    return {"left": int(left), "per_day": per_day, "days_left": round(days_left, 1),
            "course_days_left": course_left, "low": needed and days_left <= REFILL_DAYS}
