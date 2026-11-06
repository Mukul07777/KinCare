"""KinCare room, played locally: the whole family workflow without Telegram or a Switch server.

For judges and anyone without a Telegram bot. It runs the same steps the Switch agents run, on the same
KinCare API and real CDSCO data, and prints the room as a chat. The human steps (the pharmacist's
approval, the caregiver's "done") wait for you to type, or run with --auto.

    api\\.venv\\Scripts\\python switch\\demo_local.py          # interactive: you are the pharmacist
    api\\.venv\\Scripts\\python switch\\demo_local.py --auto   # plays everyone

It writes the room's shared documents to switch/demo_out/: KinCare Decisions.md and KinCare Tasks.md,
the same documents the agents keep in the Switch room.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kincare_cli as kc  # noqa: E402
import recall_watcher  # noqa: E402

STRIPS = HERE.parent / "web" / "public" / "test-strips"
OUT = HERE / "demo_out"
AUTO = "--auto" in sys.argv
os.system("")  # enable ANSI colours on Windows terminals

COLOURS = {"human": "\033[96m", "agent": "\033[93m", "pharmacist": "\033[92m", "dim": "\033[90m", "end": "\033[0m"}


def say(who: str, text: str, kind: str = "agent") -> None:
    c, end = COLOURS[kind], COLOURS["end"]
    first, *rest = text.splitlines() or [""]
    print(f"{c}{who:>22}{end}  {first}")
    for line in rest:
        print(f"{'':>22}  {line}")
    print()
    time.sleep(0 if AUTO else 0.6)


def note(text: str) -> None:
    print(f"{COLOURS['dim']}{'':>22}  [{text}]{COLOURS['end']}\n")


def ask(prompt: str, default: str) -> str:
    if AUTO:
        return default
    got = input(f"{COLOURS['pharmacist']}{prompt}{COLOURS['end']} [{default}] > ").strip()
    print()
    return got or default


def write_doc(name: str, lines: list[str]) -> Path:
    OUT.mkdir(exist_ok=True)
    p = OUT / f"{name}.md"
    p.write_text(f"# {name}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def main() -> int:
    try:
        kc.get("/health")
    except kc.ApiError as e:
        print(e)
        return 1
    # The demo works on its own copy of the family list, so the real one is never touched.
    OUT.mkdir(exist_ok=True)
    demo_family = OUT / "family.json"
    demo_family.write_text(kc.FAMILY.read_text(encoding="utf-8") if kc.FAMILY.is_file() else "[]", encoding="utf-8")
    kc.FAMILY = demo_family
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n  Telegram group  \"Sharma Family Care\"   (a Switch room: 3 people, 4 agents)\n" + "  " + "─" * 76 + "\n")

    # 1. A clean strip
    say("Dadi", "[photo: amlodipine strip]  @kincare-scan यह दवा ठीक है?", "human")
    s = kc.upload("/api/scan", str(STRIPS / "amlodipine-clean.png"))["fields"]
    note(f"kincare-scan: kincare_cli scan -> batch {s['batch']}, then check")
    r = kc.get("/api/check", batch=s["batch"], brand=s.get("brand"))
    assert r["verdict"] == "no_alert_found"
    say("KinCare Scan", f"✅ बैच {s['batch']} सरकारी अलर्ट सूची में नहीं है। दवा ले सकती हैं।\n"
                        f"Batch {s['batch']} ({s['brand']}) is not on any CDSCO alert list.")

    # 2. The flagged strip
    say("Dadi", "[photo: Namik-MR strip]  @kincare-scan और यह वाली?", "human")
    s = kc.upload("/api/scan", str(STRIPS / "namik-mr.png"))["fields"]
    note(f"kincare-scan: kincare_cli scan -> batch {s['batch']} (OCR), then check")
    kc.save_family([m for m in kc.load_family() if m["batch"] != s["batch"]]
                   + [{"person": "Dadi", "brand": s["brand"], "batch": s["batch"], "maker": s.get("maker", ""), "times": ["09:00"]}])
    flagged = next(f for f in kc.family_check()["flagged"] if f["batch"] == s["batch"])
    say("KinCare Recall Watcher", recall_watcher.alert_text(flagged))

    # 3. Pharmacist agent finds safe options
    note("kincare-pharmacist: kincare_cli replacements AT25-0938A")
    rep = kc.replacements(s["batch"], limit=3)
    opts = rep["options"]
    lines = [f"Proposed replacement for Dadi's {s['brand']} (batch {s['batch']}).",
             f"Same salts ({', '.join(rep['salts'])}), same form, makers with no CDSCO alerts on record:"]
    lines += [f"  {i}) {o['name']}  ({o['maker']}), ₹{o['unit_price']:.2f}/tablet" for i, o in enumerate(opts, 1)]
    lines += ["@Pharmacist reply  approve 1" + (f"/{len(opts)}" if len(opts) > 1 else "") + "  or  reject.  Nothing changes until you do."]
    say("KinCare Pharmacist", "\n".join(lines))

    # 4. A family member tries to approve: not allowed
    say("Rahul (son)", "approve 1", "human")
    say("KinCare Pharmacist", "Thanks Rahul. Only the pharmacist can approve a change of medicine.\n@Pharmacist please confirm.")

    # 5. The human pharmacist decides
    choice = ask("You are the pharmacist. Type 'approve N' or 'reject'", "approve 1")
    say("Pharmacist (Mr. Verma)", choice, "pharmacist")
    if not choice.lower().startswith("approve"):
        write_doc("KinCare Decisions", [f"- {today} | Dadi | {s['brand']} {s['batch']} | replacement rejected by Mr. Verma"])
        say("KinCare Pharmacist", "Noted: no change. Decision logged. Please talk to Dadi's doctor about this batch.")
        return 0
    try:
        pick = opts[int(choice.split()[-1]) - 1]
    except (ValueError, IndexError):
        pick = opts[0]
    d = write_doc("KinCare Decisions", [
        f"- {today} | Dadi | {s['brand']} batch {s['batch']} (CDSCO {flagged['match']['alert']['category'].upper()}, "
        f"{flagged['match']['alert'].get('alert_month', '')}) -> {pick['name']} ({pick['maker']}) | approved by Mr. Verma (pharmacist)"])
    t = write_doc("KinCare Tasks", [f"- [ ] Rahul: buy {pick['name']} today; keep the old strip for return",
                                    "- [ ] Dose Buddy: switch Dadi's 09:00 dose to the new strip"])
    say("KinCare Pharmacist", f"✅ Decision logged in \"KinCare Decisions\".\n"
                              f"Task for @Rahul: buy {pick['name']} today, keep the old strip for return.\n"
                              f"हिंदी: फार्मासिस्ट ने नई दवा मंज़ूर की है। राहुल आज ला देंगे।")
    note(f"room documents written: {d.relative_to(HERE.parent)}, {t.relative_to(HERE.parent)}")

    # 6. Caregiver closes the task, dose buddy switches the schedule
    say("Rahul (son)", ask("You are Rahul. Reply when bought", "done, bought"), "human")
    kc.save_family([m for m in kc.load_family() if m["batch"] != s["batch"]]
                   + [{"person": "Dadi", "brand": pick["name"], "batch": "NEW-STRIP", "maker": pick["maker"], "times": ["09:00"]}])
    write_doc("KinCare Tasks", [f"- [x] Rahul: buy {pick['name']} today; keep the old strip for return",
                                "- [x] Dose Buddy: switch Dadi's 09:00 dose to the new strip"])
    say("KinCare Dose Buddy", f"दादी, कल सुबह 9 बजे से नई दवा: {pick['name'].split()[0]}, 1 गोली।\n"
                              f"Dadi's 09:00 dose now uses the new strip. Both tasks done ✅")

    print("  " + "─" * 76)
    print("  Real: CDSCO alert for batch AT25-0938A, OCR on the strip image, 246k-brand medicine data.")
    print("  Simulated: the Sharma family and Mr. Verma. In Switch, this is the same flow in Telegram.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
