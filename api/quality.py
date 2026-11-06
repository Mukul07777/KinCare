"""Matcher accuracy, measured on the real alert table (not a hand-picked list).

Every probe goes through the same path as /api/check: candidate lookup by normalised batch, then the matcher.
  * positives  - real flagged batches, typed the ways people and OCR actually type them
                 (as printed, lower case, spaces, hyphens, slashes): every one must raise its alert
  * near-miss  - the same batch with one character changed (and not itself on any list): must raise nothing
  * clean      - realistic batch numbers that are on no list: must raise nothing
  * wrong maker- right batch, a different company: still shown (the batch is on the list) but never "strong"
Precision is the number that matters to a patient: a false alarm makes someone stop a medicine they need.
"""
import random
import re
import statistics
import string
import time
from typing import Callable

from matcher import match, normalise_batch

_cache: dict | None = None


def _variants(b: str, rnd: random.Random) -> list[str]:
    mid = max(1, len(b) // 2)
    return [b, b.lower(), f"{b[:mid]} {b[mid:]}", f"{b[:mid]}-{b[mid:]}", f" {b} ", f"{b[:mid]}/{b[mid:]}"]


def _mutate(b: str, rnd: random.Random) -> str:
    i = rnd.randrange(len(b))
    pool = string.digits if b[i].isdigit() else string.ascii_uppercase
    return b[:i] + rnd.choice([c for c in pool if c != b[i]]) + b[i + 1:]


def _clean(rnd: random.Random) -> str:
    fmt = rnd.choice(["AA0000", "AAA00000", "A0000AA", "0000AA00", "AA00A000"])
    return "".join(rnd.choice(string.ascii_uppercase) if c == "A" else rnd.choice(string.digits) for c in fmt)


def measure(conn, lookup: Callable[[str], list[dict]], n: int = 400, seed: int = 7) -> dict:
    rnd = random.Random(seed)
    known = {r[0] for r in conn.execute("SELECT DISTINCT batch_norm FROM alerts")}
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM alerts WHERE length(batch_norm) >= 4 AND manufacturer IS NOT NULL AND manufacturer != '' ORDER BY id")]
    sample = rnd.sample(rows, min(n, len(rows)))
    timings: list[float] = []

    def check(batch: str, maker: str | None = None):
        t = time.perf_counter()
        r = match(lookup(batch), batch, maker)
        timings.append((time.perf_counter() - t) * 1000)
        return r

    tp = fn = 0
    misses: list[str] = []
    for a in sample:
        for v in _variants(a["batch_no"].strip(), rnd):
            hit = any(m["alert"]["id"] == a["id"] for m in check(v))
            tp += hit
            fn += not hit
            if not hit and len(misses) < 5:
                misses.append(v)

    near_fp = near_n = 0
    for a in sample:
        b = normalise_batch(a["batch_no"])
        m = _mutate(b, rnd)
        if m in known:
            continue  # the mutation is itself a real flagged batch; not a near miss
        near_n += 1
        near_fp += bool(check(m))

    clean_fp = clean_n = 0
    while clean_n < n:
        c = _clean(rnd)
        if c in known:
            continue
        clean_n += 1
        clean_fp += bool(check(c))

    makers = [a["manufacturer"] for a in sample]
    wrong_strong = wrong_n = 0
    for a in sample:
        other = rnd.choice(makers)
        if other == a["manufacturer"]:
            continue
        wrong_n += 1
        res = [m for m in check(a["batch_no"], other) if m["alert"]["id"] == a["id"]]
        wrong_strong += bool(res and res[0]["score"]["level"] == "strong" and (res[0]["score"]["maker"] or 0) >= 80
                             and other.split()[0].lower() != a["manufacturer"].split()[0].lower())

    # Same maker, written the way a strip, a bill or OCR writes it: must still be recognised as that maker.
    def respell(m: str) -> str:
        core = re.sub(r"(?i)\b(pvt\.?|private|ltd\.?|limited|llp|m/s\.?)", " ", m)
        return rnd.choice([m.upper(), " ".join(core.split()), "M/s " + m, core.replace(" ", "", 1).strip(), m.lower() + " ltd"])

    right_strong = right_n = 0
    for a in sample:
        if re.search(r"under investigation|unknown|not known", a["manufacturer"], re.I):
            continue
        right_n += 1
        res = [m for m in check(a["batch_no"], respell(a["manufacturer"])) if m["alert"]["id"] == a["id"]]
        right_strong += bool(res and res[0]["score"]["level"] == "strong")

    fp = near_fp + clean_fp
    timings.sort()
    return {
        "alerts_in_db": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
        "sampled_alerts": len(sample),
        "positive_probes": tp + fn,
        "recall_pct": round(100 * tp / max(1, tp + fn), 2),
        "near_miss_probes": near_n,
        "clean_probes": clean_n,
        "false_alarms": fp,
        "precision_pct": round(100 * tp / max(1, tp + fp), 2),
        "wrong_maker_probes": wrong_n,
        "wrong_maker_marked_strong": wrong_strong,
        "right_maker_probes": right_n,
        "right_maker_strong_pct": round(100 * right_strong / max(1, right_n), 1),
        "check_ms_p50": round(statistics.median(timings), 3),
        "check_ms_p95": round(timings[int(len(timings) * 0.95)], 3),
        "missed_examples": misses,
        "seed": seed,
    }


def cached(conn, lookup, refresh: bool = False) -> dict:
    """The benchmark takes ~1 s; the status page reuses one result until the alert count changes."""
    global _cache
    n = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    if refresh or _cache is None or _cache["alerts_in_db"] != n:
        _cache = measure(conn, lookup)
    return _cache
