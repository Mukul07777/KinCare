"""KinCare Recall Watcher: a custom Switch protocol agent.

It speaks first. Every few minutes it checks the family's medicines (switch/family.json) against the
KinCare alert store (real CDSCO data) and, the first time a batch matches, posts an alert in the family
room and hands the case to @kincare-pharmacist by name. Nothing else in the room has to ask it.

Standard library only.

    python switch/recall_watcher.py register      # once: creates the agent, saves its key in switch/.env
    python switch/recall_watcher.py rooms         # list the rooms it is in (add it to the room in Console first)
    python switch/recall_watcher.py listen        # live: stays connected, answers @mentions, checks periodically
    python switch/recall_watcher.py run           # watch forever (every KINCARE_WATCH_MINUTES, default 10), post-only
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
            "connection_model": "always_on",
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
    ]
    doctor = kincare_cli.needs_doctor(a.get("product_name", ""))
    if doctor["required"]:
        lines += [f"🩺 This is a {doctor['why']}. A change needs the DOCTOR's approval too, not only the pharmacist's.",
                  "हिंदी: यह ज़रूरी दवा है। डॉक्टर की सलाह के बिना कोई बदलाव न करें।"]
    lines.append("Family: please don't stop or switch any medicine until the pharmacist or doctor says so.")
    return "\n".join(l for l in lines if l is not None)


def blast_text(batch: dict, pharmacy: str = "") -> str:
    """For the Pharmacy Desk: one recall, every home that holds it, next dose first."""
    a = batch["alert"]
    hs = sorted(batch["holders"], key=lambda h: min(h["times"]) if h["times"] else "99:99")
    lines = [f"📡 Blast radius: {batch['brand']} batch {batch['batch']} (CDSCO {a.get('category', '').upper()}, "
             f"{a.get('alert_month', '')}) is in {len(hs)} home{'s' if len(hs) != 1 else ''} {pharmacy and f'served by {pharmacy}'}".rstrip()]
    lines += [f"  • {h['family']}: {h['person']}, doses at {', '.join(h['times']) or 'unknown'}"
              + (f" (caregiver {h['caregiver']})" if h.get("caregiver") else "") for h in hs]
    if batch.get("doctor", {}).get("required"):
        lines.append(f"🩺 {batch['doctor']['why']}: each family's doctor must approve a change.")
    lines.append(f"@{PHARMACIST} prepare one same-salt replacement" + (" for all of them" if len(hs) > 1 else "")
                 + ". Pharmacist: approve once here, and each family room gets its own decision and task.")
    return "\n".join(lines)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.is_file() else {"alerted": []}


def check_once(env: dict, dry: bool = False) -> int:
    """Check every family in the pharmacy network. Each holder is told once, in their own family room
    (or this watcher's rooms, for the default family); the Pharmacy Desk gets one blast-radius summary
    per batch."""
    result = kincare_cli.network_check()
    state = load_state()
    net = kincare_cli.load_network()
    pharmacy_room = env.get("SWITCH_PHARMACY_ROOM_ID") or net.get("pharmacy_room_id", "")
    default_rooms: list[str] | None = None
    sent = 0
    for batch in result["flagged"]:
        for h in batch["holders"]:
            key = f"{h['family']}|{h['person']}|{batch['batch']}"
            if key in state["alerted"]:
                continue
            text = alert_text({"person": h["person"], "brand": batch["brand"], "batch": batch["batch"],
                               "match": {"alert": batch["alert"]}})
            if dry:
                print(f"[{h['family']} room]\n{text}\n")
                sent += 1
                continue
            rooms = [h["room_id"]] if h.get("room_id") else []
            if not rooms and h.get("default"):
                if default_rooms is None:
                    default_rooms = [r for r in room_ids(env) if r != pharmacy_room]
                rooms = default_rooms
            if not rooms:
                continue  # this family has no room yet; the Pharmacy Desk still hears about it below
            for room in rooms:
                post(env, room, text)
            state["alerted"].append(key)
            sent += 1
        pkey = f"pharmacy|{batch['batch']}"
        if pkey not in state["alerted"] and (pharmacy_room or dry):
            text = blast_text(batch, net.get("pharmacy", ""))
            if dry:
                print(f"[Pharmacy Desk]\n{text}\n")
            else:
                post(env, pharmacy_room, text)
                state["alerted"].append(pkey)
    if not dry:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Checked {result['checked']} batches across {len(net['families'])} families: "
          f"{sent} new alert(s){' (dry run)' if dry else ''}.")
    return sent


# ---- live connection: the watcher also answers when @mentioned ----

HELP = (
    "I watch this family's medicines against India's CDSCO drug alerts and speak up when a batch is flagged.\n"
    "Ask me: @kincare-recall-watcher check  (check everything now) · status  (what I watch) · help\n"
    "मैं परिवार की दवाओं को सरकारी अलर्ट से मिलाता हूँ। 'check' लिखें, मैं अभी जाँच करूँगा।"
)


def families_for_room(net: dict, room: str) -> list[dict]:
    """The families a room speaks for: the ones whose room_id it is, else the default family."""
    mine = [f for f in net["families"] if f.get("room_id") and f["room_id"] == room]
    return mine or [f for f in net["families"] if f.get("default")] or net["families"][:1]


def reply_to(body: str, env: dict, room: str) -> str:
    """What the watcher says to an addressed message. Answers only about this room's family, never another's.
    Uses the same 'family|person|batch' keys as the periodic check, so nothing is ever alerted twice."""
    text = body.lower()
    net = kincare_cli.load_network()
    pharmacy_room = env.get("SWITCH_PHARMACY_ROOM_ID") or net.get("pharmacy_room_id", "")
    if any(w in text for w in ("check", "scan", "जाँच", "जांच", "chek")):
        result = kincare_cli.network_check()
        if room and room == pharmacy_room:   # the Pharmacy Desk sees the whole network
            if not result["flagged"]:
                return f"✅ Checked {result['checked']} batches across {len(net['families'])} families: no alerts."
            return "\n\n".join(blast_text(b, net.get("pharmacy", "")) for b in result["flagged"])
        names = {f["name"] for f in families_for_room(net, room)}
        state = load_state()
        out, count = [], sum(len(f.get("medicines", [])) for f in net["families"] if f["name"] in names)
        for b in result["flagged"]:
            for h in b["holders"]:
                if h["family"] not in names:
                    continue
                key = f"{h['family']}|{h['person']}|{b['batch']}"
                if key in state["alerted"]:
                    out.append(f"Still flagged (already raised): {h['person']}'s {b['brand']}, batch {b['batch']}.")
                else:
                    out.append(alert_text({"person": h["person"], "brand": b["brand"], "batch": b["batch"],
                                           "match": {"alert": b["alert"]}}))
                    state["alerted"].append(key)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if not out:
            return f"✅ Checked {count} medicines just now: none is on a CDSCO alert list.\nसभी {count} दवाएँ जाँचीं: कोई अलर्ट नहीं।"
        return "\n\n".join(out)
    if "status" in text or "list" in text:
        fams = families_for_room(net, room)
        meds = [(f["name"], m) for f in fams for m in f.get("medicines", [])]
        lines = [f"• {m['person']}: {m['brand']}, batch {m['batch']}" for _, m in meds] or ["(no medicines saved yet)"]
        return f"I watch {len(meds)} medicines, every {env.get('KINCARE_WATCH_MINUTES', '10')} min:\n" + "\n".join(lines)
    return HELP


async def listen(env: dict) -> None:
    """Hold the Switch connection: answer pings, act on messages addressed to the watcher,
    and run the periodic check alongside. Reconnects with the same connection id."""
    import asyncio
    import uuid

    import websockets

    base = env["SWITCH_URL"].rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    conn_id = env.get("SWITCH_CONNECTION_ID") or str(uuid.uuid4())
    if not env.get("SWITCH_CONNECTION_ID"):
        save_env({"SWITCH_CONNECTION_ID": conn_id})
    rooms = room_ids(env)
    if not rooms:
        sys.exit("The watcher is in no room yet. Add it to the family room in Switch Console.")
    # Claim every family room on open; with more than one room the connection must be multi-room.
    url = (f"{base}/agents/{env['SWITCH_AGENT_ID']}/connection/ws?connection_id={conn_id}&client=kincare-watcher&filter=addressed"
           f"&rooms={','.join(rooms)}" + ("&scope=all" if len(rooms) > 1 else ""))
    minutes = float(env.get("KINCARE_WATCH_MINUTES", "10"))

    async def periodic():
        while True:
            try:
                await asyncio.to_thread(check_once, env)
            except (SwitchError, kincare_cli.ApiError) as e:
                print(f"[retry next round] {e}")
            await asyncio.sleep(minutes * 60)

    ticker = asyncio.create_task(periodic())
    cursor = 0
    try:
        while True:
            try:
                async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {env['SWITCH_AGENT_KEY']}"}) as ws:
                    print(f"Connected to Switch as {AGENT_NAME}. Listening for @mentions.")
                    async for raw in ws:
                        frame = json.loads(raw)
                        event, data = frame.get("event"), frame.get("data") or {}
                        if isinstance(frame.get("id"), int):
                            cursor = frame["id"]
                        if event == "ping":
                            await ws.send(json.dumps({"type": "pong", "cursor": cursor}))
                        elif event == "connection_state":
                            cursor = data.get("cursor", cursor) or cursor
                        elif event in ("refused", "evicted"):
                            print(f"Switch {event} the connection: {data}")
                            break
                        elif event == "message":
                            payload = data.get("payload") or {}
                            if payload.get("addressed") and payload.get("sender_kind") != "agent":
                                room = data.get("room_id")
                                try:
                                    text = await asyncio.to_thread(reply_to, payload.get("body", ""), env, room)
                                except kincare_cli.ApiError as e:
                                    text = f"KinCare is not reachable right now, I'll keep trying. ({e})"
                                await asyncio.to_thread(post, env, room, text)
            except (OSError, websockets.WebSocketException) as e:
                print(f"Connection lost ({e}); reconnecting in 5 s")
            await asyncio.sleep(5)
    finally:
        ticker.cancel()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "once"
    env = load_env()
    dry = cmd == "once" and "--dry" in sys.argv
    if cmd in ("rooms", "once", "run", "listen") and not dry:
        missing = [k for k in ("SWITCH_URL", "SWITCH_AGENT_ID", "SWITCH_AGENT_KEY") if not env.get(k)]
        if missing:
            sys.exit(f"Missing {', '.join(missing)} in switch/.env. Set SWITCH_URL and SWITCH_REGISTRATION_KEY, then run:\n"
                     "  api\\.venv\\Scripts\\python switch\\recall_watcher.py register\n"
                     "(Or try it without Switch: recall_watcher.py once --dry, or switch\\demo_local.py)")
    try:
        if cmd == "register":
            register(env)
        elif cmd == "rooms":
            print(json.dumps(op(env, "list_rooms"), indent=2))
        elif cmd == "once":
            check_once(env, dry="--dry" in sys.argv)
        elif cmd == "listen":
            import asyncio
            asyncio.run(listen(env))
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
