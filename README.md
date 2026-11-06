# KinCare: know the batch, decide together

[![CI](https://github.com/Mukul07777/KinCare/actions/workflows/ci.yml/badge.svg)](https://github.com/Mukul07777/KinCare/actions/workflows/ci.yml)

**A family, their pharmacist and AI agents in one chat room, keeping an elder's medicines safe.**
Built on [Switch](https://github.com/sandbox-quantum/switch) for the Flip the Switch hackathon (Track 01: Best Business Workflow).

Team Avengers: Mukul (lead), Ashpreet Singh Saini.

---

## The problem nobody tells you about

India's drug regulator (CDSCO) publishes the batches that failed a quality test or turned out to be fake.
We pulled **6,830 real alerts (2019 to 2026)** from its public portal and measured the gap:

- A failed batch reaches the CDSCO list a median **10 months** after it was made.
- When it is listed, **99.5%** of those batches are still within expiry, with a median **14 months** left.
- So the medicine is still in homes, and people are still taking it. **Nobody tells them.**

And looking after an elder's medicines is a team job: Dadi takes them, her son lives in another city,
her daughter buys them, the local pharmacist knows what to replace them with. Today that "team" is a
messy WhatsApp group where a government PDF never arrives.

## What KinCare does

KinCare turns that family group into a **Switch room** where people and agents work together:

```
 Telegram group "Sharma Family Care"  (a Switch room)
 ─────────────────────────────────────────────────────────────────────────────
 Dadi            [photo of a Namik-MR strip]  @kincare-scan
 KinCare Scan    ⚠️ बैच AT25-0938A सरकारी जाँच में फेल। This batch is on the CDSCO
                 Not of Standard Quality list. @kincare-pharmacist please find a replacement.
 KinCare Pharm.  Proposed for Dadi (same three salts, makers with no CDSCO alerts):
                 1) StayHappi Aceclofenac+Chlorzoxazone+Paracetamol 100/325/250 mg, ₹2.70/tablet
                 2) Genericart Aceclofenac+Paracetamol+Chlorzoxazone 100/325/250 mg, ₹8.20/tablet
                 @Pharmacist reply approve 1/2 or reject. Nothing changes until you do.
 Pharmacist      approve 1
 KinCare Pharm.  ✅ Decision logged. Task: @Rahul buy StayHappi today, keep the old strip for return.
 Rahul           done, bought
 KinCare Dose    दादी, कल सुबह 9 बजे से नई दवा: StayHappi, 1 गोली।
 ─────────────────────────────────────────────────────────────────────────────
 Room documents:  KinCare Decisions · KinCare Tasks   (everyone reads the same record)
```

| Agent | Kind | What it does |
|---|---|---|
| **kincare-recall-watcher** | Custom Switch protocol agent (Python) | Speaks first: checks the family's batches against new CDSCO alerts and raises the alarm in the room |
| **kincare-scan** | Claude Code agent run by Switch Console | Reads a strip or bill photo (KinCare's own OCR), checks the exact batch, answers in Hindi + English |
| **kincare-pharmacist** | Claude Code agent run by Switch Console | Finds the same salts from a maker with no alerts and the saving, **asks the human pharmacist**, records the decision and the task |
| **kincare-dose** | Claude Code agent run by Switch Console | Dose schedule, "what's due?", missed-dose nudge to a caregiver, switches the schedule after an approved replacement |

**Humans decide, agents do the legwork.** Room rules (in the template) forbid any agent from telling anyone
to stop or switch a medicine; only the pharmacist or a doctor approves, and that approval is what gets logged.

## Why this needs Switch

Take Switch away and KinCare is a one-person app again. The whole idea is a **shared room**:

- **People and agents together, with roles**: elder, caregivers, pharmacist, four agents, one chat the family already uses (Telegram).
- **Agents hand off to each other in the open**: watcher → pharmacist agent → human pharmacist → dose agent, each by @name, visible to the family.
- **One shared record**: decisions and tasks live in the room's documents, not in someone's head.
- **Two ways of joining a room, both used**: three Claude Code agents run by Switch Console, and one custom agent speaking the Switch agent protocol (`POST /agents`, `POST /agents/{id}/message`), because a recall alert must arrive without anyone asking.
- **One-click setup**: a Switch room template creates the agents and the room with its rules.

## Try it in 2 minutes (no Telegram needed)

```bat
start_switch.bat                                   :: first run loads the real data, then starts the API
api\.venv\Scripts\python switch\demo_local.py     :: the family room in your terminal; you are the pharmacist
```

`demo_local.py` plays the same flow the Switch agents run, on the same real data: OCR on a strip photo,
the CDSCO match, safe same-salt options, your approval, and the room's *KinCare Decisions* and *KinCare Tasks*
documents written to `switch/demo_out/`. Add `--auto` to play every part.

## Run it in Switch

You need Windows, Python 3.12, [Switch Console](https://docs.switchagents.ai/switch-rooms/getting-started/install-switch-console) with Claude Code as the provider, and a Telegram bot.

1. **KinCare API and data**: double-click `start_switch.bat`. The first run loads the real CDSCO alerts and 246k medicine brands (a few minutes).
2. **Telegram**: create a bot with @BotFather, **turn Group Privacy off**, then in Switch Console: Connectors → Telegram. Make a group, add the bot. ([Switch docs](https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps/telegram))
3. **Agents and room**: Switch Console → Templates → Import template → [`switch/kincare-room.template.yaml`](switch/kincare-room.template.yaml) → Use template. Set *KinCare folder* to this repository.
4. **Recall Watcher**: fill `switch/.env` (from [`switch/.env.example`](switch/.env.example)), then
   `api\.venv\Scripts\python switch\recall_watcher.py register`, add **kincare-recall-watcher** to the room in Console, and run `start_switch.bat` again.
5. **Try it**: in the group, send a strip photo with `@kincare-scan`, or run `api\.venv\Scripts\python switch\recall_watcher.py once`.

Demo data: [`switch/family.json`](switch/family.json) holds a simulated family. **The batch AT25-0938A and its alert are real** (CDSCO NSQ list, Sep 2026); the family and pharmacist are simulated.

## How it is built

```
 Telegram ──► Switch server (rooms, people, roles, documents) ◄── Switch Console runs Claude Code agents
                    ▲                                                 │  scan · pharmacist · dose
                    │ POST /agents/{id}/message                       │  (instructions: switch/agents/*/AGENT.md)
                    │                                                 ▼
          recall_watcher.py ──────────────► switch/kincare_cli.py ──► KinCare API (FastAPI, :8000)
          (custom protocol agent)            (one tool, stdlib only)   CDSCO alerts · OCR · 246k medicines
```

| Path | What |
|---|---|
| [`switch/`](switch/) | **New for this hackathon**: agent instructions, CLI, Recall Watcher, room template, tests |
| [`docs/SWITCH_NOTES.md`](docs/SWITCH_NOTES.md) | How Switch works and how KinCare uses it |
| [`api/`](api/) | KinCare API: CDSCO ingest, batch matcher, OCR, prices, care plans |
| [`web/`](web/) | KinCare web app (optional for the Switch workflow) |

Tests: `api\.venv\Scripts\python -m pytest switch -q` (Switch layer) and `cd api && .venv\Scripts\python -m pytest -q` (KinCare API).

## What is new for Flip the Switch

KinCare's API and web app began as our earlier project (Carely, HackIIITD 2026); see [docs/KINCARE_APP.md](docs/KINCARE_APP.md).
Everything that puts it in a team room is new and built during this hackathon: the four Switch agents and their
instructions, the custom protocol Recall Watcher, the agent CLI, the room template with its safety rules,
the decision and task workflow, and the tests in `switch/`.

## Data and safety

- Alerts: CDSCO public NSQ and spurious-drug portal plus monthly alert PDFs. Medicines: Indian Medicine Dataset (MIT).
- Batch numbers are matched exactly; a near miss never raises an alert.
- KinCare never says a medicine is "safe" or "genuine", only whether a batch is on an alert list.
- No agent ever advises stopping or switching a medicine. A human pharmacist or doctor approves.
- Health data stays in the family's room. Secrets (`switch/.env`, `api/.env.bat`) are git-ignored.
