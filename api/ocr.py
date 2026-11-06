"""Read a medicine strip photo with a local OCR model and pull out label fields.

RapidOCR (PaddleOCR models on ONNX Runtime) runs on CPU with no API key.
Field extraction is rule-based so every value can be traced to an OCR line.
"""
import re
from functools import lru_cache

import numpy as np

# OCR often reads the "o" of "No." as a zero ("B.N0."). A 0 counts as that "o" only when "." ":" or a space
# follows, so the leading zero of "B.N05240198" stays part of the batch.
_NO = r"N(?:o|O|0(?=[.:\s]))"
BATCH_RE = re.compile(rf"\b(?:B\.?\s*{_NO}?\.?|BATCH\s*(?:{_NO}\.?)?|LOT\s*(?:{_NO}\.?)?)\s*[:.\-]?\s*([A-Z0-9][A-Z0-9\-/]{{2,15}})", re.I)
EXP_RE = re.compile(r"(?<![A-Z])(?:E?XP(?:IRY)?|USE\s*BEFORE|E\.?D\.?)\.?\s*(?:DATE)?\s*[:.\-]?\s*((?:\d{1,2}\s*[/\-.]\s*\d{2,4})|(?:[A-Z]{3}\.?\s*[/\-.]?\s*\d{2,4}))", re.I)
MFG_RE = re.compile(r"\b(?:MFG|MFD|MANUF\w*|M\.?\s*D\.?)\.?\s*(?:DATE|DT)?\.?\s*[:.\-]?\s*((?:\d{1,2}\s*[/\-.]\s*\d{2,4})|(?:[A-Z]{3}\.?\s*[/\-.]?\s*\d{2,4}))", re.I)
MAKER_LABEL_RE = re.compile(r"(?:MFD\.?|MANUFACTURED|MARKETED|MKTD\.?)\s*BY\s*[:.\-]?\s*(.*)", re.I)
COMPANY_RE = re.compile(r"\b(LTD|LIMITED|PVT|PRIVATE|PHARMA\w*|LABORATORIES|LABS|HEALTHCARE|LIFESCIENCES?)\b", re.I)
# "No. DOB5480" with the "B." cut off at the strip edge; never "Mfg. Lic. No." or "Regd. No.".
BARE_NO_RE = re.compile(r"(?<![A-Z])N[O0]\s*[.:]\s*([A-Z0-9]{4,14})(?![A-Z0-9/])", re.I)
_NOT_BATCH_BEFORE = re.compile(r"(?:LIC|LICENCE|LICENSE|REGD?|REG\.?)\W*$", re.I)
LABEL_ONLY_RE = re.compile(r"^(?:B\.?\s*N[O0]\.?|BATCH\s*(?:N[O0]\.?)?|LOT\s*(?:N[O0]\.?)?)\s*[:.\-]?$", re.I)


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def read_lines(image_bytes: bytes, long_side: int = 2000) -> list[dict]:
    import cv2

    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    # Camera photos are 4000 px+ (slow), WhatsApp sends 1280 px (thin edge print like "B.No.JCHT6539" goes undetected):
    # bring both to about 2000 px on the long side.
    scale = long_side / max(img.shape[:2])
    if abs(scale - 1) > 0.05:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    result, _ = _engine()(img)
    lines = []
    for box, text, conf in result or []:
        ys, xs = [p[1] for p in box], [p[0] for p in box]
        lines.append({"text": text.strip(), "conf": float(conf), "height": max(ys) - min(ys), "top": min(ys), "left": min(xs)})
    lines.sort(key=lambda l: (l["top"], l["left"]))

    # Merge boxes on the same visual line ("Telma" + "H" -> "Telma H").
    merged: list[dict] = []
    for l in lines:
        prev = merged[-1] if merged else None
        if prev and abs(l["top"] - prev["top"]) < 0.5 * min(l["height"], prev["height"]):
            prev["text"] += " " + l["text"]
            prev["conf"] = min(prev["conf"], l["conf"])
            prev["height"] = max(prev["height"], l["height"])
        else:
            merged.append(dict(l))
    return merged


# ---- clean-up of what OCR reads on real foil: glued words, letter swaps, boilerplate ----

# Packaging text that sits next to the maker's name but is not part of it.
_MAKER_NOISE = re.compile(
    r"\b(?:regd\.?|registered|trade\s*mark(?:s)?(?:\s*(?:proprietor|owner|of))?|tm|®|™|marketed\s*by|mfd\.?\s*by|manufactured\s*by|"
    r"mkt\.?\s*by|distributed\s*by|an\s+iso\s*\d*\s*certified\s*company)\b\.?", re.I)
_SUFFIX = {"ltd": "Ltd", "pvt": "Pvt", "llp": "LLP", "inc": "Inc"}


def tidy_maker(name: str | None) -> str | None:
    """'MICRO LABS Trade Mark Proprietor' -> 'Micro Labs'. Shouting capitals become Title Case; acronyms of 2-3 letters stay."""
    if not name:
        return name
    t = _MAKER_NOISE.sub(" ", name.replace("®", " ").replace("™", " "))
    t = re.split(r",|\s-\s|\bat\b|\bplot\b|\bsurvey\b|contact|e-?mail|@|\bsec(?:tor|lor)\b|\d", t, flags=re.I)[0]  # an address often follows
    t = " ".join(t.split()).strip(" .:-")
    if t.isupper():
        t = " ".join(_SUFFIX.get(w.lower().strip("."), w if len(w) <= 3 else w.capitalize()) for w in t.split())
    return t or None


# Dosage-form words that OCR glues to the salt name ("ParacetamolTabletsIP") or misreads ("Tableis").
_FORMS = {"tablets": "Tablets", "tablet": "Tablet", "capsules": "Capsules", "capsule": "Capsule", "syrup": "Syrup",
          "injection": "Injection", "suspension": "Suspension", "ointment": "Ointment", "cream": "Cream", "drops": "Drops", "gel": "Gel"}
_FORM_FIX = {"tableis": "tablets", "tabiets": "tablets", "tablcts": "tablets", "tabtets": "tablets", "tabels": "tablets", "lablets": "tablets",
             "capsuies": "capsules", "capsulcs": "capsules"}


@lru_cache(maxsize=1)
def salt_words() -> frozenset:
    """Single-word salt names from the medicine dataset (paracetamol, telmisartan, ...). Empty before the first ingest."""
    import sqlite3

    from db import DB_PATH

    try:
        c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows = c.execute("SELECT DISTINCT salts FROM medicines").fetchall()
        c.close()
    except sqlite3.Error:
        return frozenset()
    out = set()
    for (s,) in rows:
        for w in re.findall(r"[a-z]{5,}", (s or "").lower()):
            out.add(w)
    return frozenset(out)


def tidy_brand(text: str | None, vocab: frozenset | None = None) -> str | None:
    """'aracelamolTableisIP' -> 'Paracetamol Tablets IP'.

    Only for a generic-name line, the way a plain strip prints its salt ("Paracetamol Tablets IP"): once un-glued it holds a
    dosage-form word or IP / BP / USP. Brand names ("Bacfen", "Mytrip", "DavaIndia") are returned exactly as read: on 20,000
    real brand names, correcting everything renamed 3.35% of them (Bacfen -> Baclofen), which is worse than a typo.

    1. Split words OCR glued together (before a capital, before a form word, IP / BP / USP after a form word).
    2. Fix common misreadings of form words ("Tableis" -> "Tablets").
    3. Snap a misread salt to the closest real salt name when it is a near match (ratio >= 85), e.g. a lost first letter."""
    if not text:
        return text
    from rapidfuzz import fuzz, process

    vocab = salt_words() if vocab is None else vocab
    forms = sorted(set(_FORMS) | set(_FORM_FIX), key=len, reverse=True)
    form_alt = "|".join(forms)
    # "gel", "drops", "cream" often end a brand ("Mucogel", "Softdrops"): only long form words are split off a glued word
    glue_alt = "|".join(f for f in forms if len(f) >= 6)
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)                                  # camelCase glue
    t = re.sub(rf"(?i)(?<=[a-z])(?=(?:{glue_alt})(?:ip|bp|usp)?\b)", " ", t)        # ParacetamolTablets
    t = re.sub(rf"(?i)\b({form_alt})(ip|bp|usp)\b", r"\1 \2", t)                     # TabletsIP
    if not re.search(rf"(?i)\b(?:{form_alt}|ip|bp|usp)\b", t):
        return text  # not a generic-name line: a brand, keep it exactly
    for bad, good in _FORM_FIX.items():
        t = re.sub(rf"(?i)\b{bad}\b", _FORMS[good], t)
    # Salt names are corrected only on a pharmacopoeia line ("... Tablets IP"): a brand line such as "Inderal Tablets"
    # would otherwise become "Mineral Tablets".
    pharmacopoeia = bool(re.search(r"(?i)\b(?:ip|bp|usp)\b", t))
    if not pharmacopoeia:
        return text  # a brand line ("StayHappi ... Tablet"): exactly as read
    words = []
    for w in t.split():
        lw = w.lower()
        if lw in _FORMS:
            words.append(w)  # read correctly: keep it as printed ("CAPSULE" stays)
        elif lw in ("ip", "bp", "usp"):
            words.append(lw.upper())
        elif pharmacopoeia and vocab and len(lw) >= 5 and lw.isalpha() and lw not in vocab:
            hit = process.extractOne(lw, vocab, scorer=fuzz.ratio, score_cutoff=85)
            words.append(hit[0].capitalize() if hit else w)
        elif pharmacopoeia and vocab and lw in vocab and w.islower():
            words.append(w.capitalize())
        else:
            words.append(w)
    out = " ".join(words)
    return text if out == " ".join(text.split()) else out  # nothing fixed: keep the original exactly


# Words of warning, dosage and price lines that sit in large type but are never the brand.
_NOT_BRAND = re.compile(r"\b(?:from|contains?|warning|important|overdose|injurious|liver|taxes|incl|mrp|per|tablets?\s+ip|"
                        r"physician|doctor|pregnancy|children|relief|pain|effervescent|dissolves?|reach|caution)\b|[()（）]", re.I)
# What OCR glues onto the end of a batch number: the next field's label ("DFNY0223MFG").
_BATCH_TAIL = re.compile(r"(?:MFG|MFD|EXP|MRP|DATE)$", re.I)


def clean_batch(b: str) -> str:
    """'DFNY0223MFG' -> 'DFNY0223'; 'D0BS4480' -> 'DOBS4480' (a zero between two letters is the letter O)."""
    b = b.upper().strip("-/")
    t = _BATCH_TAIL.sub("", b)
    if len(t) >= 3 and any(c.isdigit() for c in t):
        b = t
    return re.sub(r"(?<=[A-Z])0(?=[A-Z])", "O", b)


def extract_fields(lines: list[dict]) -> dict:
    texts = [l["text"] for l in lines]
    joined = "\n".join(texts)
    fields = {"batch": None, "expiry": None, "mfg_date": None, "maker": None, "brand": None}
    conf = {}

    for i, t in enumerate(texts):
        if not fields["batch"]:
            m = BATCH_RE.search(t)
            if m:
                fields["batch"], conf["batch"] = m.group(1).upper(), lines[i]["conf"]
            elif LABEL_ONLY_RE.match(t) and i + 1 < len(texts):
                fields["batch"], conf["batch"] = texts[i + 1].split()[0].upper(), lines[i + 1]["conf"]
        if not fields["maker"]:
            m = MAKER_LABEL_RE.search(t)
            if m:
                name = m.group(1).strip() or (texts[i + 1] if i + 1 < len(texts) else "")
                fields["maker"] = name.split(",")[0].strip() or None

    if not fields["batch"]:
        for i, t in enumerate(texts):
            m = next((m for m in BARE_NO_RE.finditer(t) if not _NOT_BATCH_BEFORE.search(t[:m.start()])
                      and any(c.isdigit() for c in m.group(1))), None)
            if m:
                fields["batch"], conf["batch"] = m.group(1).upper(), lines[i]["conf"]
                break

    if fields["batch"]:
        fields["batch"] = clean_batch(fields["batch"])
    if m := EXP_RE.search(joined):
        fields["expiry"] = re.sub(r"\s+", "", m.group(1))
    if m := MFG_RE.search(joined):
        fields["mfg_date"] = re.sub(r"\s+", "", m.group(1))
    if not fields["maker"]:
        fields["maker"] = next((t.split(",")[0] for t in texts if COMPANY_RE.search(t)), None)
    fields["maker"] = tidy_maker(fields["maker"])

    # Brand: the tallest text that isn't a label field.
    skip = re.compile(r"\d{2}[/\-.]\d{2}|B\.?\s*N[O0]|BATCH|EXP|MFG|MFD|LTD|LIMITED|PVT|SCHEDULE|RX|DOSAGE|STORE|KEEP|MADE\s*IN|MFD\s*BY|MARKETED"
                      r"|\d{6,}|TOLL|FREE", re.I)
    # "Dol0-500" / "Dol6-500": a lone 0 or 6 between a word and its strength is the letter o.
    unzero = lambda s: re.sub(r"(?<=[A-Za-z]{2})[06](?=-\d{2,4}\b)", "o", s)
    # A brand is a short name, not a sentence of warning text that OCR read in a large font.
    candidates = [l for l in lines if len(l["text"]) >= 3 and not skip.search(l["text"]) and l["conf"] > 0.6
                  and len(l["text"]) <= 30 and len(l["text"].split()) <= 4 and not _NOT_BRAND.search(l["text"])]
    if candidates:
        best = max(candidates, key=lambda l: l["height"])
        fields["brand"], conf["brand"] = tidy_brand(unzero(best["text"])), best["conf"]
        # Strips repeat the brand all over the foil ("Dolo-650 Dolo-650 ..."): a name printed 3+ times is the brand.
        counts: dict[str, int] = {}
        for t in texts:
            for w in re.findall(r"[A-Za-z][A-Za-z]{2,}(?:-?\d{2,4})?", unzero(t)):
                counts[w.lower()] = counts.get(w.lower(), 0) + 1
        rep = [w for w in re.findall(r"[A-Za-z][A-Za-z]{2,}(?:-?\d{2,4})?", unzero(best["text"])) if counts[w.lower()] >= 3 and not skip.search(w)]
        if rep:
            fields["brand"] = max(rep, key=lambda w: (counts[w.lower()], len(w)))

    # A name with its strength ("PARACIP-500") printed twice or more is the brand, even when OCR merged it into a long line.
    named: dict[str, list[str]] = {}
    for t in texts:
        for w in re.findall(r"(?<![A-Za-z])[A-Za-z]{3,}-\d{2,4}\b", unzero(t)):
            if not skip.search(w):
                named.setdefault(w.lower(), []).append(w)
    if named:
        top = max(named.values(), key=len)
        if len(top) >= 2:
            fields["brand"] = max(set(top), key=top.count)

    return {"fields": fields, "confidence": conf}


TOKEN_RE = re.compile(r"(?<![A-Z0-9])[A-Z0-9][A-Z0-9\-/]{3,14}(?![A-Z0-9])")
NOT_BATCH = re.compile(r"^(?:\d{1,2}[/\-]\d{2,4}|300[34]\d{4}|\d{10,}|GST\w*|HSN\w*|\d+\.\d+)$")


def bill_candidates(lines: list[dict]) -> list[dict]:
    """Every token on a bill that could be a batch number, with the line it came from.
    Bills put product, batch, expiry and price on one row; we keep the row text so
    the user can see which medicine each candidate belongs to."""
    out, seen = [], set()
    for l in lines:
        for tok in TOKEN_RE.findall(l["text"].upper()):
            t = tok.strip("-/")
            has_digit, has_alpha = any(c.isdigit() for c in t), any(c.isalpha() for c in t)
            glued = re.search(r"\d[A-Z]{3,}", t)  # OCR-merged words like "NIMCEF200TAB", "4471DATE"
            if not has_digit or glued or NOT_BATCH.match(t) or (not has_alpha and not 5 <= len(t) <= 9) or t in seen:
                continue
            seen.add(t)
            out.append({"batch": t, "line": l["text"], "conf": l["conf"]})
    return out


def scan_bill(image_bytes: bytes) -> dict:
    lines = read_lines(image_bytes)
    return {"candidates": bill_candidates(lines), "lines": [l["text"] for l in lines]}


def _rotated(image_bytes: bytes, code: int) -> bytes:
    import cv2

    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    return cv2.imencode(".jpg", cv2.rotate(img, code))[1].tobytes()


def scan(image_bytes: bytes) -> dict:
    """Read the strip. Batch, expiry and MRP are often printed sideways along the edge: when the upright read finds
    no batch, read the photo turned 90 degrees each way and take the missing dates and batch from there."""
    import cv2

    lines = read_lines(image_bytes)
    out = extract_fields(lines)
    texts = [l["text"] for l in lines]
    for code in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE):
        if out["fields"]["batch"]:
            break
        side = read_lines(_rotated(image_bytes, code), long_side=2560)  # thin edge print needs more pixels
        got = extract_fields(side)
        for k in ("batch", "expiry", "mfg_date"):
            if not out["fields"][k] and got["fields"][k]:
                out["fields"][k] = got["fields"][k]
                if k in got["confidence"]:
                    out["confidence"][k] = got["confidence"][k]
        texts += ["(sideways) " + l["text"] for l in side]
    return {**out, "lines": texts}
