"""KinCare CLI: the one tool KinCare's Switch agents use to reach the KinCare API.

Standard library only, so any agent (Claude Code, Codex, ...) can run it with plain `python`.
Every command prints JSON on stdout. Exit code 0 = ok, 1 = API error, 2 = bad usage.

    python switch/kincare_cli.py health
    python switch/kincare_cli.py check AT25-0938A [--maker "X Pharma"] [--brand Namik-MR]
    python switch/kincare_cli.py scan path/to/strip.jpg
    python switch/kincare_cli.py bill path/to/bill.jpg
    python switch/kincare_cli.py search "telma h"
    python switch/kincare_cli.py alternatives 12345 [--limit 5]
    python switch/kincare_cli.py info 12345
    python switch/kincare_cli.py alerts [--q namik] [--limit 10]
    python switch/kincare_cli.py family                      # the room's family medicine list
    python switch/kincare_cli.py family-add "Dadi" "Namik-MR" AT25-0938A [--maker X] [--times 08:00,20:00]
    python switch/kincare_cli.py family-check                # every family batch against the alert store
    python switch/kincare_cli.py replacements AT25-0938A     # same salts + form, makers with no alerts (+ needs_doctor)
    python switch/kincare_cli.py holders AT25-0938A          # every family in the pharmacy network holding it
    python switch/kincare_cli.py network-check               # all families, flagged batches grouped (blast radius)

KINCARE_API (default http://localhost:8000) points at the KinCare API.
KINCARE_FAMILY (default switch/family.json) is the family medicine list.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = os.environ.get("KINCARE_API", "http://localhost:8000").rstrip("/")
FAMILY = Path(os.environ.get("KINCARE_FAMILY", Path(__file__).with_name("family.json")))
TIMEOUT = 60


class ApiError(Exception):
    pass


def _request(method: str, path: str, *, params: dict | None = None, body: bytes | None = None,
             headers: dict | None = None):
    query = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except (ValueError, AttributeError):
            pass
        raise ApiError(f"KinCare API {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"KinCare API not reachable at {API} ({e.reason}). Start it with run.bat.") from None


def get(path: str, **params):
    return _request("GET", path, params=params)


def upload(path: str, file: str):
    p = Path(file)
    if not p.is_file():
        raise ApiError(f"No such image: {file}")
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{p.name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return _request("POST", path, body=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})


# ---- family medicine list (what this family holds; the room's shared record) ----

def load_family() -> list[dict]:
    if not FAMILY.is_file():
        return []
    return json.loads(FAMILY.read_text(encoding="utf-8"))


def save_family(items: list[dict]) -> None:
    FAMILY.parent.mkdir(parents=True, exist_ok=True)
    FAMILY.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def family_check() -> dict:
    out = []
    for m in load_family():
        r = get("/api/check", batch=m["batch"], maker=m.get("maker"), brand=m.get("brand"))
        out.append({**m, "verdict": r.get("verdict"), "match": (r.get("matches") or [None])[0]})
    return {"checked": len(out), "flagged": [o for o in out if o["verdict"] == "alert_found"], "items": out}


# ---- safe replacements: same salts, maker with no alerts ----

_SALT_SPLIT = re.compile(r",|&|\+|\band\b|/", re.I)
_DROP = re.compile(r"\b(tablets?|capsules?|syrup|suspension|injection|ip|bp|usp|sr|er|mr|cr|film|coated|oral|i\.p\.|"
                   r"sodium|potassium|calcium|hydrochloride|hcl|besilate|besylate|succinate|tartrate|maleate|"
                   r"mesylate|sulphate|sulfate|medoxomil|extended|release|prolonged|gastro|resistant|dispersible)\b"
                   r"|\d+(\.\d+)?\s*(mg|mcg|g|ml|%)", re.I)
_FORMS = ("tablet", "capsule", "syrup", "suspension", "injection", "gel", "cream", "drops")


def salts_of(product_name: str) -> list[str]:
    """'Aceclofenac, Paracetamol & Chlorzoxazone Tablets' -> ['aceclofenac', 'paracetamol', 'chlorzoxazone']."""
    out = []
    for part in _SALT_SPLIT.split(product_name or ""):
        word = re.sub(r"[^a-z ]", " ", _DROP.sub(" ", part).lower())
        word = " ".join(w for w in word.split() if len(w) > 2)
        if word:
            out.append(word)
    return out


def strengths_of(product_name: str, brand: str = "") -> list[str]:
    """Strength numbers to match: '... 50 mcg' -> ['50']; else a brand's trailing number ('Thyrox 50' -> ['50'])."""
    found = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mg|mcg|µg|g|iu)\b", product_name or "", re.I)
    if not found:
        m = re.search(r"\b(\d+(?:\.\d+)?)\s*$", (brand or "").strip())
        found = [m.group(1)] if m and brand.strip().upper() != "NA" else []
    return found


def _has_strength(med: dict, n: str) -> bool:
    text = f"{med.get('salts', '')} {med.get('name', '')}"
    return re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", text) is not None


def form_of(text: str) -> str:
    t = (text or "").lower()
    return next((f for f in _FORMS if f in t), "")


def replacements(batch: str, limit: int = 3) -> dict:
    """For a flagged batch: products with every salt of the original (checked in name AND salts, because the
    dataset can drop a salt), the same form, from makers with no CDSCO alerts, cheapest per unit first."""
    chk = get("/api/check", batch=batch)
    if chk.get("verdict") != "alert_found":
        return {"batch": batch, "flagged": False, "options": [], "note": "This batch is not on any alert list."}
    alert = chk["matches"][0]["alert"]
    product = alert.get("product_name") or alert.get("brand") or ""
    salts, form = salts_of(product), form_of(product)
    strengths = strengths_of(product, alert.get("brand", ""))
    if not salts:
        return {"batch": batch, "flagged": True, "alert": alert, "options": [], "note": "Salts unknown; ask the pharmacist."}
    seen, pool = set(), []
    for q in [" ".join(salts)] + salts:
        for m in get("/api/medicines/search", q=q) or []:
            if m["id"] not in seen:
                seen.add(m["id"]); pool.append(m)
        if len(pool) > 3:
            for alt in (get(f"/api/medicines/{pool[0]['id']}/alternatives", limit=50) or {}).get("alternatives", []):
                if alt["id"] not in seen:
                    seen.add(alt["id"]); pool.append(alt)
    bad_maker = normalise(alert.get("manufacturer", ""))
    options = []
    for m in pool:
        text = f"{m['name']} {m.get('salts', '')}".lower()
        # Count the ingredients the dataset lists; more than the original means a different medicine.
        listed = len([s for s in (m.get("salts") or "").split("+") if s.strip()])
        if not all(s in text for s in salts) or listed > len(salts):
            continue
        if form and m.get("form") and m["form"] != form:
            continue
        if not all(_has_strength(m, n) for n in strengths):   # same strength, or it is not the same medicine
            continue
        if (m.get("maker_record") or {}).get("alerts", 1) != 0 or normalise(m.get("maker", "")) == bad_maker:
            continue
        options.append({k: m.get(k) for k in ("id", "name", "maker", "price", "pack", "salts", "unit_price")})
    options.sort(key=lambda o: o["unit_price"] if o["unit_price"] is not None else 1e9)
    return {"batch": batch, "flagged": True, "salts": salts, "form": form, "strengths": strengths, "alert": alert,
            "options": options[:limit], "needs_doctor": needs_doctor(product),
            "note": ("Same salts, form and strength " + "/".join(strengths) if strengths else
                     "Same salts and form (strength not on the alert: the pharmacist must confirm it)")
                    + ", makers with no CDSCO alerts on record."}


# ---- doctor escalation: medicines where a change needs a doctor, not only a pharmacist ----

# Salt (as it appears in alert product names) -> why a doctor must sign off. Narrow-therapeutic-index and
# high-risk medicines: a different maker's tablet can behave differently, so the dose may need checking.
CRITICAL = {
    "warfarin": "blood thinner (dose is tuned with INR tests)",
    "acenocoumarol": "blood thinner (dose is tuned with INR tests)",
    "clopidogrel": "blood thinner after heart events or stents",
    "thyroxine": "thyroid hormone (dose is tuned with TSH tests)",
    "levothyroxine": "thyroid hormone (dose is tuned with TSH tests)",
    "phenytoin": "epilepsy medicine (narrow safe range)",
    "carbamazepine": "epilepsy medicine (narrow safe range)",
    "valproate": "epilepsy medicine (narrow safe range)",
    "lithium": "mood medicine (narrow safe range)",
    "digoxin": "heart rhythm medicine (narrow safe range)",
    "insulin": "diabetes injection (dose is tuned to blood sugar)",
    "glimepiride": "diabetes medicine (risk of low blood sugar)",
    "tacrolimus": "transplant medicine (narrow safe range)",
    "cyclosporine": "transplant medicine (narrow safe range)",
    "enoxaparin": "blood thinner injection",
}


def needs_doctor(product_name: str) -> dict:
    text = (product_name or "").lower()
    hits = sorted({why for salt, why in CRITICAL.items() if salt in text})
    return {"required": bool(hits), "why": "; ".join(hits)}


# ---- pharmacy network: which families hold a batch ----

NETWORK = Path(os.environ.get("KINCARE_NETWORK", Path(__file__).with_name("network.json")))


def load_network() -> dict:
    if not NETWORK.is_file():
        return {"pharmacy": "", "pharmacist": "", "pharmacy_room_id": "",
                "families": [{"name": "Family", "caregiver": "", "room_id": "", "default": True, "medicines": load_family()}]}
    net = json.loads(NETWORK.read_text(encoding="utf-8"))
    for fam in net["families"]:
        if "medicines_file" in fam:  # the room's own list (family.json) stays the source of truth
            fam["medicines"] = load_family()
    return net


def _norm_batch(b: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (b or "").upper())


def holders(batch: str) -> list[dict]:
    """Every family member in the pharmacy's network holding this exact batch."""
    want = _norm_batch(batch)
    out = []
    for fam in load_network()["families"]:
        for m in fam.get("medicines", []):
            if _norm_batch(m["batch"]) == want:
                out.append({"family": fam["name"], "caregiver": fam.get("caregiver", ""), "room_id": fam.get("room_id", ""),
                            "default": fam.get("default", False), **m})
    return out


def network_check() -> dict:
    """Check every batch every family holds; group the flagged ones by batch (one recall, many homes)."""
    net, verdicts, batches = load_network(), {}, {}
    for fam in net["families"]:
        for m in fam.get("medicines", []):
            key = _norm_batch(m["batch"])
            if key not in verdicts:
                verdicts[key] = get("/api/check", batch=m["batch"], maker=m.get("maker"), brand=m.get("brand"))
            r = verdicts[key]
            if r.get("verdict") == "alert_found":
                alert = r["matches"][0]["alert"]
                b = batches.setdefault(key, {"batch": m["batch"], "brand": m["brand"], "alert": alert,
                                             "doctor": needs_doctor(alert.get("product_name", "")), "holders": []})
                b["holders"].append({"family": fam["name"], "caregiver": fam.get("caregiver", ""),
                                     "room_id": fam.get("room_id", ""), "default": fam.get("default", False),
                                     "person": m["person"], "times": m.get("times", [])})
    return {"pharmacy": net.get("pharmacy", ""), "checked": len(verdicts), "flagged": list(batches.values())}


def normalise(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower().replace("pvt", "").replace("ltd", "").replace("llp", ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kincare_cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    c = sub.add_parser("check"); c.add_argument("batch"); c.add_argument("--maker"); c.add_argument("--brand")
    sub.add_parser("scan").add_argument("image")
    sub.add_parser("bill").add_argument("image")
    sub.add_parser("search").add_argument("query")
    a = sub.add_parser("alternatives"); a.add_argument("medicine_id", type=int); a.add_argument("--limit", type=int, default=5)
    sub.add_parser("info").add_argument("medicine_id", type=int)
    al = sub.add_parser("alerts"); al.add_argument("--q"); al.add_argument("--limit", type=int, default=10)
    sub.add_parser("family")
    fa = sub.add_parser("family-add")
    fa.add_argument("person"); fa.add_argument("brand"); fa.add_argument("batch")
    fa.add_argument("--maker", default=""); fa.add_argument("--times", default="")
    sub.add_parser("family-check")
    rp = sub.add_parser("replacements"); rp.add_argument("batch"); rp.add_argument("--limit", type=int, default=3)
    sub.add_parser("holders").add_argument("batch")
    sub.add_parser("network-check")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "health":
            out = get("/health")
        elif args.cmd == "check":
            out = get("/api/check", batch=args.batch, maker=args.maker, brand=args.brand)
        elif args.cmd == "scan":
            out = upload("/api/scan", args.image)
        elif args.cmd == "bill":
            out = upload("/api/scan/bill", args.image)
        elif args.cmd == "search":
            out = get("/api/medicines/search", q=args.query)
        elif args.cmd == "alternatives":
            out = get(f"/api/medicines/{args.medicine_id}/alternatives", limit=args.limit)
        elif args.cmd == "info":
            out = get(f"/api/medicines/{args.medicine_id}/info")
        elif args.cmd == "alerts":
            out = get("/api/alerts", q=args.q, limit=args.limit)
        elif args.cmd == "family":
            out = load_family()
        elif args.cmd == "family-add":
            items = [m for m in load_family() if not (m["person"] == args.person and m["batch"] == args.batch)]
            entry = {"person": args.person, "brand": args.brand, "batch": args.batch, "maker": args.maker,
                     "times": [t for t in args.times.split(",") if t]}
            items.append(entry)
            save_family(items)
            out = {"saved": entry, "total": len(items)}
        elif args.cmd == "replacements":
            out = replacements(args.batch, args.limit)
        elif args.cmd == "holders":
            out = holders(args.batch)
        elif args.cmd == "network-check":
            out = network_check()
        else:  # family-check
            out = family_check()
    except ApiError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Hindi in answers crashes a Windows cp1252 console
    sys.exit(main())
