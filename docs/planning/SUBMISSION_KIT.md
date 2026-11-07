# Submission kit (Nov 7)

## 1. Demo video: 2 min 30 s, one take for the core loop

Setup first: Switch Console running all 4 agents, KinCare API on :8000, Telegram desktop with "Sharma Family Care"
and "Pharmacy Desk" groups, a real strip of Namik-MR (or the printed `web/public/test-strips/namik-mr.png`).

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | CDSCO alert PDF, then the stat: 7,920 alerts, 99.6% still within expiry, median 14 months left | "When a medicine batch fails a government test, the list comes out ten months later, and nobody tells the families still taking it." |
| 0:15–0:30 | Switch Console: the 4 agents, the room, its roles | "KinCare puts the family, their pharmacist and four AI agents in one Switch room. Nothing changes until a human approves." |
| 0:30–1:00 | Telegram: Dadi's photo of the strip, `@kincare-scan` replies in Hindi + English, batch flagged | "The scan agent reads the exact batch and checks it against the real CDSCO list." |
| 1:00–1:30 | Pharmacist agent proposes 2 replacements with prices; the real pharmacist types `approve 1` | "The agent proposes. The pharmacist decides." (pause on this moment) |
| 1:30–1:50 | Task to Rahul, "done, bought", dose agent posts the new schedule | "The task and the schedule follow the decision." |
| 1:50–2:10 | Room documents: Decisions and Tasks updated | "Everyone reads the same record: an audit trail for free." |
| 2:10–2:25 | Pharmacy Desk room: blast radius across families | "One flagged batch, every home it reached, in the pharmacist's own room." |
| 2:25–2:30 | Repo URL + "Built on Switch" | |

Tips: 1080p, zoom the Telegram font, hide notifications, no background music over speech. Upload unlisted on
YouTube; put the link as the first line under the README title.

## 2. Screenshots for the README (save in `docs/img/`)

1. `room-chat.png`: the Telegram chat from the scan to `approve 1`
2. `console-agents.png`: Switch Console with the 4 agents
3. `room-documents.png`: Decisions and Tasks documents
4. `pharmacy-desk.png`: the blast radius message

Then paste under the README title:

```markdown
**[▶ Watch the 2-minute demo](VIDEO_URL)**

| Family room | Pharmacy Desk | Room documents |
|---|---|---|
| ![](docs/img/room-chat.png) | ![](docs/img/pharmacy-desk.png) | ![](docs/img/room-documents.png) |
```

## 3. Track 03 (core contribution): only with an assigned issue

Only pull requests for issues labelled `hackathon` and **assigned to you** are judged, and they must be open by
Nov 7, 11:59 PM IST. Low-effort PRs (typos, docs only, unreviewed AI output) are not judged. With hours left, try
this only if one of us already has an issue assigned. Otherwise put the time into the video.

## 4. Posting checklist

- [ ] Video uploaded, link in README
- [ ] Screenshots in README
- [ ] Blog published (Medium / dev.to / Hashnode), link in README
- [ ] #HowISwitch post on LinkedIn and X by both teammates, with a 30 s clip, tagging Switch
- [ ] Submission form: repo, video, blog, track 01
