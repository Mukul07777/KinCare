"""Post-recall check-in: did the patient feel unwell?

Every recall message carries a personal link. The patient answers in a few
taps; red-flag answers are triaged "urgent" so the pharmacist calls first.
Triage rules are deliberately simple and conservative; they decide who gets
a call back first, never what treatment to give.
"""
import os
import secrets

PUBLIC_WEB_URL = os.environ.get("PUBLIC_WEB_URL", "http://localhost:3000")

RED_FLAGS = {"breathlessness", "chest_pain", "rash_swelling", "fainting", "confusion", "bleeding"}
SYMPTOMS = {
    "dizziness": ("Dizziness", "चक्कर"),
    "headache": ("Headache", "सिरदर्द"),
    "nausea": ("Nausea / vomiting", "उल्टी / जी मिचलाना"),
    "no_effect": ("Medicine not working", "दवा असर नहीं कर रही"),
    "fever": ("Fever", "बुखार"),
    "rash_swelling": ("Rash or swelling", "दाने या सूजन"),
    "breathlessness": ("Breathlessness", "साँस फूलना"),
    "chest_pain": ("Chest pain", "सीने में दर्द"),
    "fainting": ("Fainting", "बेहोशी"),
    "confusion": ("Confusion", "भ्रम / उलझन"),
    "bleeding": ("Unusual bleeding", "असामान्य रक्तस्राव"),
}


def create(conn, *, name, phone, language, batch, alert_id) -> str:
    token = secrets.token_urlsafe(16)  # 128 bits: the link alone opens the check-in
    conn.execute(
        "INSERT INTO checkins (token, name, phone, language, batch, alert_id) VALUES (?,?,?,?,?,?)",
        (token, name, phone, language, batch, alert_id),
    )
    return token


def link(token: str) -> str:
    return f"{PUBLIC_WEB_URL}/checkin?t={token}"


def triage(feeling: str, symptoms: list[str], sys_: int | None, dia: int | None) -> str:
    if set(symptoms) & RED_FLAGS:
        return "urgent"
    if sys_ and (sys_ >= 180 or sys_ < 90):
        return "urgent"
    if dia and dia >= 120:
        return "urgent"
    if feeling == "unwell" or symptoms or (sys_ and sys_ >= 160):
        return "review"
    return "ok"
