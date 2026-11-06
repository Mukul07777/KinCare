"""Batch matcher: exact batch match + fuzzy manufacturer/brand support.

Fuzziness is only ever applied to names, never to batch numbers, so a
near-miss batch can never produce a false alarm.
"""
import re

from rapidfuzz import fuzz

_STRIP = re.compile(r"[\s\-/.\\_]")
# Strip only legal forms. Words like "Pharma" or "Labs" distinguish companies
# ("Apple Formulations" vs "Apple Remedies"), so they stay.
_MAKER_NOISE = re.compile(r"^\s*m/s\.?|\b(pvt|private|ltd|limited|inc|co|company|llp|corp|corporation|as labelled)\b|[().,&]")

_UNKNOWN_MAKER = re.compile(r"under investigation|not known|unknown|^-$|^na$", re.I)
# Industry words most makers share. They keep different firms apart in normalise_maker, but they must not carry a
# fuzzy match: "Biodeal Pharmaceuticals" vs "Sakthi Ayurveda Pharmaceuticals" scored 88 on them alone.
_GENERIC = re.compile(
    r"\b(pharmaceuticals?|pharma|laborator(y|ies)|labs?|health ?care|life ?sciences?|sciences?|remedies|formulations?|"
    r"drugs?|bio ?tech|biotech|medicare|industries|international|india|products|mfg|manufactured|marketed|by|for|and|the)\b|[^a-z0-9 ]"
    # long industry words glued on by OCR ("hemalaboratories", "mmghealthcare"); short ones like "lab" stay word-bound
    r"|pharmaceuticals?|laborator(y|ies)|healthcare|lifesciences?|formulations?|remedies|medicare")

MAKER_THRESHOLD = 80
BRAND_THRESHOLD = 75


def _name_score(a: str, b: str, norm) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    # partial_ratio copes with OCR gluing words ("glenmarkpharmaceuticals").
    return max(fuzz.token_set_ratio(a, b), fuzz.partial_ratio(a, b) if min(len(a), len(b)) >= 5 else 0)


def _maker_score(a: str, b: str) -> float:
    """Full-name similarity, capped by the similarity of the distinctive words (generic industry words removed)."""
    full = _name_score(a, b, normalise_maker)
    core = lambda s: " ".join(_GENERIC.sub(" ", normalise_maker(s)).split())  # noqa: E731
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return full  # a name that is only generic words: nothing better to compare
    # partial_ratio again for OCR-glued words ("glenmarkpharmaceuticals" still contains "glenmark")
    distinct = max(fuzz.token_set_ratio(ca, cb), fuzz.partial_ratio(ca, cb) if min(len(ca), len(cb)) >= 5 else 0)
    return min(full, distinct)


def normalise_batch(batch: str) -> str:
    return _STRIP.sub("", batch or "").upper()


# Characters OCR swaps on foil: O/0, I/1, S/5, B/8, Z/2. Used only to raise a "possible" match for the user to check.
_LOOKALIKE = str.maketrans("OISBZ", "01582")
LOOKALIKE_SQL = "replace(replace(replace(replace(replace(batch_norm,'O','0'),'I','1'),'S','5'),'B','8'),'Z','2')"


def lookalike(batch: str) -> str:
    return normalise_batch(batch).translate(_LOOKALIKE)


def normalise_maker(name: str) -> str:
    return " ".join(_MAKER_NOISE.sub(" ", (name or "").lower()).split())


def score(alert: dict, batch: str, maker: str | None, brand: str | None) -> dict | None:
    """Return a score breakdown if the batch matches exactly, else None."""
    exact = normalise_batch(alert["batch_no"]) == normalise_batch(batch)
    if not exact and lookalike(alert["batch_no"]) != lookalike(batch):
        return None

    alert_maker = alert.get("manufacturer") or ""
    # Spurious lists often name no real maker ("Under Investigation"): skip the maker check then.
    maker_known = alert_maker and not _UNKNOWN_MAKER.search(alert_maker)
    maker_score = _maker_score(alert_maker, maker) if maker and maker_known else None
    brand_score = (
        max(_name_score(alert.get("brand") or "", brand, str.lower), _name_score(alert["product_name"], brand, str.lower))
        if brand else None
    )

    if not exact:
        level = "possible"  # same batch only if a 0 is really an O (etc.): never claimed as certain
    elif maker_score is not None and maker_score >= MAKER_THRESHOLD:
        level = "strong"
    elif brand_score is not None and brand_score >= BRAND_THRESHOLD:
        level = "strong" if maker_score is None else "possible"
    else:
        level = "possible"

    return {
        "level": level,
        "batch": 100 if exact else 90,
        "lookalike": not exact,
        "maker": maker_score,
        "brand": brand_score,
    }


def match(alerts: list[dict], batch: str, maker: str | None = None, brand: str | None = None) -> list[dict]:
    results = []
    for alert in alerts:
        s = score(alert, batch, maker, brand)
        if s:
            results.append({"alert": alert, "score": s})
    results.sort(key=lambda r: r["score"]["level"] != "strong")
    return results
