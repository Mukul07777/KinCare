"""The Switch side of KinCare, as data for the web app's Care Network page.

It runs the same logic the Switch agents run (switch/kincare_cli.py: network check, blast radius, doctor
escalation, safe replacements) inside this process, so the page shows exactly what the agents would say
in the family rooms and the Pharmacy Desk. Read-only.
"""
import re
import sys
from pathlib import Path

from fastapi import APIRouter

from core import conn, run_check

SWITCH_DIR = Path(__file__).resolve().parents[2] / "switch"
if str(SWITCH_DIR) not in sys.path:
    sys.path.insert(0, str(SWITCH_DIR))
import kincare_cli as kc  # noqa: E402

router = APIRouter()


def _in_process_get(path: str, **params):
    """kincare_cli talks HTTP to this API; inside the API, answer the same calls directly."""
    import prices

    if path == "/api/check":
        return run_check(params["batch"], params.get("maker"), params.get("brand"))
    if path == "/api/medicines/search":
        return prices.search(conn, params["q"])
    m = re.fullmatch(r"/api/medicines/(\d+)/alternatives", path)
    if m:
        return prices.alternatives(conn, int(m.group(1)), min(int(params.get("limit", 20)), 50)) or {}
    if path == "/health":
        return {"ok": True}
    raise ValueError(f"unsupported in-process call {path}")


kc.get = _in_process_get

_options_cache: dict[str, dict] = {}


def _docs() -> dict:
    """The room documents the demo or the agents wrote (switch/demo_out), if any."""
    out: dict[str, list[dict]] = {"decisions": [], "tasks": []}
    folder = SWITCH_DIR / "demo_out"
    if not folder.is_dir():
        return out
    for f in sorted(folder.glob("*.md")):
        kind = "decisions" if "Decisions" in f.name else "tasks" if "Tasks" in f.name else None
        if not kind:
            continue
        family = f.name.split(" - ")[0] if " - " in f.name else "Sharma"
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.startswith("- "):
                continue
            item = {"family": family, "text": line[2:].strip()}
            if kind == "tasks":
                item["done"] = item["text"].startswith("[x]")
                item["text"] = item["text"][3:].strip() if item["text"][:3] in ("[x]", "[ ]") else item["text"]
            out[kind].append(item)
    return out


@router.get("/api/switch/network")
def switch_network():
    net = kc.load_network()
    result = kc.network_check()
    flagged = []
    for b in result["flagged"]:
        key = kc._norm_batch(b["batch"])
        if key not in _options_cache:
            rep = kc.replacements(b["batch"], limit=3)
            _options_cache[key] = {k: rep.get(k) for k in ("options", "salts", "strengths", "note")}
        a = b["alert"]
        flagged.append({
            "batch": b["batch"], "brand": b["brand"], "doctor": b["doctor"],
            "holders": sorted(b["holders"], key=lambda h: min(h["times"]) if h["times"] else "99:99"),
            "alert": {k: a.get(k) for k in ("category", "product_name", "reason", "manufacturer", "reported_by",
                                            "alert_month", "mfg_date", "expiry", "alert_url")},
            **_options_cache[key],
        })
    flagged_keys = {kc._norm_batch(f["batch"]) for f in flagged}
    families = [{
        "name": f["name"], "caregiver": f.get("caregiver", ""), "default": f.get("default", False),
        "medicines": [{**m, "flagged": kc._norm_batch(m["batch"]) in flagged_keys} for m in f.get("medicines", [])],
    } for f in net["families"]]
    return {
        "pharmacy": net.get("pharmacy", ""), "pharmacist": net.get("pharmacist", ""),
        "families": families, "flagged": flagged, "checked": result["checked"], "documents": _docs(),
        "agents": [
            {"name": "kincare-recall-watcher", "label": "Recall Watcher", "kind": "Custom protocol agent (Python)",
             "job": "Speaks first when a family's batch is flagged; posts the blast radius to the Pharmacy Desk"},
            {"name": "kincare-scan", "label": "Scan", "kind": "Claude Code, run by Switch Console",
             "job": "Strip or bill photo → batch → CDSCO check, Hindi first"},
            {"name": "kincare-pharmacist", "label": "Pharmacist", "kind": "Claude Code, run by Switch Console",
             "job": "Same salts, form and strength from makers with no alerts; asks the human; logs the decision"},
            {"name": "kincare-dose", "label": "Dose Buddy", "kind": "Claude Code, run by Switch Console",
             "job": "Dose schedule, missed-dose nudges, switches to the approved strip"},
        ],
    }
