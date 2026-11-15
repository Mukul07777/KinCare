"""Google Gemini: a short, warm, plain-language care note for the elder and their circle.

Gemini only *explains* the numbers we already computed (adherence, often-missed doses, next appointment).
It is told never to suggest, change or stop a medicine. Without GEMINI_API_KEY, or if the call fails,
a deterministic note is returned, so the feature never breaks.
"""
import os

import requests

MODEL = lambda: os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"  # noqa: E731
RULES = ("You write a short care note (max 90 words) for an elderly person in India and their family. "
         "Be warm and respectful, speak to the elder directly, simple words, no medical jargon. "
         "Never suggest starting, stopping, changing or doubling any medicine or dose; for any concern say 'ask your doctor'. "
         "Mention one thing going well, one gentle focus for this week, and the next appointment if any. No markdown.")


def ready() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def facts(elder: str, adherence: dict, appts: list[dict]) -> str:
    missed = [f"{m['name']} ({m['pct']}%)" for m in adherence["medicines"] if m["pct"] is not None and m["pct"] < 80]
    nxt = f"{appts[0]['doctor']} on {appts[0]['at'].replace('T', ' at ')}" if appts else "none booked"
    return (f"Elder: {elder}. Doses taken last 7 days: {adherence['pct_7']}%. Last 30 days: {adherence['pct_30']}%. "
            f"Days in a row with every dose: {adherence['streak_days']}. Often missed: {', '.join(missed) or 'none'}. Next appointment: {nxt}.")


def fallback(elder: str, adherence: dict, appts: list[dict], lang: str) -> str:
    p = adherence["pct_7"]
    missed = [m["name"] for m in adherence["medicines"] if m["pct"] is not None and m["pct"] < 80]
    if lang == "hi":
        s = f"{elder} जी, इस हफ़्ते आपने {p if p is not None else '-'}% खुराक समय पर लीं।"
        s += f" {', '.join(missed)} पर थोड़ा ध्यान दें।" if missed else " बहुत बढ़िया, ऐसे ही चलते रहें।"
        return s + (f" अगली डॉक्टर विज़िट: {appts[0]['doctor']}, {appts[0]['at'].replace('T', ' ')}।" if appts else "")
    s = f"{elder}, you took {p if p is not None else '-'}% of your doses this week."
    s += f" A little extra care with {', '.join(missed)} would help; ask your doctor if anything feels hard." if missed else " Wonderful, keep it up."
    return s + (f" Next visit: {appts[0]['doctor']}, {appts[0]['at'].replace('T', ' ')}." if appts else "")


def care_note(elder: str, adherence: dict, appts: list[dict], lang: str = "en") -> dict:
    if ready():
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL()}:generateContent",
                headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=20,
                json={"systemInstruction": {"parts": [{"text": RULES}]},
                      "contents": [{"role": "user", "parts": [{"text": facts(elder, adherence, appts) + f" Write in {'Hindi' if lang == 'hi' else 'English'}."}]}],
                      "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300}})
            r.raise_for_status()
            text = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]).strip()
            if text:
                return {"text": text, "source": "gemini"}
        except Exception as e:  # quota, network, safety block: fall back
            print("gemini:", str(e)[:200])
    return {"text": fallback(elder, adherence, appts, lang), "source": "rules"}
