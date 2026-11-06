"""KinCare Recall Watcher: a custom Switch protocol agent.

It speaks first. Every few minutes it checks the family's medicines (switch/family.json) against the
KinCare alert store (real CDSCO data) and, the first time a batch matches, posts an alert in the family
room and hands the case to @kincare-pharmacist by name. Nothing else in the room has to ask it.

Standard library only.

    python switch/recall_watcher.py register      # once: creates the agent, saves its key in switch/.env
    python switch/recall_watcher.py rooms         # list the rooms it is in (add it to the room in Console first)
    python switch/recall_watcher.py run           # watch forever (every KINCARE_WATCH_MINUTES, default 10)
    python switch/recall_watcher.py once          # one check now (for the demo)
    python switch/recall_watcher.py once --dry    # print the alert instead of posting it

Settings (switch/.env, git-ignored, or environment):
    SWITCH_URL                Switch server address (Console -> server -> address), e.g. http://127.0.0.1:59754
    SWITCH_REGISTRATION_KEY   registration key (Gateway -> API Keys), only for `register`
    SWITCH_AGENT_ID           written by `register`
    SWITCH_AGENT_KEY          written by `register` (shown once by Switch; keep it secret)
    SWITCH_ROOM_IDS           comma-separated room ids to post in; default: every room the agent is in
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kincare_cli  # noqa: E402

ENV_FILE = HERE / ".env"
STATE_FILE = HERE / ".watcher_state.json"
AGENT_NAME = "kincare-recall-watcher"
PHARMACIST = "kincare-pharmacist"


# ---- settings ----

def load_env() -> dict[str, str]:
    env = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
    env.update({k: v for k, v in os.environ.items() if k.startswith(("SWITCH_", "KINCARE_"))})
    return env


def save_env(updates: dict[str, str]) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.is_file() else []
    keep = [l for l in lines if l.split("=", 1)[0].strip() not in updates]
    keep += [f"{k}={v}" for k, v in updates.items()]
    ENV_FILE.write_text("\n".join(keep) + "\n", encoding="utf-8")


# ---- Switch HTTP ----

class SwitchError(Exception):
    pass


def call(base: str, method: str, path: str, key: str, body: dict | None = None):
    req = urllib.request.Request(
        base.rstrip("/") + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        raise SwitchError(f"Switch {e.code} on {path}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    except urllib.error.URLError as e:
        raise SwitchError(f"Switch not reachable at {base} ({e.reason}). Is Switch Console running?") from None


def register(env: dict) -> None:
    base, reg = env.get("SWITCH_URL"), env.get("SWITCH_REGISTRATION_KEY")
    if not base or not reg:
        sys.exit("Set SWITCH_URL and SWITCH_REGISTRATION_KEY in switch/.env first (see REMINDER_MUKUL.txt).")
    r = call(base, "POST", "/agents", reg, {
        "name": AGENT_NAME,
        "display_name": "KinCare Recall Watcher",
        "description": "Watches CDSCO drug alerts and tells the family when a medicine they hold is flagged.",
        "connector_type": "kincare-python",
        "integration_profile": {
            "connection_model": "session_passive",
            "message_exchange": True,
            "pre_invocation_mediation": [],
            "post_invocation_mediation": [],
            "event_reporting": [],
        },
    })
    save_env({"SWITCH_AGENT_ID": r["id"], "SWITCH_AGENT_KEY": r["api_key"]})
    print(f"Registered {AGENT_NAME} ({r['id']}). Key saved in switch/.env.")
    print("Next: in Switch Console add it to the family room, then run: python switch/recall_watcher.py rooms")


def op(env: dict, name: str, args: dict | None = None):
    r = call(env["SWITCH_URL"], "POST", f"/agents/{env['SWITCH_AGENT_ID']}/ops/{name}", env["SWITCH_AGENT_KEY"], args or {})
    return r.get("result", r) if isinstance(r, dict) else r


def room_ids(env: dict) -> list[str]:
    if env.get("SWITCH_ROOM_IDS"):
        return [r.strip() for r in env["SWITCH_ROOM_IDS"].split(",") if r.strip()]
    rooms = op(env, "list_rooms")
    rooms = rooms.get("rooms", rooms) if isinstance(rooms, dict) else rooms
    return [r.get("room_id") or r.get("id") for r in rooms or [] if isinstance(r, dict)]


def post(env: dict, room: str, text: str) -> None:
    call(env["SWITCH_URL"], "POST", f"/agents/{env['SWITCH_AGENT_ID']}/message", env["SWITCH_AGENT_KEY"],
         {"room_id": room, "content": text})


# ---- the alert ----

def alert_text(item: dict) -> str:
    """One alert, written for a family: what, why, who acts next. Never tells anyone to stop a medicine."""
    m = item.get("match") or {}
    a = m.get("alert") or {}
    kind = {"nsq": "Not of Standard Quality", "spurious": "spurious (fake) drug"}.get(a.get("category"), "drug alert")
    reason = (a.get("reason") or "failed a government quality test").strip().rstrip(".")
    when = a.get("alert_month") or ""
    maker = (a.get("manufacturer") or item.get("maker") or "").strip().rstrip(".")
    where = (a.get("reported_by") or "").strip()
    lines = [
        f"⚠️ Recall alert for {item['person']}: {item['brand']}, batch {item['batch']}",
        f"This exact batch is on the CDSCO {kind} list{f' ({when})' if when else ''}"
        + (f", sampled in {where}" if where else "") + f": {reason}."
        + (f" Maker: {maker}." if maker else "")
        + (f" Made {a['mfg_date']}, expires {a['expiry']}, so it may still be in use." if a.get("mfg_date") and a.get("expiry") else ""),
        f"Source: {a['alert_url']}" if a.get("alert_url") else None,
        f"हिंदी: {item['person']} की दवा {item['brand']} (बैच {item['batch']}) सरकारी जाँच में फेल हुई है। "
        "दवा बदलने से पहले फार्मासिस्ट या डॉक्टर से बात करें।",
        "",
        f"@{PHARMACIST} please find the same salts from a maker with no alerts, and ask our pharmacist to approve.",
        "Family: please don't stop or switch any medicine until the pharmacist or doctor says so.",
    ]
    return "\n".join(l for l in lines if l is not None)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.is_file() else {"alerted": []}


def check_once(env: dict, dry: bool = False) -> int:
    result = kincare_cli.family_check()
    state = load_state()
    new = [f for f in result["flagged"] if f"{f['person']}|{f['batch']}" not in state["alerted"]]
    if not new:
        print(f"Checked {result['checked']} medicines: nothing new.")
        return 0
    rooms = [] if dry else room_ids(env)
    if not dry and not rooms:
        sys.exit("The watcher is in no room yet. Add it to the family room in Switch Console.")
    for item in new:
        text = alert_text(item)
        if dry:
            print(text + "\n")
        else:
            for room in rooms:
                post(env, room, text)
            state["alerted"].append(f"{item['person']}|{item['batch']}")
    if not dry:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Checked {result['checked']} medicines: {len(new)} new alert(s){' (dry run)' if dry else ''}.")
    return len(new)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "once"
    env = load_env()
    try:
        if cmd == "register":
            register(env)
        elif cmd == "rooms":
            print(json.dumps(op(env, "list_rooms"), indent=2))
        elif cmd == "once":
            check_once(env, dry="--dry" in sys.argv)
        elif cmd == "run":
            minutes = float(env.get("KINCARE_WATCH_MINUTES", "10"))
            print(f"Watching every {minutes:g} min. Ctrl+C to stop.")
            while True:
                try:
                    check_once(env)
                except (SwitchError, kincare_cli.ApiError) as e:
                    print(f"[retry next round] {e}")
                time.sleep(minutes * 60)
        elif cmd == "reset":
            STATE_FILE.unlink(missing_ok=True)
            print("Forgot past alerts; the next check alerts again.")
        else:
            sys.exit(__doc__)
    except (SwitchError, kincare_cli.ApiError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
