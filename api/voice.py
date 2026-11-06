"""Dadi mode: a spoken question in Hindi (or English) -> a short spoken answer from KinCare's real data.

Understands five things: a batch check, a price ("kitne ki aati hai"), what a medicine is for,
today's doses, and an emergency (always first: call 108). Browser speech recognition writes brand
names in Devanagari ("डोलो"), so they are transliterated and matched loosely against brand names.
KinCare never tells anyone to start, stop or change a medicine.
"""
import re

from rapidfuzz import fuzz

import prices

# ---- Devanagari -> rough Latin, good enough to find "डोलो" -> dolo, "टेल्मा" -> telma ----
_V = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri", "ऑ": "o"}
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri", "ॉ": "o", "ॅ": "e"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
      "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
      "प": "p", "फ": "f", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
      "ष": "sh", "स": "s", "ह": "h", "क़": "k", "ज़": "z", "फ़": "f", "ड़": "d", "ढ़": "rh"}
_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def translit(text: str) -> str:
    out, chars = [], list(text.translate(_DIGITS))
    for i, ch in enumerate(chars):
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch in _C:
            out.append(_C[ch])
            # Inherent "a" unless a vowel sign, a virama or the end of the word follows. Hindi also drops it in
            # the middle of a word before a consonant that carries a vowel sign: थायरो -> "thayro", not "thayaro".
            nxt2 = chars[i + 2] if i + 2 < len(chars) else ""
            prev = chars[i - 1] if i else ""
            mid_drop = nxt in _C and nxt2 in _M and (prev in _M or prev in _V)
            if nxt not in _M and nxt != "्" and nxt not in ("ं", "ँ") and nxt and re.match(r"[ऀ-ॿ]", nxt) and not mid_drop:
                out.append("a")
        elif ch in _M:
            out.append(_M[ch])
        elif ch in _V:
            out.append(_V[ch])
        elif ch in ("ं", "ँ"):
            out.append("n")
        elif ch in ("्", "़", "ः"):
            continue
        else:
            out.append(ch)
    return "".join(out).lower()


# ---- what the question is about ----
def _has(t: str, *words: str) -> bool:
    return any(w in t for w in words)


EMERGENCY = ("साँस", "सांस", "saans", "sans nahi", "chest pain", "सीने", "seene", "behosh", "बेहोश", "unconscious", "खून बह", "khoon",
             "emergency", "इमरजेंसी", "heart attack", "हार्ट अटैक", "दौरा", "breath", "can't breathe", "faint")
DOSES = ("aaj", "आज", "today", "kaunsi", "कौन सी", "कौनसी", "agli", "अगली", "next dose", "meri dawai", "मेरी दवा", "kab leni", "कब लेनी", "khurak", "खुराक")
PRICE = ("kitne", "कितने", "kitna", "कितना", "कितनी", "keemat", "कीमत", "daam", "दाम", "sasta", "सस्ता", "सस्ती", "price", "cost", "cheap", "rate", "रेट", "how much")
GREETING = re.compile(r"^\s*(hi|hii+|hello|hey|namaste|namaskar|नमस्ते|नमस्कार|राम राम|ram ram|pranam|प्रणाम)\b[\s!.?]*$", re.I)
USES = ("kis liye", "किस लिए", "किसलिए", "kya kaam", "क्या काम", "kis kaam", "किस काम", "use", "uses", "what is", "kya hai", "क्या है", "kyon", "क्यों", "for what")
STOP = {"kitne", "kitna", "kitni", "ki", "ka", "ke", "ko", "hai", "he", "h", "aati", "ati", "aata", "milti", "milta", "keemat", "daam", "dam", "kya", "kis", "liye", "lie",
        "kaam", "sasta", "sasti", "price", "cost", "of", "the", "is", "what", "how", "much", "for", "a", "meri", "mera", "dawai", "dawa", "dava", "davai", "goli",
        "tablet", "tablets", "batao", "bataiye", "bataen", "please", "kripya", "ye", "yeh", "wo", "woh", "mein", "me", "se", "aur", "rate", "uses", "use",
        "cheap", "cheapest", "sabse", "kaun", "si", "konsi", "kaunsi", "acchi", "achi", "hoti", "hota", "kyon", "kyu", "and", "my", "medicine", "about", "tell",
        "kahan", "lena", "leni", "chahiye", "sahi", "theek", "safe", "check", "batch", "number", "nambar", "kitane", "kitana", "aatee", "hain", "kee", "kaa"}
BATCH_TOKEN = re.compile(r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9][A-Z0-9-]{3,15}\b", re.I)

# Common uses of frequent salts, in plain Hindi / English. General information, not advice.
USE_HI = [
    (("telmisartan", "amlodipine", "losartan", "olmesartan", "metoprolol", "atenolol", "ramipril", "cilnidipine", "nebivolol"), "ब्लड प्रेशर (BP)", "blood pressure"),
    (("metformin", "glimepiride", "sitagliptin", "vildagliptin", "voglibose", "gliclazide", "teneligliptin", "dapagliflozin", "empagliflozin"), "शुगर (डायबिटीज़)", "diabetes (sugar)"),
    (("paracetamol",), "बुखार और दर्द", "fever and pain"),
    (("ibuprofen", "diclofenac", "aceclofenac", "nimesulide", "etoricoxib", "naproxen"), "दर्द और सूजन", "pain and swelling"),
    (("atorvastatin", "rosuvastatin"), "कोलेस्ट्रॉल", "cholesterol"),
    (("aspirin", "clopidogrel"), "खून पतला रखने, दिल की सुरक्षा", "keeping blood thin, heart protection"),
    (("warfarin", "apixaban", "rivaroxaban", "dabigatran"), "खून पतला करने", "thinning the blood"),
    (("pantoprazole", "omeprazole", "rabeprazole", "esomeprazole", "ranitidine", "famotidine"), "एसिडिटी और गैस", "acidity and heartburn"),
    (("levothyroxine", "thyroxine"), "थायरॉइड", "thyroid"),
    (("cetirizine", "levocetirizine", "fexofenadine", "montelukast", "chlorpheniramine"), "एलर्जी, छींक, नाक बहना", "allergy and sneezing"),
    (("amoxycillin", "amoxicillin", "azithromycin", "cefixime", "ciprofloxacin", "doxycycline", "ofloxacin", "cefuroxime", "cefpodoxime"), "बैक्टीरिया का इन्फेक्शन (एंटीबायोटिक)", "bacterial infection (antibiotic)"),
    (("ondansetron", "domperidone"), "उल्टी और जी मिचलाना", "nausea and vomiting"),
    (("alprazolam", "clonazepam", "lorazepam"), "घबराहट और नींद (सिर्फ़ डॉक्टर की पर्ची से)", "anxiety and sleep (prescription only)"),
    (("calcium", "cholecalciferol", "vitamin"), "कैल्शियम और विटामिन की कमी", "calcium and vitamin deficiency"),
]


def common_use(salts: str) -> tuple[str, str] | None:
    s = salts.lower()
    return next(((hi, en) for keys, hi, en in USE_HI if any(k in s for k in keys)), None)


def sound(word: str) -> str:
    """Spelling -> rough sound, so 'Crocin' and the transliterated 'krosin' compare equal."""
    w = word.lower().replace("ph", "f").replace("ck", "k").replace("q", "k").replace("w", "v").replace("z", "j").replace("x", "ks")
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    w = re.sub(r"(.)\1", r"\1", w)  # doubled letters: "Glycomett" ~ "glikomet"
    return w.replace("y", "i").replace("ee", "i").replace("oo", "u")


def find_medicine(conn, latin: str) -> dict | None:
    """The brand the question names. Words left after removing question words; number = strength."""
    words = [w for w in re.findall(r"[a-z0-9]+", latin) if w not in STOP and len(w) > 1]
    if not words:
        return None
    names = [w for w in words if not w.isdigit()]
    nums = [w for w in words if w.isdigit()]
    if not names:
        return None
    # The brand's first word, compared by sound ("krosin" = Crocin, "ikosprin" = Ecosprin, "pain" ~ Pan), so a
    # word buried inside another name ("Gaso-pain") never wins. Then: has the spoken strength, is a tablet, shortest.
    head = sound(names[0])
    # ऐ in an English loanword is usually a plain "a" (पैन = Pan, टैब = Tab), so try both spellings.
    heads = {head, head.replace("ai", "a")}
    firsts = "aeiou" if head[:1] in "aeiou" else {"k": "kcq", "s": "sc", "f": "fp", "v": "vw", "j": "jgz", "g": "gj"}.get(head[:1], head[:1])
    cands = conn.execute(f"SELECT id, name_lc, form, salts FROM medicines WHERE {' OR '.join(['name_lc LIKE ?'] * len(firsts))} LIMIT 60000",
                         [c + "%" for c in firsts]).fetchall()
    # The spoken strength can sit in the name ("Dolo 650") or only in the salt ("Amlong" = amlodipine 5mg).
    strength = re.compile(rf"(?<![\d.]){re.escape(nums[0])}(?![\d.])") if nums else None
    scored = []
    for r in cands:
        sim = max(fuzz.ratio(h, sound(re.split(r"[\s-]", r["name_lc"])[0])) for h in heads)
        if sim >= 78:
            has = 0 if not strength else 2 if strength.search(r["name_lc"]) else 1 if strength.search(r["salts"]) else 0
            scored.append((has, sim, r["form"] == "tablet", -len(r["name_lc"]), r["id"]))
    best = max(scored, default=None)
    return prices._row(conn, conn.execute("SELECT * FROM medicines WHERE id = ?", (best[4],)).fetchone()) if best else None


def rupees(v: float | None) -> str:
    return "-" if v is None else f"₹{v:.2f}" if v < 10 else f"₹{v:.1f}"


def answer(conn, text: str, lang: str, run_check, today: dict | None) -> dict:
    """{kind, say, show, data}. `say` is short and speakable; `show` can carry more."""
    hi = lang == "hi"
    raw = text.strip()
    t = raw.lower()
    latin = translit(t)
    both = f"{t} {latin}"

    if _has(both, *EMERGENCY):
        say = ("अभी 108 पर फ़ोन करें। अगर साँस, सीने में दर्द या बेहोशी है तो देर मत कीजिए। नीचे का लाल बटन परिवार को आपकी लोकेशन भेज देगा।"
               if hi else "Call 108 now. With breathing trouble, chest pain or fainting, don't wait. The red button below sends your family your location.")
        return {"kind": "emergency", "say": say, "show": say, "data": {}}

    if GREETING.match(raw):
        say = ("नमस्ते! मैं KinCare हूँ। आप मुझसे दवा की कीमत, वो किस लिए है, आज कौन सी दवा लेनी है, या बैच नंबर के बारे में पूछ सकती हैं।"
               if hi else "Hello! I'm KinCare. Ask me a medicine's price, what it's for, today's doses, or about a batch number.")
        return {"kind": "hello", "say": say, "show": say, "data": {}}

    m = BATCH_TOKEN.search(raw)
    if m and not _has(both, *PRICE, *USES):
        batch = m.group(0).upper()
        chk = run_check(batch, None, None)
        if chk["matches"]:
            a = chk["matches"][0]["alert"]
            kind = "नकली (spurious)" if a["category"] == "spurious" else "घटिया (NSQ, जाँच में फेल)"
            say = (f"सावधान। बैच {batch}, {a['product_name']}, सरकारी लिस्ट में {kind} बताया गया है। यह दवा अभी मत लीजिए, केमिस्ट या डॉक्टर को दिखाइए।"
                   if hi else f"Careful. Batch {batch}, {a['product_name']}, is on the regulator's {a['category'].upper()} list. Show it to your chemist or doctor before the next dose.")
            return {"kind": "batch_alert", "say": say, "show": say, "data": {"batch": batch, "alert": a}}
        say = (f"बैच {batch} किसी भी सरकारी अलर्ट लिस्ट में नहीं है, आज तक। एक्सपायरी डेट भी देख लीजिए।"
               if hi else f"Batch {batch} is not on any regulator alert list, as of today. Check the expiry date too.")
        return {"kind": "batch_clean", "say": say, "show": say, "data": {"batch": batch}}

    if _has(both, *DOSES) and today is not None:
        pending = [d for d in today["doses"] if not d["taken_at"]]
        if not today["doses"]:
            say = "अभी कोई पर्ची सेव नहीं है। केयर में डॉक्टर की पर्ची स्कैन कर लीजिए।" if hi else "No prescription saved yet. Scan the doctor's prescription in Care."
        elif not pending:
            say = "आज की सारी दवाइयाँ ले ली गई हैं। शाबाश!" if hi else "All of today's doses are taken. Well done!"
        else:
            parts = [f"{d['time']} बजे {d['member']} की {d['name']}" if hi else f"{d['name']} for {d['member']} at {d['time']}" for d in pending[:3]]
            say = ("अभी बाकी हैं: " + ", ".join(parts) + "। दवा लेने के बाद केयर में टिक कर दीजिए।") if hi else ("Still to take: " + ", ".join(parts) + ".")
        return {"kind": "doses", "say": say, "show": say, "data": {"pending": pending[:6]}}

    med = find_medicine(conn, latin)
    if med and _has(both, *PRICE):
        alt = prices.alternatives(conn, med["id"], limit=0)
        best = alt["cheapest_clean"] if alt else None
        if best and best["unit_price"] and med["unit_price"] and best["unit_price"] < med["unit_price"]:
            say = (f"{med['name']} की एक गोली लगभग {rupees(med['unit_price'])} की है। इसी नमक की सबसे सस्ती, साफ़ रिकॉर्ड वाली दवा {best['name']} है, {rupees(best['unit_price'])} की एक गोली। बदलने से पहले डॉक्टर या केमिस्ट से पूछिए।"
                   if hi else f"{med['name']} costs about {rupees(med['unit_price'])} a tablet. The cheapest same-salt brand from a maker with no alerts is {best['name']}, {rupees(best['unit_price'])} a tablet. Ask your doctor or chemist before switching.")
        else:
            say = (f"{med['name']} की एक गोली लगभग {rupees(med['unit_price'])} की है। यह पहले से सबसे सस्ती दवाओं में है।"
                   if hi else f"{med['name']} costs about {rupees(med['unit_price'])} a tablet, already among the cheapest for this salt.")
        return {"kind": "price", "say": say, "show": say, "data": {"medicine": med, "cheapest": best}}

    if med:
        use = common_use(med["salts"])
        alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE lower(product_name) LIKE ?", (f"%{med['salts'].split('(')[0].strip().lower()}%",)).fetchone()[0]
        if hi:
            say = f"{med['name']} में {med['salts']} है।" + (f" यह आमतौर पर {use[0]} के लिए दी जाती है।" if use else "") + " दवा डॉक्टर के बताए अनुसार ही लीजिए।"
            if alerts:
                say += f" इस नमक के {alerts} सैंपल सरकारी जाँच में फेल हुए हैं, इसलिए अपना बैच स्कैन कर लीजिए।"
        else:
            say = f"{med['name']} contains {med['salts']}." + (f" It is commonly used for {use[1]}." if use else "") + " Take it only as your doctor advised."
            if alerts:
                say += f" {alerts} samples of this salt failed government tests, so scan your batch."
        return {"kind": "uses", "say": say, "show": say, "data": {"medicine": med, "common_use": use and (use[0] if hi else use[1]), "salt_alerts": alerts}}

    say = ("मैं ये बता सकती हूँ: किसी दवा की कीमत, वो किस लिए है, आज कौन सी दवा लेनी है, या बैच नंबर सही है या नहीं। जैसे पूछिए: डोलो 650 कितने की आती है?"
           if hi else "I can tell you a medicine's price, what it's for, which doses are due today, or whether a batch is flagged. Try: how much is Dolo 650?")
    return {"kind": "help", "say": say, "show": say, "data": {}}


# ---- chat actions: things Dadi can *do*, not just answer ----
# Whole words only: "le lijiye" (please take it) is not "le li", "betadine" is not "beta", "abandoned" is not "done".
def _words(*ws: str) -> re.Pattern:
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in ws) + r")(?!\w)", re.I)


TAKEN = _words("le li", "le liya", "le lee", "kha li", "kha liya", "khaa li", "ले ली", "ले लिया", "खा ली", "खा लिया", "took", "taken", "have taken", "done")
FAMILY = _words("beta", "बेटा", "beti", "बेटी", "bete", "बेटे", "bahu", "बहू", "family", "परिवार", "parivar", "ghar wale", "ghar walon", "घर वाले", "घर वालों",
                "call my", "bulao", "बुलाओ", "bula do", "बुला दो", "baat karni", "बात करनी", "phone karo", "फ़ोन करो", "फोन करो", "message karo", "मैसेज करो",
                "tell my", "caregiver")
# "BP 140/90", "बीपी 140 बटा 90", "pulse 82", "oxygen 96", "bukhar 101" / "temperature 38.5"
_BP = re.compile(r"(?:bp|b\.p|बीपी|blood pressure|pressure|प्रेशर)\D{0,12}(\d{2,3})\s*(?:/|by|बटा|bata|over|ऊपर|upar|-)\s*(\d{2,3})", re.I)
_PULSE = re.compile(r"(?:pulse|नब्ज़|नब्ज|nabz|heart rate|धड़कन|dhadkan)\D{0,10}(\d{2,3})", re.I)
_SPO2 = re.compile(r"(?:oxygen|ऑक्सीजन|spo2|sp02|saturation)\D{0,10}(\d{2,3})", re.I)
_TEMP = re.compile(r"(?:temp(?:erature)?|बुखार|bukhar|बुख़ार|fever|तापमान|taapmaan)\D{0,10}(\d{2,3}(?:\.\d)?)", re.I)


def is_taken(text: str) -> bool:
    t = text.lower()
    return bool(TAKEN.search(t) or TAKEN.search(translit(t))) and not _has(t, "?", "kya", "क्या", "kab", "कब")


def is_family(text: str) -> bool:
    t = text.lower()
    return bool(FAMILY.search(t) or FAMILY.search(translit(t)))


def vitals_in(text: str) -> dict:
    """Readings said out loud. Temperatures above 45 are Fahrenheit (Indian thermometers mostly are)."""
    t = text.translate(_DIGITS)
    out: dict = {}
    if m := _BP.search(t):
        out["bp_sys"], out["bp_dia"] = int(m.group(1)), int(m.group(2))
    if m := _PULSE.search(t):
        out["pulse"] = int(m.group(1))
    if m := _SPO2.search(t):
        out["spo2"] = int(m.group(1))
    if m := _TEMP.search(t):
        v = float(m.group(1))
        out["temp_c"] = round((v - 32) * 5 / 9, 1) if v > 45 else v
    return out
