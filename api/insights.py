"""Turn raw regulator wording into plain-language categories.

- failure categories, with what each means for a patient (English + Hindi)
- testing lab -> state
- dosage form and broad therapeutic group from the product name
Rule-based on purpose: every label can be traced to the words that triggered it.
"""
import re

# (key, pattern, severity, English meaning, Hindi meaning)
FAILURES = [
    ("toxic_contaminant", r"diethylene|ethylene glycol", "critical",
     "Contains a toxic industrial chemical (DEG/EG). This contaminant has caused child deaths in India. Do not use; see a doctor.",
     "इसमें ज़हरीला रसायन (DEG/EG) पाया गया। इसी से भारत में बच्चों की मौतें हुई हैं। उपयोग न करें, डॉक्टर से मिलें।"),
    ("spurious", r"spurious|not manufactured|impugned", "critical",
     "The named company says it did not make this batch. It may be a fake.",
     "नामित कंपनी कहती है कि यह बैच उसने नहीं बनाया। यह नकली हो सकता है।"),
    ("sterility", r"steril|bacterial endotoxin|endotoxin|microbial|pyrogen", "high",
     "Failed a germ or contamination test. For injections and eye drops this can cause infection.",
     "कीटाणु/संक्रमण जाँच में फेल। इंजेक्शन या आई-ड्रॉप में इससे संक्रमण हो सकता है।"),
    ("particulate", r"particulate|foreign (matter|particle)|visible particle", "high",
     "Tiny particles found in the product. Unsafe especially in injections.",
     "दवा में बारीक कण पाए गए। ख़ासकर इंजेक्शन में यह असुरक्षित है।"),
    ("assay", r"\bassay|content of|active ingredient", "medium",
     "Contains the wrong amount of medicine: too little may not work, too much may cause side effects.",
     "दवा की मात्रा सही नहीं: कम हो तो असर नहीं करेगी, ज़्यादा हो तो दुष्प्रभाव हो सकते हैं।"),
    ("dissolution", r"dissolution|disintegration", "medium",
     "The tablet may not dissolve properly in the body, so less medicine gets absorbed.",
     "गोली शरीर में ठीक से नहीं घुलती, इसलिए दवा कम असर करती है।"),
    ("identity", r"identification|identity", "high",
     "The expected medicine could not be confirmed in the sample.",
     "नमूने में अपेक्षित दवा की पुष्टि नहीं हुई।"),
    ("impurity", r"related substance|impurit|degradation", "medium",
     "Has more impurities or breakdown products than allowed.",
     "इसमें अनुमति से ज़्यादा अशुद्धियाँ हैं।"),
    ("uniformity", r"uniformity|weight variation|average weight|\bweight\b", "low",
     "Tablets vary too much in weight or dose from one to the next.",
     "हर गोली में दवा या वज़न एक-सा नहीं है।"),
    ("ph_physical", r"\bph\b|viscosity|water content|loss on drying|friability|fill|leak|extractable|alcohol", "low",
     "A physical or chemical property (pH, water, fill volume…) is outside limits.",
     "कोई भौतिक/रासायनिक गुण (pH, पानी, मात्रा…) सीमा से बाहर है।"),
    ("description", r"description|appearance|colou?r|odou?r", "low",
     "Looks, smells or feels different from what it should.",
     "दवा का रूप, रंग या गंध जैसा होना चाहिए वैसा नहीं है।"),
    ("labelling", r"label|misbrand", "low",
     "Label information is wrong or missing.",
     "लेबल की जानकारी ग़लत या अधूरी है।"),
]
LABEL = {
    "toxic_contaminant": "Toxic contaminant", "spurious": "Possibly fake", "sterility": "Contamination / sterility",
    "particulate": "Particles found", "assay": "Wrong strength", "dissolution": "Doesn't dissolve properly",
    "identity": "Identity not confirmed", "impurity": "Impurities", "uniformity": "Uneven dose",
    "ph_physical": "Physical property", "description": "Appearance", "labelling": "Labelling", "other": "Other",
}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def failures_of(reason: str, category: str = "nsq") -> list[dict]:
    r = (reason or "").lower()
    out = [{"key": k, "label": LABEL[k], "severity": sev, "en": en, "hi": hi}
           for k, pat, sev, en, hi in FAILURES if re.search(pat, r)]
    if category == "spurious" and not any(f["key"] == "spurious" for f in out):
        k, _, sev, en, hi = FAILURES[1]
        out.insert(0, {"key": k, "label": LABEL[k], "severity": sev, "en": en, "hi": hi})
    return sorted(out, key=lambda f: SEVERITY_RANK[f["severity"]]) or [
        {"key": "other", "label": "Other", "severity": "medium",
         "en": "Did not meet the required quality standard.", "hi": "आवश्यक गुणवत्ता मानक पूरा नहीं किया।"}]


STATES = {
    "Andhra Pradesh": ["andhra", "vijayawada", "hyderabad (ap)"], "Assam": ["guwahati", "assam"],
    "Bihar": ["patna", "bihar"], "Chandigarh": ["chandigarh"], "Chhattisgarh": ["raipur", "chhattisgarh"],
    "Delhi": ["delhi"], "Goa": ["goa", "panaji"], "Gujarat": ["gujarat", "vadodara", "ahmedabad"],
    "Haryana": ["haryana"], "Himachal Pradesh": ["himachal", "baddi", "kandaghat"],
    "Jammu & Kashmir": ["jammu", "kashmir", "srinagar"], "Jharkhand": ["ranchi", "jharkhand"],
    "Karnataka": ["karnataka", "bengaluru", "bangalore", "bellary", "hubli"], "Kerala": ["kerala", "thiruvananthapuram", "ernakulam", "kochi"],
    "Madhya Pradesh": ["madhya", "bhopal", "indore"], "Maharashtra": ["mumbai", "maharashtra", "pune", "nagpur", "aurangabad"],
    "Odisha": ["odisha", "bhubaneswar", "orissa"], "Puducherry": ["puducherry", "pondicherry"], "Punjab": ["punjab", "kharar"],
    "Rajasthan": ["rajasthan", "jaipur"], "Tamil Nadu": ["chennai", "madurai", "tamil", "coimbatore"],
    "Telangana": ["telangana", "hyderabad"], "Uttar Pradesh": ["uttar pradesh", "lucknow", "ghaziabad", "agra", "meerut"],
    "Uttarakhand": ["uttarakhand", "dehradun"], "West Bengal": ["kolkata", "west bengal"],
    "Sikkim": ["sikkim", "gangtok"], "Tripura": ["tripura", "agartala"], "Meghalaya": ["meghalaya", "shillong"],
}


def state_of(lab: str) -> str | None:
    s = (lab or "").lower()
    for state, keys in STATES.items():
        if any(k in s for k in keys):
            return state
    return None


FORMS = [("Injection", r"inject|infusion|i\.v\.|vial|ampoule"), ("Syrup / liquid", r"syrup|suspension|oral solution|elixir|liquid|drops?\b"),
         ("Capsule", r"capsule"), ("Tablet", r"tablet|tab\b"), ("Cream / ointment", r"cream|ointment|gel\b|lotion"),
         ("Eye / ear drops", r"eye|ophthalmic|ear drop")]
GROUPS = [
    ("Antibiotics", r"cef|amoxi|azithro|oflox|ciproflox|levoflox|clavul|doxycyc|metronid|ornidazole|linezolid|norflox|cloxacil|clarithro"),
    ("Heart & BP", r"telmisartan|amlodipine|atorvastatin|rosuvastatin|losartan|olmesartan|metoprolol|clopidogrel|aspirin|ramipril|atenolol"),
    ("Diabetes", r"metformin|glimepiride|gliclazide|sitagliptin|vildagliptin|teneligliptin|insulin|voglibose|dapagliflozin"),
    ("Pain & fever", r"paracetamol|diclofenac|aceclofenac|ibuprofen|nimesulide|tramadol|mefenamic|etoricoxib"),
    ("Stomach & acidity", r"pantoprazole|rabeprazole|omeprazole|esomeprazole|domperidone|ranitidine|ondansetron|famotidine"),
    ("Allergy & cough", r"cetirizine|levocetirizine|montelukast|chlorphen|dextromethorphan|ambroxol|fexofenadine|cough"),
    ("Vitamins & supplements", r"vitamin|calcium|iron|folic|zinc|multivit|methylcobalamin|cholecalciferol|ferrous"),
    ("IV fluids", r"sodium chloride|dextrose|ringer|glucose"),
    ("Steroids", r"dexamethasone|prednisolone|methylpred|betamethasone|hydrocortisone"),
    ("Mental health & sleep", r"alprazolam|clonazepam|lorazepam|sertraline|escitalopram|fluoxetine|olanzapine"),
]


def form_of(product: str) -> str:
    p = (product or "").lower()
    return next((f for f, pat in FORMS if re.search(pat, p)), "Other")


def group_of(product: str) -> str:
    p = (product or "").lower()
    return next((g for g, pat in GROUPS if re.search(pat, p)), "Other")


def national(conn) -> dict:
    rows = conn.execute("SELECT product_name, reason, category, reported_by, alert_month, source FROM alerts").fetchall()
    by_state, by_fail, by_form, by_group, by_year, critical = {}, {}, {}, {}, {}, []
    for r in rows:
        st = state_of(r["reported_by"])
        if st:
            by_state[st] = by_state.get(st, 0) + 1
        fails = failures_of(r["reason"], r["category"])
        for f in fails:
            by_fail[f["key"]] = by_fail.get(f["key"], 0) + 1
        by_form[form_of(r["product_name"])] = by_form.get(form_of(r["product_name"]), 0) + 1
        g = group_of(r["product_name"])
        by_group[g] = by_group.get(g, 0) + 1
        y = r["alert_month"][:4]
        by_year[y] = by_year.get(y, 0) + 1
        if fails[0]["severity"] == "critical":
            critical.append({"product_name": r["product_name"], "reason": r["reason"], "month": r["alert_month"], "type": fails[0]["label"]})
    srt = lambda d: [{"name": k, "n": v} for k, v in sorted(d.items(), key=lambda x: -x[1])]
    return {
        "total": len(rows),
        "by_state": srt(by_state),
        "by_failure": [{"key": k, "name": LABEL[k], "n": v, "severity": next((s for kk, _, s, _, _ in FAILURES if kk == k), "medium")} for k, v in sorted(by_fail.items(), key=lambda x: -x[1])],
        "by_form": srt(by_form),
        "by_group": srt(by_group),
        "by_year": [{"name": k, "n": v} for k, v in sorted(by_year.items())],
        "critical_recent": sorted(critical, key=lambda c: c["month"], reverse=True)[:8],
        "critical_total": len(critical),
    }
