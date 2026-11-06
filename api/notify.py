"""Patient notifications: WhatsApp message + voice call in Hindi or English.

WhatsApp goes through Meta's Cloud API when WHATSAPP_* is set (cheapest, see whatsapp.py),
else Twilio when TWILIO_* is set (voice calls always use Twilio). Otherwise each message
is recorded with status "outbox" so the UI can show exactly what would be sent
(and speak the voice script in the browser).
"""
import os
from xml.sax.saxutils import escape

import requests

import whatsapp

conn = None  # set by main: the WhatsApp 24-hour window lives in the database

CATEGORY = {
    "en": {"spurious": "spurious", "nsq": "not of standard quality"},
    "hi": {"spurious": "नकली (स्प्यूरियस)", "nsq": "मानक गुणवत्ता से कम (NSQ)"},
}


def _month(ym: str, lang: str) -> str:
    y, m = ym.split("-")
    en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    hi = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
    return f"{(hi if lang == 'hi' else en)[int(m) - 1]} {y}"


def whatsapp_text(alert: dict, batch: str, name: str | None, lang: str, checkin_url: str | None = None) -> str:
    cat = CATEGORY[lang][alert["category"]]
    med = alert.get("brand") or alert["product_name"]
    if lang == "hi":
        return (
            f"नमस्ते{(' ' + name) if name else ''}, KinCare की ओर से ज़रूरी सूचना।\n"
            f"दवा: {med}\nबैच: {batch}\n"
            f"इस बैच को {_month(alert['alert_month'], 'hi')} की सरकारी (CDSCO) सूची में {cat} बताया गया है।\n"
            f"कृपया अपनी दवा अपने आप बंद न करें। आज ही अपने फ़ार्मासिस्ट या डॉक्टर को यह संदेश दिखाएँ।\n"
            + (f"आप कैसा महसूस कर रहे हैं? यहाँ बताएँ: {checkin_url}\n" if checkin_url else "")
            + f"स्रोत: {alert['alert_url']}"
        )
    return (
        f"Hello{(' ' + name) if name else ''}, an important notice from KinCare.\n"
        f"Medicine: {med}\nBatch: {batch}\n"
        f"This batch is listed as {cat} in the {_month(alert['alert_month'], 'en')} regulator (CDSCO) alert.\n"
        f"Please do not stop any medicine on your own. Show this message to your pharmacist or doctor today.\n"
        + (f"How are you feeling? Tell us here: {checkin_url}\n" if checkin_url else "")
        + f"Source: {alert['alert_url']}"
    )


def voice_script(alert: dict, batch: str, name: str | None, lang: str) -> str:
    med = alert.get("brand") or alert["product_name"]
    spoken_batch = " ".join(batch)  # read the batch character by character
    if lang == "hi":
        return (
            f"नमस्ते{(' ' + name) if name else ''}। यह KinCare की ओर से एक ज़रूरी कॉल है। "
            f"आपकी दवा {med}, बैच नंबर {spoken_batch}, को सरकारी सूची में {CATEGORY['hi'][alert['category']]} बताया गया है। "
            f"कृपया दवा अपने आप बंद न करें। आज ही अपने फ़ार्मासिस्ट या डॉक्टर से बात करें। "
            f"पूरी जानकारी आपके व्हाट्सऐप पर भेज दी गई है। धन्यवाद।"
        )
    return (
        f"Hello{(' ' + name) if name else ''}. This is an important call from KinCare. "
        f"Your medicine {med}, batch number {spoken_batch}, is listed as {CATEGORY['en'][alert['category']]} in a government alert. "
        f"Please do not stop the medicine on your own. Speak to your pharmacist or doctor today. "
        f"The details have been sent to your WhatsApp. Thank you."
    )


def twilio_ready() -> bool:
    return all(os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"))


def _twilio(path: str, data: dict) -> str:
    sid, token = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/{path}", data=data, auth=(sid, token), timeout=30)
    r.raise_for_status()
    return r.json()["sid"]


def whatsapp_ready() -> bool:
    return whatsapp.ready() or (twilio_ready() and bool(os.environ.get("TWILIO_WHATSAPP_FROM")))


def send_whatsapp(phone: str, text: str, urgent: bool = True) -> tuple[str, str | None]:
    """urgent=False for routine reminders: those respect the monthly paid-message cap (recalls and SOS never do)."""
    if whatsapp.ready() and conn is not None:
        return whatsapp.send(conn, phone, text, urgent)
    sender = os.environ.get("TWILIO_WHATSAPP_FROM")
    if not (twilio_ready() and sender):
        return "outbox", None
    return "sent", _twilio("Messages.json", {"From": f"whatsapp:{sender}", "To": f"whatsapp:{phone}", "Body": text})


def place_call(phone: str, script: str, lang: str) -> tuple[str, str | None]:
    sender = os.environ.get("TWILIO_VOICE_FROM")
    if not (twilio_ready() and sender):
        return "outbox", None
    voice = 'language="hi-IN" voice="Polly.Aditi"' if lang == "hi" else 'language="en-IN" voice="Polly.Raveena"'
    twiml = f"<Response><Say {voice}>{escape(script)}</Say><Pause length=\"1\"/><Say {voice}>{escape(script)}</Say></Response>"
    return "sent", _twilio("Calls.json", {"From": sender, "To": phone, "Twiml": twiml})


def purchase_text(med: dict, member: str, due_now: bool, next_time: str | None, lang: str) -> str:
    """WhatsApp sent right after a prescribed medicine is bought."""
    name = f"{med['name']} {med.get('strength') or ''}".strip()
    food = f" ({med['food']})" if med.get("food") else ""
    if lang == "hi":
        head = f"KinCare: {member} ke liye {name} kharid li gayi (batch {med['batch']}). Is batch par koi regulator alert nahi mila."
        when = f"Abhi dawa lene ka samay hai{food}." if due_now else (f"Agli khuraak {next_time} baje{food}." if next_time else "Aaj aur koi khuraak baaki nahi.")
        return f"{head}\n{when}\nHar khuraak par hum yaad dilayenge. Dawa lene ke baad *1* bhejein."
    head = f"KinCare: {name} bought for {member} (batch {med['batch']}). No regulator alert found for this batch."
    when = f"Please take your dose now{food}." if due_now else (f"Next dose at {next_time}{food}." if next_time else "No more doses due today.")
    return f"{head}\n{when}\nWe will remind you at every dose. Reply *1* once taken."


def dose_text(med: dict, member: str, time: str, lang: str) -> str:
    name = f"{med['name']} {med.get('strength') or ''}".strip()
    food = f" ({med['food']})" if med.get("food") else ""
    if lang == "hi":
        return f"KinCare: {member}, {time} baj gaye. {name} lene ka samay hai{food}.\nDawa lene ke baad *1* likh kar bhejein."
    return f"KinCare: {member}, it's {time}. Time to take {name}{food}.\nReply *1* once taken."


def refill_text(med: dict, member: str, left: int, days_left: float, cheaper: str | None, lang: str) -> str:
    """Sent once when a bought medicine is about to run out."""
    name = f"{med['name']} {med.get('strength') or ''}".strip()
    days = max(int(days_left), 0)
    if lang == "hi":
        msg = f"KinCare: {member} ki {name} ki sirf {left} goli bachi hai (lagbhag {days} din). Khatam hone se pehle dobara le lein."
        if cheaper:
            msg += f"\nWahi salt sasta: {cheaper}. Badalne se pehle doctor/pharmacist se poochhein."
        return msg + "\nKharidne ke baad app mein naya batch darj karein."
    msg = f"KinCare: only {left} tablets of {name} left for {member} (about {days} days). Please refill before it runs out."
    if cheaper:
        msg += f"\nSame salt for less: {cheaper}. Ask your doctor or pharmacist before switching."
    return msg + "\nEnter the new batch in the app after you buy it."
