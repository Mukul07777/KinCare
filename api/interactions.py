"""Drug-interaction check across a patient's prescribed medicines, from openFDA drug labels.

For every pair (A, B) we read the "Drug Interactions" / "Warnings" sections of A's
official US label and look for B's generic name. Shown as "ask your doctor", never advice.
"""
import json
import re
import sqlite3

import requests

FDA = "https://api.fda.gov/drug/label.json"

# Common Indian brands -> generic (US label names where they differ).
BRANDS = {
    "crocin": "acetaminophen", "dolo": "acetaminophen", "calpol": "acetaminophen", "paracetamol": "acetaminophen",
    "combiflam": "ibuprofen", "brufen": "ibuprofen", "disprin": "aspirin", "ecosprin": "aspirin",
    "pan": "pantoprazole", "pantocid": "pantoprazole", "omez": "omeprazole", "rantac": "ranitidine",
    "glycomet": "metformin", "amaryl": "glimepiride", "telma": "telmisartan", "amlong": "amlodipine", "stamlo": "amlodipine",
    "atorva": "atorvastatin", "storvas": "atorvastatin", "rosuvas": "rosuvastatin", "clopilet": "clopidogrel",
    "augmentin": "amoxicillin", "mox": "amoxicillin", "azithral": "azithromycin", "azee": "azithromycin",
    "cifran": "ciprofloxacin", "ciplox": "ciprofloxacin", "allegra": "fexofenadine", "cetzine": "cetirizine",
    "montair": "montelukast", "thyronorm": "levothyroxine", "eltroxin": "levothyroxine", "warf": "warfarin",
    "ativan": "lorazepam", "alprax": "alprazolam", "nexito": "escitalopram", "shelcal": "calcium carbonate",
}
SECTIONS = ("drug_interactions", "warnings", "boxed_warning", "precautions")


def generic(name: str) -> str:
    word = re.sub(r"[^a-z ]", " ", name.lower()).split()
    for w in word:
        if w in BRANDS:
            return BRANDS[w]
    return word[0] if word else name.lower()


def _label(conn: sqlite3.Connection, g: str) -> dict | None:
    conn.execute("CREATE TABLE IF NOT EXISTS fda_labels (generic TEXT PRIMARY KEY, body TEXT)")
    row = conn.execute("SELECT body FROM fda_labels WHERE generic = ?", (g,)).fetchone()
    if row:
        return json.loads(row[0])
    try:
        r = requests.get(FDA, params={"search": f'openfda.generic_name:"{g}"', "limit": 1}, timeout=15)
        res = r.json().get("results", []) if r.ok else []
    except requests.RequestException:
        return None  # offline: don't cache, try next time
    body = {s: " ".join(res[0].get(s, [])) for s in SECTIONS} if res else {}
    conn.execute("INSERT OR REPLACE INTO fda_labels (generic, body) VALUES (?, ?)", (g, json.dumps(body)))
    conn.commit()
    return body


def _snippet(text: str, term: str) -> str:
    i = text.lower().find(term)
    start = max(0, text.rfind(".", 0, i) + 1)
    end = text.find(".", i)
    return text[start: end + 1 if end != -1 else i + 200].strip()[:320]


def check(conn: sqlite3.Connection, names: list[str]) -> dict:
    meds = [{"name": n, "generic": generic(n)} for n in dict.fromkeys(names)]
    found, missing = [], []
    for a in meds:
        lab = _label(conn, a["generic"])
        if not lab:
            missing.append(a["name"])
            continue
        for b in meds:
            if b is a or b["generic"] == a["generic"]:
                continue
            for sec in SECTIONS:
                text = lab.get(sec, "")
                if re.search(rf"\b{re.escape(b['generic'])}\b", text, re.I):
                    found.append({"a": a["name"], "b": b["name"], "section": sec.replace("_", " "),
                                  "severity": "high" if sec == "boxed_warning" else "check",
                                  "evidence": _snippet(text, b["generic"])})
                    break
    # Keep one entry per pair.
    seen, out = set(), []
    for f in found:
        key = frozenset((f["a"], f["b"]))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return {"medicines": meds, "interactions": out, "no_label": missing, "source": "openFDA drug labels (api.fda.gov)"}
