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

KINCARE_API (default http://localhost:8000) points at the KinCare API.
KINCARE_FAMILY (default switch/family.json) is the family medicine list.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
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
        else:  # family-check
            out = family_check()
    except ApiError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
