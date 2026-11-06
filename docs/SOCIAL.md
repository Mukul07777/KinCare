# #HowISwitch posts (drafts)

Attach the demo video clip (or a screenshot of the Telegram group). Replace the links before posting.

## X / Twitter (single post)

A failed medicine batch takes ~10 months to reach India's CDSCO list, and 99.6% are still in date when they do.
Nobody tells the family.

We built KinCare on Switch [tag Switch's official handle; check it first]: Dadi, her kids, their pharmacist and 4 AI agents in one Telegram group.
Strip photo → recall alert → pharmacist approves → task done.

#HowISwitch #FlipTheSwitch @WeMakeDevs
[video] [repo link]

## X / Twitter (thread)

1/ My grandmother's medicine strip has a batch number. That exact batch might already be on a government
"failed quality" list. We'd never know. So we measured it: 7,920 CDSCO alerts, median 10 months to listing,
99.6% still in date. 🧵 #HowISwitch

2/ Looking after an elder's medicines is a team job: the elder, a son in another city, a daughter who buys
them, a local pharmacist. So we put all of them, plus 4 AI agents, in one Telegram group with Switch.

3/ The agents: Scan (reads the strip photo), Recall Watcher (speaks first when a batch is flagged),
Pharmacist (finds the same salts from makers with no alerts), Dose Buddy (Hindi reminders).

4/ The rule that matters: no agent ever tells anyone to stop or switch a medicine. Only the human pharmacist
approves, and that approval is what gets logged in the room's Decisions document.

5/ Three of the agents are Claude Code in a folder with instructions. The fourth is our own Python code on the
Switch agent protocol, because a recall alert can't wait to be asked.

6/ Repo + 2-minute local demo (no Telegram needed): [repo link]  Built for #FlipTheSwitch by @WeMakeDevs

## LinkedIn

**We put a family, their pharmacist and four AI agents in one Telegram group.**

India's drug regulator publishes batches that failed quality tests. We analysed 7,920 of those alerts: a
failed batch reaches the list a median 10 months after it was made, and 99.6% are still within expiry when
listed. The medicine is still in homes, and nobody tells the people taking it.

For the Flip the Switch hackathon we turned our medicine-safety project, KinCare, into a team workflow on
Switch (open source infrastructure for agents in team chat):

📸 Dadi sends a photo of her strip.
⚠️ The Recall Watcher agent flags the exact batch against real CDSCO data.
💊 The Pharmacist agent finds the same three salts from makers with no alerts on record.
✅ The human pharmacist approves. The decision and the task land in the room's shared documents.
🗓️ The Dose agent tells Dadi, in Hindi, what her new strip looks like.

Agents do the legwork; people decide. What I learned: put safety-critical logic in tested code, not in the
agent's prompt. Our first "same salt" suggestion turned out to be a different medicine because the dataset
had dropped a salt. Now the code checks it, with tests.

Repo and a 2-minute local demo: [link]
Built with Ashpreet Singh Saini.

#HowISwitch #FlipTheSwitch #AIagents #HealthTech #India
