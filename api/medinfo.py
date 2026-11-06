"""Medicine info page: what a medicine is for, how to take it, side effects and warnings.

Text comes from the official US FDA label of each salt (openFDA, cached). Indian brands share the
salt, not always the label, so the page says so. KinCare adds what no label has: CDSCO batch alerts
for that salt, the maker's record, and where this brand sits on price.
"""
import json
import re
import sqlite3

import requests

import prices

FDA = "https://api.fda.gov/drug/label.json"

# Indian (INN / BP) salt names -> US label names where they differ.
US_NAME = {
    "paracetamol": "acetaminophen", "amoxycillin": "amoxicillin", "salbutamol": "albuterol", "levosalbutamol": "levalbuterol",
    "glibenclamide": "glyburide", "frusemide": "furosemide", "adrenaline": "epinephrine", "noradrenaline": "norepinephrine",
    "thyroxine": "levothyroxine", "levothyroxine sodium": "levothyroxine", "cholecalciferol": "cholecalciferol",
    "clavulanic acid": "clavulanate potassium", "potassium clavulanate": "clavulanate potassium", "rabeprazole": "rabeprazole sodium",
    "metformin": "metformin hydrochloride", "ondansetron": "ondansetron", "lignocaine": "lidocaine", "pethidine": "meperidine",
}

# Label section -> what the patient sees. First section found wins (Rx labels and OTC labels name them differently).
SECTIONS = {
    "uses": ("indications_and_usage", "purpose"),
    "how_to_take": ("dosage_and_administration", "directions"),
    "side_effects": ("adverse_reactions",),
    "warnings": ("boxed_warning", "warnings_and_cautions", "warnings"),
    "do_not_take": ("contraindications", "do_not_use"),
    "pregnancy": ("pregnancy", "pregnancy_or_breast_feeding", "use_in_specific_populations"),
}
MAX_CHARS = 900


def salt_names(salts: str) -> list[str]:
    """'telmisartan (40mg) + hydrochlorothiazide (12.5mg)' -> ['telmisartan', 'hydrochlorothiazide']."""
    out = []
    for part in re.split(r"\s*\+\s*", salts or ""):
        name = " ".join(re.sub(r"\(.*?\)", " ", part.lower()).split())
        if name and name not in out:
            out.append(name)
    return out


def us_name(salt: str) -> str:
    return US_NAME.get(salt, salt)


def _clean(text: str) -> str:
    """Labels repeat the heading ("1 INDICATIONS AND USAGE ...") and run long; keep readable sentences only."""
    text = " ".join(text.split())
    # Drop the all-caps heading words only; stop at the first normal word ("Telmisartan ...").
    body = re.sub(r"^[\d.\s]*(?:[A-Z][A-Z&/,():-]+\s+)+", "", text)
    text = body if len(body) > 40 else text
    if len(text) <= MAX_CHARS:
        return text
    cut = text.rfind(". ", 0, MAX_CHARS)
    return text[: cut + 1 if cut > 200 else MAX_CHARS].rstrip() + " …"


def label(conn: sqlite3.Connection, generic: str) -> dict | None:
    """Patient-facing sections of the FDA label for one salt. None = offline (not cached, retried later); {} = no label."""
    conn.execute("CREATE TABLE IF NOT EXISTS fda_info (generic TEXT PRIMARY KEY, body TEXT)")
    row = conn.execute("SELECT body FROM fda_info WHERE generic = ?", (generic,)).fetchone()
    if row:
        return json.loads(row[0])
    try:
        r = requests.get(FDA, params={"search": f'openfda.generic_name:"{generic}"', "limit": 1}, timeout=15)
        res = r.json().get("results", []) if r.ok else []
    except requests.RequestException:
        return None
    body = {}
    if res:
        lab = res[0]
        for key, names in SECTIONS.items():
            text = next((" ".join(lab[n]) for n in names if lab.get(n)), "")
            if text:
                body[key] = _clean(text)
        body["label_name"] = ", ".join(lab.get("openfda", {}).get("generic_name", [])[:1]) or generic
    conn.execute("INSERT OR REPLACE INTO fda_info (generic, body) VALUES (?, ?)", (generic, json.dumps(body)))
    conn.commit()
    return body


def salt_alerts(conn: sqlite3.Connection, salts: list[str], limit: int = 8) -> dict:
    """CDSCO / state alerts whose product name mentions the medicine's main salt."""
    if not salts:
        return {"salt": None, "total": 0, "spurious": 0, "recent": []}
    salt = salts[0].split()[0]  # "metformin hydrochloride" -> "metformin": product names in alerts are free text
    like = f"%{salt}%"
    total, spurious = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(category = 'spurious'), 0) FROM alerts WHERE lower(product_name) LIKE ?", (like,)).fetchone()
    recent = [dict(r) for r in conn.execute(
        """SELECT id, product_name, batch_no, manufacturer, category, reason, alert_month FROM alerts
           WHERE lower(product_name) LIKE ? ORDER BY alert_month DESC, id DESC LIMIT ?""", (like, limit))]
    return {"salt": salt, "total": total, "spurious": spurious, "recent": recent}


def info(conn: sqlite3.Connection, mid: int) -> dict | None:
    alt = prices.alternatives(conn, mid, limit=0)
    if not alt:
        return None
    names = salt_names(alt["medicine"]["salts"])
    salts = []
    for s in names:
        g = us_name(s)
        salts.append({"name": s, "label_name": g, "label": label(conn, g)})
    return {
        "medicine": alt["medicine"],
        "salts": salts,
        "alerts": salt_alerts(conn, names),
        "price": {"brands": alt["brands"], "rank": alt["rank"], "unit_price": alt["unit_price"], "cheapest_clean": alt["cheapest_clean"]},
        "source": "US FDA drug labels (openFDA, api.fda.gov), by salt",
    }
