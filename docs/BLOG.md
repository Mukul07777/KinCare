# We put a family, a pharmacist and four AI agents in one Telegram group. Here's how, with Switch.

*By Mukul and Ashpreet Singh Saini (Team Avengers), for the Flip the Switch hackathon.*

My grandmother's medicine strip has a batch number on it. Somewhere in a government portal, that exact
batch may already be listed as "Not of Standard Quality". Nobody in our family would ever know.

We measured how often that happens. From 7,920 public alerts by CDSCO (India's drug regulator), a failed
batch reaches the list a median **10 months** after it was made, and **99.6%** of listed batches are still
within expiry when they appear. The medicine is still in homes. Nobody tells the people taking it.

We had already built the hard part, KinCare: a batch matcher over CDSCO data, OCR for strip photos, and a
246,000-brand medicine dataset. What it lacked was the *team*. Looking after an elder's medicines is never
one person: the elder takes them, a son in another city worries, a daughter buys them, the local pharmacist
knows what to swap. This post is how we used **Switch** to put all of them, plus four agents, in one chat,
and what we learned as first-time Switch users.

## What Switch is, in one paragraph

Switch is open source infrastructure that connects AI agents to team chat. Every chat channel becomes a
**room**: a shared log of messages, instructions, roles and documents that every person and every agent in
it reads from. Agents join a room like teammates, with their own name. You bring the agents (Claude Code,
Codex, your own code) and the chat app (Slack, Teams, Discord, Telegram, Mattermost); Switch connects them.
Switch Console, the desktop app, runs a local Switch server and your agents.

## The workflow we built

```
Dadi            [photo of a Namik-MR strip]  @kincare-scan
Recall Watcher  ⚠️ Batch AT25-0938A is on the CDSCO Not of Standard Quality list (Sep 2026).
                @kincare-pharmacist please find a replacement. Family: don't stop it on your own.
KinCare Pharm.  Same three salts, makers with no alerts: 1) StayHappi ₹2.70/tablet 2) Genericart ₹8.20
                @Pharmacist reply approve 1/2 or reject.
Rahul (son)     approve 1
KinCare Pharm.  Only the pharmacist can approve. @Pharmacist please confirm.
Pharmacist      approve 1
KinCare Pharm.  ✅ Decision logged. Task for @Rahul: buy StayHappi today.
KinCare Dose    दादी, कल सुबह 9 बजे से नई दवा: StayHappi, 1 गोली।
```

Four agents, each with one job:

| Agent | How it joins Switch | Job |
|---|---|---|
| kincare-scan | Claude Code, run by Switch Console | strip photo → batch → CDSCO check, Hindi first |
| kincare-pharmacist | Claude Code, run by Switch Console | same-salt options, asks the human pharmacist, records the decision |
| kincare-dose | Claude Code, run by Switch Console | dose schedule, missed-dose nudges |
| kincare-recall-watcher | our own Python code, speaking the Switch agent protocol | speaks first when a family batch is flagged |

## Step 1: Install Switch Console (and one gotcha on Windows)

Download Switch Console, choose **On this computer**, and it starts a local Switch server. It then asks for
an AI provider to power *switch-buddy*, its built-in assistant.

**Gotcha:** we use Claude Code inside VS Code, so Console reported Claude Code as "Not installed", and its
one-click install failed on Windows with a PowerShell `InvalidEndOfLine` error. The VS Code extension is not
the command-line tool Console looks for. Installing the CLI fixed it:

```
npm install -g @anthropic-ai/claude-code
```

Restart Console and pick Claude Code.

## Step 2: Connect Telegram (turn Group Privacy off first)

Make a bot with @BotFather (`/newbot`), keep the token private, and **before adding the bot to any group**:
`/mybots` → your bot → Bot Settings → Group Privacy → **Turn off**. If you skip this, the bot only sees
messages that tag it, and turning it off later doesn't fix groups it already joined.

In Console: **Connectors → Telegram**, paste the token and username. Then make a Telegram group, add the bot,
and say hi. The group appears under **Your Rooms**. Two things that surprised us:

- Switch can't *create* Telegram chats. The room exists once the bot is in the group.
- A direct message with the bot doesn't make a room. Use a group, even a group of two.

## Step 3: Agents as Claude Code + a folder + instructions

The nicest discovery: most agents need **no protocol code at all**. In Console, an agent is a coding agent
(Claude Code here) running in a **directory** you choose. Switch starts it when someone @mentions it.

So each KinCare agent is just a folder:

```
switch/agents/kincare-pharmacist/
  AGENT.md     # who you are, the flow, the never-do list
  CLAUDE.md    # one line, "@AGENT.md", so Claude Code loads it automatically
```

and one shared tool, `switch/kincare_cli.py`, a standard-library Python script that talks to the KinCare
API and prints JSON. The pharmacist's instructions say: run `kincare_cli.py replacements <batch>`, offer up to
three options, ask the pharmacist, and only on their "approve" write to the room's *KinCare Decisions* document.

**Lesson: move safety-critical logic out of the prompt and into code.** Our first version asked the agent to
"pick alternatives with the same salts". Testing on real data, the cheapest "same salt" option for Namik-MR
(aceclofenac + paracetamol + chlorzoxazone) turned out to contain a *different* third drug, because the
medicine dataset sometimes drops a salt. Now `replacements` checks every salt against the product name too,
filters by form and by makers with zero CDSCO alerts, and has tests. The agent explains; the code decides
what is allowed on the list.

## Step 4: One template for the whole room

Switch templates are YAML. Ours creates the three Claude Code agents and, depending on one choice:

- **Telegram group:** the agents join the group you already made, or
- **New rooms:** a *group* of two linked rooms, "Sharma Family Care" and "Sharma Pharmacy Desk", with roles
  (`elder`, `caregiver`, and an exclusive `pharmacist`), three pre-made room documents
  (*KinCare Decisions*, *KinCare Tasks*, *KinCare data sources*) and room rules every agent reads.

The rules are the product: *never tell anyone to stop or switch a medicine; only the pharmacist approves;
Hindi first; hand off by @name; write decisions to the shared document.*

**Tip:** Switch Console ships a template linter. We ran Switch's own `lint_template` and `compile_v2` on our
file before importing it. The compiler caught an error the linter didn't (a group needs a `name`).

Import it: Console → **Templates → Import template** → Use template.

## Step 5: A custom agent that speaks first

The three Claude Code agents answer when asked. A recall alert can't wait to be asked, so the Recall Watcher
is our own process speaking the **Switch agent protocol**:

1. `POST /agents` with a registration key → `{id, api_key}` (the key is shown once; keep it).
2. `POST /agents/{id}/message` with `{room_id, content}` to post, no connection needed.
3. For two-way: a WebSocket at `/agents/{id}/connection/ws?connection_id=<uuid>&rooms=<ids>&filter=addressed`.
   The server sends `ping`; answer `{"type":"pong","cursor":n}`. Messages arrive as `message` events with
   `payload.addressed`, `payload.body` and `room_id`.

Every 10 minutes it checks the family's batches against the alert store and posts once per new match. When
someone writes `@kincare-recall-watcher check`, it checks on the spot.

## What made Switch essential, not decoration

Take Switch away and KinCare is a one-person app again. What Switch gave us:

- **People and agents in the chat the family already uses**, each with a name and a role.
- **Handoffs in the open**: watcher → pharmacist agent → human pharmacist → dose agent, all visible.
- **One shared record**: decisions and tasks live in room documents, not in someone's memory.
- **Mix and match**: Claude Code agents and our own Python agent in the same room.

## Try it

- Repo: github.com/Mukul07777/KinCare
- No Telegram? `api\.venv\Scripts\python switch\demo_local.py` plays the whole room in your terminal on real
  data (you are the pharmacist).
- Real: the CDSCO alert for batch AT25-0938A and the medicine data. Simulated: the family and the pharmacist.

If you build with Switch, our three tips: install the Claude Code CLI before Console asks for it; turn
Telegram Group Privacy off before adding the bot; and put anything safety-critical in a tested tool, not in
the agent's prompt.
