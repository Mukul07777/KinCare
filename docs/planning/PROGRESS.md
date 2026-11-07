# KinCare: Build Plan & Progress Tracker

> **KinCare: know the batch, not just the brand.**
> Drug recall system for India. Scan a medicine strip or a pharmacy bill, live agents check every regulator alert source, and if a batch gets flagged, the patient gets a WhatsApp message and a Hindi voice call.

**Team Avengers:** Mukul (Team Lead) · Ashpreet Singh Saini
**Event:** Flip the Switch 2026 · ~30 hours · relay workflow (one codes, other rests)
**Powered by:** TinyFish Agent API

---

## How to use this file

- Tick a box when done: `- [ ]` → `- [x]`
- Update the **Progress Dashboard** numbers at the end of every shift.
- Write the shift log at the bottom before pushing.
- **Never push broken code to `main`.** Unfinished work goes on a branch.
- Claude sessions: read this file first, then `HANDOFF` section of the latest shift log.

**Status legend:** ✅ done · 🟡 in progress · ⬜ not started · ❌ cut / dropped · 🔥 blocker

---

## 📊 Progress Dashboard

| Area | Status | Done / Total | Progress |
|---|---|---|---|
| 0. Pre-hackathon prep | 🟡 | 1 / 14 | `█░░░░░░░░░` 7% |
| 1. Repo & infra setup | 🟡 | 6 / 12 | `█████░░░░░` 50% |
| 2. Alert database & PDF parser | 🟡 | 12 / 15 | `████████░░` 80% |
| 3. TinyFish agent ingester | 🟡 | 9 / 12 | `████████░░` 75% |
| 4. Matcher engine | 🟡 | 9 / 10 | `█████████░` 90% |
| 5. Scan flow | 🟡 | 9 / 13 | `███████░░░` 69% |
| 6. Verdict UI & watchlist | 🟡 | 11 / 12 | `█████████░` 92% |
| 7. Manufacturer trust score | 🟡 | 4 / 7 | `██████░░░░` 57% |
| 8. WhatsApp + Hindi voice call | 🟡 | 8 / 13 | `██████░░░░` 62% |
| 9. "Ask the regulator" chat | 🟡 | 6 / 9 | `███████░░░` 67% |
| 10. Visual pack check | ⬜ | 0 / 8 | `░░░░░░░░░░` 0% |
| 11. Pharmacy dashboard | 🟡 | 9 / 11 | `████████░░` 82% |
| 12. Live command screen | 🟡 | 7 / 10 | `███████░░░` 70% |
| 11b. Business & revenue | 🟡 | 3 / 5 | `██████░░░░` 60% |
| 13. Stretch features | 🟡 | 4 / 8 | `█████░░░░░` 50% |
| 15. Early Signal: patients as sensors | 🟡 | 12 / 15 | `████████░░` 80% |
| 16. Next innovative build | ⬜ | 0 / 7 | `░░░░░░░░░░` 0% |
| 17. Payments, SOS, admin, vitals trends | 🟡 | 12 / 14 | `█████████░` 86% |
| 18. Purchase loop, interactions, demo | 🟡 | 6 / 7 | `█████████░` 86% |
| 19. Live vitals + Doctor connect | 🟡 | 13 / 14 | `█████████░` 91% |
| 20. Same medicine, lower price | ✅ | 7 / 7 | `██████████` 100% |
| 21. Pack QR / Data Matrix scan | 🟡 | 6 / 7 | `█████████░` 86% |
| 22. Competitor parity (info, refill, push, Jan Aushadhi) | 🟡 | 12 / 14 | `█████████░` 86% |
| 23. Real WhatsApp (free) + fair pricing | 🟡 | 8 / 10 | `████████░░` 80% |
| 24. Business model enforced + polish & focus | 🟡 | 12 / 13 | `█████████░` 92% |
| 25. Recall blast radius + body signal | ✅ | 8 / 8 | `██████████` 100% |
| 26. Real number, phone login, deploy kit, pitch | 🟡 | 6 / 10 | `██████░░░░` 60% |
| 14. Demo, pitch & submission | 🟡 | 2 / 16 | `█░░░░░░░░░` 13% |
| 27. WhatsApp photo check (no app needed) | ✅ | 6 / 6 | `██████████` 100% |
| 28. Dadi mode: ask in Hindi, hear the answer (removed 24 Oct, rebuilt in §34) | ✅ | 7 / 7 | `██████████` 100% |
| 29. Fake-pack radar (copied QR codes) | ✅ | 7 / 7 | `██████████` 100% |
| 30. Drug-controller dashboard | ✅ | 6 / 6 | `██████████` 100% |
| 31. Judge mode (/stage), removed 24 Oct for a cleaner product | ❌ | 6 / 6 | `██████████` 100% |
| 32. Hard test + reliability fixes | ✅ | 5 / 5 | `██████████` 100% |
| 33. Measured engineering depth + navigation | ✅ | 7 / 7 | `██████████` 100% |
| 34. Dadi chat + Family caregivers (consent) + free Telegram | 🟡 | 11 / 12 | `█████████░` 92% |
| 35. Hard test of §34 + fixes | ✅ | 8 / 8 | `██████████` 100% |
| **TOTAL** | 🟡 | **265 / 365** | `███████░░░` **72%** |

### Team contribution (git, no merges)

| Member | Commits | Lines added | Share |
|---|---|---|---|
| Mukul | 55 | ~17,400 | `███████░░░` 69% |
| Ashpreet | 13 | ~7,900 | `███░░░░░░░` 31% |

_Recounted 25 Oct from `git log --numstat`, excluding data/, *.json, *.lock, *.pptx, *.png (generated files), so both rows use the same method._


### 🆕 Latest updates (newest first, read this first, Mukul)
| When | Who | What changed | Where |
|---|---|---|---|
| 25 Oct | Ashpreet | **📸 Real-photo OCR: batch + expiry 100% on all 4 real strips** (Disprin, Dolo-500, Dolo-650, Paracip-500; was 3/4 batch, 2/4 expiry). (1) Every photo is scaled to 2000 px (WhatsApp sends 1280 px, too small for thin edge print; 4000 px camera photos were slow and timed out the /api proxy after 30 s → "Request failed (500)"); sideways passes read at 2560 px, which finds Paracip's `B.No.JCHT6539 … EXPIRY DATE JUN.29`. (2) Batch clean-up: `DFNY0223MFG` → `DFNY0223`, `D0BS4480` → `DOBS4480` (a 0 between letters is O). (3) Brand: warning/price/toll-free lines are never the brand; `Dol0-500` → `Dolo-500`; a name+strength printed twice (`PARACIP-500`) wins even inside merged lines. (4) WhatsApp/Telegram photo replies and `bench_strips.py` now use `ocr.scan` (with the sideways read), same as the app. (5) Web proxy timeout raised to 120 s. **Benchmark, real: 5 photos, batch 100%, expiry 100%, brand 80%** (Disprin's brand is a logo; it reads the salt). Labels typed from the photos in `tests/strips/labels.csv`. **Open:** a sideways strip takes ~15–40 s on a laptop CPU (3 OCR passes) | `api/ocr.py`, `api/bench_strips.py`, `api/routes/whatsapp_bot.py`, `web/next.config.ts`, `api/test_ocr_fields.py` |
| 25 Oct | Mukul | **📸 Real Dolo-650 strip now reads.** It found no batch because batch, expiry and MRP are printed **sideways** along the edge. Now: if the upright read finds no batch, KinCare reads the photo turned 90° both ways; accepts `No. DOB…` / `XP.APR.2030` when the B / E is cut off at the edge (never `Mfg. Lic. No.`); a name printed 3+ times on the foil is the brand (`Dolo-650`, not `olo-650Dol0-650 Over d`); "Made in India" is never the brand. **O/0, I/1, S/5, B/8 misreads** no longer silently miss a recall: they show as a **possible** match telling the user which character to check. Same photo: before nothing, now batch + expiry + brand. 212 tests, OCR benchmark still 5/5. Also fixed a 500 on /result (a test server had overwritten the built site) | `api/ocr.py`, `api/matcher/core.py`, `web/components/ResultView.tsx` |
| 25 Oct | Mukul | **🐟 TinyFish live agents fixed and verified with a real key.** Bug: with `TINYFISH_API_KEY` set, every live recall returned **zero rows**, because the SDK puts the answer in `result_json`, not `result`. Fixed; a real run now reads the newest CDSCO alert (Alzomac-0.5, batch 60098, Sep 2026). **Ashpreet: put the TinyFish key in your own `api\.env.bat` (`TINYFISH_API_KEY=`, never commit it; ask Mukul) and restart `run.bat`; /live then uses TinyFish agents.** No Supabase needed: SQLite + our own sessions, roles and encryption cover it | `api/agents.py` |
| 25 Oct | Mukul | **🛂 Role-based access control.** Every account is a **patient**; **pharmacist**, **regulator** and **admin** are granted, never assumed. Roles map to permissions (`api/roles.py`), and each of **25 professional endpoints** asks for one (`core.require`). **Closed real leaks found while doing it:** `/api/notifications` gave anyone every customer's name, phone and message; `/api/blast/{batch}` gave anyone the names, phones and next doses of everyone holding a flagged batch; anyone could run a recall, fetch alerts, message a typed-in number, or use any pharmacy endpoint. Now: pharmacists see only their own shop's customers, regulators see holders (phones masked in the message log), and only admins seed demo data or message a demo number. **Request → approve → revoke:** a signed-in user asks on Account (pharmacy + drug licence, or office + officer ID), an admin approves on /admin, and a revoke cuts the same session off at once. Admin can't be requested and nobody approves themselves. **Audit log** of every role decision, every look at batch holders, alerts and recalls (account ids shown as masked phones). Locked pages explain why and offer the request form. Also fixes the blast page's Alert / Demo buttons, which had needed an admin token since the last security change. **11 RBAC tests** (incl. one that calls all 25 endpoints as every role) + a 17-step browser test with pharmacist, regulator and admin: all pass. **210 API tests pass.** **Ashpreet: on your laptop (`run.bat`, demo mode) a role request is approved at once; open /account, sign in, press "I'm a pharmacist"** | `api/roles.py`, `api/core.py`, `api/routes/*`, `api/test_rbac.py`, `web/components/RoleGate.tsx`, `web/app/admin`, `web/app/account`, `docs/SECURITY.md` |
| 25 Oct | Mukul | **🔐 Security & privacy for medical data, rebuilt.** Users are **no longer identified by a device id**: the browser used to send an id and the server trusted it, so knowing someone's id gave you their prescriptions. Now: **server-issued 256-bit sessions** in an **HttpOnly SameSite cookie**, stored only as hashes, expiring and revocable; account ids never leave the server. The site calls `/api` on its **own origin** (Next.js forwards it), so CORS is locked to configured origins and **CSRF** is blocked (forged POST with a real cookie → 403). **Closed 3 more holes:** login codes were returned on screen whenever WhatsApp wasn't set up (anyone could sign in as any phone) → now only with `KINCARE_DEMO=1`; admin trusted `127.0.0.1` (every visitor once proxied) → always needs `ADMIN_TOKEN`; unsigned WhatsApp webhooks and a simulator taking any phone number could tick anyone's doses → signature required, simulator pinned to a sandbox number. Plus: **AES-256-GCM encryption at rest** for chats, doctor messages and diagnoses; **sharing needs a verified phone**; rate limits; security headers + CSP; **Signed-in devices** list and sign-out-everywhere on Account. **`docs/SECURITY.md`** lists every protection, its test, and what is still open. **18 security tests** (`test_security.py`, incl. one that checks all 60+ personal endpoints refuse a request without a session) + an 18-step browser test as two people: all pass. **198 API tests pass.** **Ashpreet: after pulling, run `run.bat` once** (it sets `KINCARE_DEMO=1`, makes an admin token and rebuilds the site); sign in with your phone on /login before using Family | `api/sessions.py`, `api/vault.py`, `api/core.py`, `api/main.py`, `api/routes/*`, `web/next.config.ts`, `web/lib/api.ts`, `docs/SECURITY.md` |
| 25 Oct | Mukul | **🏆 Ashpreet's 75/100 review, every point addressed.** (1) **Flaky test fixed at the root:** /status counted 503 "payments not configured" as a crash (judges would have seen "1 server error" after anyone pressed Pay); the refill test was a Windows clock-tick race, fixed with strictly increasing timestamps (25/25 runs). (2) **CI:** `.github/workflows/ci.yml` runs all API tests + web typecheck/lint/build on every push; green on GitHub. (3) **main.py split** (2,500 lines) into `core.py` + 22 files in `api/routes/`, generated mechanically so no line was lost; verified identical route order (124) and startup hooks; deprecated `@app.on_event` replaced by a lifespan (0 warnings). (4) **Privacy / DPDP Act:** found and fixed a real leak: browsers with storage blocked all used device id "anonymous", i.e. **one shared account for strangers' health data**; now a per-tab random id, and the server refuses shared ids. Added **Download my data** + **Delete all my data** (Account), retention limits, and a plain-language **/privacy** page. (5) **Focus:** top bar is now one story, Scan · Care · Dadi mode · Family; the other 20 pages sit under **More**. Fixed a home-page crash on an empty database. (6) **OCR benchmark:** `api/bench_strips.py` on human-labelled photos, real vs synthetic never mixed, shown on /status. Synthetic demo prints: 5/5. **Real phone photos: not measured yet, needs 20+ photos of real strips** (`api/tests/strips/real/README.md`). **177 API tests pass** | `.github/`, `api/core.py`, `api/routes/`, `api/privacy.py`, `api/bench_strips.py`, `web/components/Nav.tsx`, `web/app/privacy`, `web/app/account`, `web/app/status` |
| 25 Oct | Mukul | **📲 Telegram does everything WhatsApp does (free) + bot is live: @KinCareDadiBot.** Strip **photo** → batch read by OCR + checked; batch numbers; **"1"** after a dose ticks it; **dose reminders** (for every scheduled dose, no purchase needed, with tap-to-tick buttons); refill reminders; **recall alerts** (bought batch flagged, watchlist batch newly flagged, recall blast); purchase confirmations. One helper `alert_device()` = phone notification + Telegram, used at every alert point. **Connect fix:** t.me's "Start bot" does nothing on a laptop without the Telegram app, so the button now opens a panel: **QR to scan with the phone**, **Telegram Web**, or type `/start CODE`; it turns green by itself once linked. Also fixed a flaky refill count (Windows clock tick). 7 new tests (`test_telegram.py`), **171 API tests pass** (only the Stripe test fails without a key). Token lives in `api\.env.bat` (git-ignored) | `api/main.py`, `api/telegram.py`, `components/TelegramConnect.tsx` |
| 25 Oct | Mukul | **🗂️ Repo tidied.** Top level now holds only README, PROGRESS, run.bat, dev.sh, render.yaml, `api/`, `web/`, `data/`. Guides moved to **`docs/setup/`** (DEPLOY, TELEGRAM_SETUP, WHATSAPP_SETUP), BUSINESS + DATASETS to **`docs/`**, handoffs to **`docs/handoffs/`**, decks + scripts to **`pitch/`**. Every link and mention updated; README has the full folder map. Keys: `api\.env.bat` (git-ignored), template `api\env.example.bat`; run.bat creates the keys file and rebuilds the web app after a pull | `README.md`, `docs/`, `pitch/`, `run.bat` |
| 25 Oct | Mukul | **🧪 Hard test of Dadi + Family, 7 real bugs fixed.** (1) "दवा ले लीजिए" (*please take it*) and "abandoned" were ticking doses: intents now match whole words only. (2) "Betadine" was alerting the son ("beta"): same fix. (3) 00:00–00:59 would have reported every dose of the new day as missed to caregivers. (4) After ~23:15 "dawa le li" couldn't tick the 21:00 dose. (5) **Demo-breaker:** Dadi chat always spoke as "Me", so Papa's BP / "call my son" never reached Papa's caregiver; now defaults to the member who has a caregiver, with a "Who is talking?" picker. (6) Live camera/watch vitals never alerted caregivers. (7) **Render runs UTC**, so 08:00 IST reminders (old WhatsApp ones too) would fire 5½ h late: `TZ=Asia/Kolkata` in render.yaml. Plus the SOS screen showed caregiver alerts as "WhatsApp sent". **55 new edge-case tests** (`test_caregiver_hard.py`) + a two-browser run (Papa + son, desktop + 390 px phone). **164 API tests pass** (only failure: the Stripe test, needs a Stripe key) | §35, `api/voice.py`, `api/caregiver.py`, `api/main.py`, `render.yaml`, `app/dadi`, `app/family`, `app/sos` |
| 25 Oct | Mukul | **👵 Dadi mode is back, as a real chat** (/dadi). Conversation history, big bubbles, mic + spoken replies (slower voice, mute toggle), today's doses pinned on top with one-tap tick. KinCare now **acts**, not just answers: "मैंने दवा ले ली" ticks the dose, "बीपी 140 बटा 90" / "bukhar 101" logs vitals (°F → °C) and grades them, "बेटे को बुलाओ" alerts the family, emergencies say 108 first and alert SOS caregivers. Same chat on Telegram | §34, `api/voice.py`, `api/main.py` (dadi_turn, `/api/dadi/*`), `app/dadi/page.tsx` |
| 25 Oct | Mukul | **👨‍👩‍👦 Family: caregivers with consent** (/family). Elder makes a 6-letter code and ticks exactly what to share (doses · vitals · SOS); consent checkbox required. Caregiver sees the scopes before accepting. Dashboard: today's doses (taken / not taken / later), 7-day adherence %, 7-day bars, latest vitals + BP trend, medicine list, send a reminder (lands in Papa's Dadi chat + phone, max 5/h). Alerts: dose unticked 1 h after its time, urgent reading, SOS (once each). Elder sees an **access log** (every look, reminder, alert) and can **stop sharing** instantly; caregiver can never change medicines/readings. Links survive phone login | §34, `api/caregiver.py`, `/api/caregiver/*`, `app/family/page.tsx` |
| 25 Oct | Mukul | **💬 Telegram = the free channel.** WhatsApp bills every message outside the 24 h window; Telegram's Bot API is free at any volume, no window, no template approval. Elder chats with KinCare there; caregivers get alerts there. Long-polls, so it works from a laptop with no public URL. **Needs a bot token**: see docs/setup/TELEGRAM_SETUP.md (keys go in `api\.env.bat`) | §34, `api/telegram.py`, `components/TelegramConnect.tsx`, docs/setup/TELEGRAM_SETUP.md |
| 24 Oct | Ashpreet | **✨ Professional, premium UI pass.** Judge mode (/stage) removed; "Install app" button removed and the browser's install banner suppressed (KinCare is a website; push notifications still work). Header is now: Families · Pharmacies · Regulators menus, search, Sign in, one **Check a batch** button (SOS stays in the Families menu and as the phone button). Home page is one flow: hero → recall gap → how it works (3 steps) → built for families / pharmacies / regulators → real data → CTA. Every page heading moved from Title Case to sentence case. Deck slide 7 now walks through /demo | `web/components/Nav.tsx`, `web/app/page.tsx`, `web/components/Pwa.tsx`, all page headings, `pitch/KinCare_Pitch_Deck.pptx` |
| 24 Oct | Ashpreet | **🎤 Pitch deck for the evaluation** (13 slides, speaker notes = the spoken script): problem → solution → **Workflow** (PDF to phone, 3 live journeys) → **MVP execution** (8 live features, judge-mode demo plan) → **Technical feasibility & architecture** (diagram, measured accuracy + latency chart, unit economics + risks) → **Progress** (229/333 tasks, next 30 days) → **Team contribution** (git-attributed ownership) → close. Every number is from the repo or /api/status | `pitch/KinCare_Pitch_Deck.pptx` |
| 24 Oct | Ashpreet | **⚙️ Engineering depth, measured.** (1) **Matcher benchmark on the real alert table** (`api/quality.py`): 2,400 typed variants of 400 real flagged batches → 100% caught; 798 near-miss + clean batches → 0 false alarms. It exposed a real bug: a different company sharing "Pharmaceuticals"/"Laboratories" scored as a *strong* maker match (25 of 399). Maker matching now compares the distinctive words → 0 of 399, same maker still 99.7%. Enforced by `test_quality.py`. (2) **Latency under 32 parallel clients: p95 12,098 ms → 33 ms, p99 14,910 → 43 ms.** Controller/stats/datasets/insights/recall-gap cached until the alert table changes, single-flight fills, warmed at startup; medicine search on an FTS5 trigram index (90 → 8 ms, identical results). Recall-gap cache never refreshed after an ingest: fixed. (3) **Nightly ingest really scheduled** (02:00 IST, `ingest_runs` log, failures logged not raised). (4) **/status "Under the hood"** page: live accuracy, p50/p95/p99, slowest routes, data freshness, ingest history. (5) **Nav by audience** (Families / Pharmacies / Regulators mega-menus) from one route registry `web/lib/routes.ts`, plus **⌘K / "/" command palette** to every page; footer grouped the same way. **103 API tests** | `api/quality.py`, `api/matcher/core.py`, `api/controller.py`, `api/prices.py`, `api/timeline.py`, `api/main.py`, `web/app/status`, `web/components/Nav.tsx`, `web/components/CommandPalette.tsx` |
| 24 Oct | Ashpreet | **🧪 Hard test + fixes.** (1) **API crashed under parallel load:** one sqlite connection shared by every request thread; 15 of 240 parallel requests returned 500 (`/api/controller`, `/api/blast/...`). Now one connection per thread (`db.ThreadConnection`, autocommit): 0 of 600 fail. (2) First `/demo` after a restart took 23 s (one openFDA call hit its 15 s timeout); labels for all common brands now warm in the background at startup, demo runs in ~5 s. (3) Branded 404 and error pages (were Next's black screen). (4) "Failed to fetch" → "Can't reach the KinCare server…" everywhere; /controller no longer spins forever when the API is down. (5) "Medicine not found. Run: python -m ingest…" no longer shown to users | `api/db.py`, `api/main.py`, `web/app/not-found.tsx`, `web/app/error.tsx`, `web/lib/api.ts`, `web/lib/pharmacy.ts`, `/controller` |
| 24 Oct | Ashpreet | **🎬 Judge mode (/stage):** the whole pitch as one full-screen, dark, keyboard-driven tour on live data, so we never hop between 7 pages on stage. 8 scenes: title → 10-month gap → WhatsApp bot (real reply) → Dadi mode (real Hindi answer, spoken) → blast radius (seeds holders, one-click alert, dots turn teal) → fake-pack radar (seeds ring, route draws across India) → controller KPIs + action queue → business + "KinCare vs pharmacy apps vs govt portal" table. → / Space next, ← back, F full screen, `?s=4` jumps to a scene. Linked from the home hero ("Judge Mode · 3-min tour") and the footer | §31, `app/stage/page.tsx`, `globals.css` (scene-in) |
| 24 Oct | Mukul | **🏛️ Drug-controller dashboard (/controller):** state selector (by testing lab), KPIs (alerts 12 m +49% y/y, fakes, critical, 10-month median lag, holders alerted, copied codes, signals), ranked **action queue**, 18-month trend, what fails / drug groups / makers, flagged batches still in homes, PvPI + signal exports, one-click labelled demo data | §30, `api/controller.py`, `/api/controller`, `app/controller/page.tsx` |
| 24 Oct | Mukul | **🛡️ Fake-pack radar (/radar):** every QR scan with a pack serial is logged (location rounded ~1 km). Same serial far apart within a day, on many phones, or with a different batch = **copied code**; the scan result warns, the radar draws the route on a map. Demo ring sits on the /scan QR test code, so a judge scanning it gets the warning | §29, `api/packs.py`, `/api/packs/*`, `app/radar/page.tsx`, `components/QrScan.tsx` |
| 24 Oct | Mukul | **🎙️ Dadi mode (/dadi):** one giant button, ask in Hindi or English, KinCare answers out loud: price + cheapest clean brand, what a medicine is for, today's doses, batch check, emergency → 108. Hindi brand names (डोलो, क्रोसिन) matched by sound. Nav: Scan · WhatsApp · Dadi · Care · Save · Recall · Pharmacy (Signals moved to footer) | §28, `api/voice.py`, `/api/voice/ask`, `app/dadi/page.tsx` |
| 24 Oct | Mukul | **📷 Send a strip photo on WhatsApp, get the verdict:** KinCare downloads the photo, reads the batch (OCR), checks every alert, replies in Hindi/English, warns if expired. **/whatsapp** page = same bot on an on-screen phone (works without Meta keys, for stage) | §27, `api/main.py` (whatsapp_photo_reply, /api/whatsapp/simulate), `api/whatsapp.py`, `app/whatsapp/page.tsx` |
| 24 Oct | Ashpreet | **📊 The real number for slide 1:** from 6,172 real CDSCO alerts, a failed batch reaches the list a **median 10 months** after it was made, and **99.5%** are still in date when listed (**14 months** of shelf life left). Shown on the home page ("Ten months in homes") | §26, `api/timeline.py`, `/api/insights/recall-gap`, home page |
| 24 Oct | Ashpreet | **📱 Phone login:** 6-digit code on WhatsApp, one account per number on any phone, data from a new phone merges in. Without WhatsApp keys the code shows on screen (demo mode). Nav shows "Sign in" / your masked number | §26, `api/auth.py`, `/login`, Nav, Account |
| 24 Oct | Ashpreet | **🚀 Ready to deploy:** `render.yaml` (API + 1 GB disk, builds the DB on first boot), Vercel steps, checklist in **docs/setup/DEPLOY.md**. **🎤 Pitch rewritten:** 3-min single story + judges' Q&A + backup-video shot list in **pitch/PITCH_SCRIPT.md** | §26, docs/setup/DEPLOY.md, pitch/PITCH_SCRIPT.md |
| 24 Oct | Ashpreet | **🔥 New headline innovation: Recall blast radius (/blast, "Recall" in nav).** For a flagged batch: everyone holding it (Care purchases, pharmacy sales, watchlists) on a radar by time to their next dose; one button alerts them soonest-dose first; **body signal** compares each holder's vitals before vs after starting the batch ("9 of 26 show resting pulse up"). Patient sees their own "since starting this batch" card in Care. Demo link from /demo's recall step | §25, `api/blast.py`, `app/blast/page.tsx`, `components/BodySignal.tsx` |
| 24 Oct | Ashpreet | **Business model made real:** plans now enforced (member + WhatsApp limits), 14-day Family trial for every new user, pharmacy first month free, **pharmacy pays → its customers get Basic free** (growth loop). Yearly plans no longer expire after 31 days (bug). docs/BUSINESS.md rewritten with worst-case profit per plan | §24, `api/entitlements.py`, docs/BUSINESS.md, /pricing |
| 24 Oct | Ashpreet | **Polish + focus:** fixed blank cards site-wide (`.card` overrode coloured backgrounds: Family plan card, home stats, revenue card were invisible); nav cut to Scan · Care · Save · Pharmacy · Signals + teal Demo button; plan badge on Care/Account; clear WhatsApp messages after purchase | §24, `globals.css`, `Nav.tsx` |
| 24 Oct | Ashpreet | **Plans explained clearly:** each plan lists exactly what it includes and stacks on the one before (Free → Basic → Family → Pharmacy → Pro). **Pharmacy Pro = every KinCare feature** ("All features" badge) | §23, `api/billing.py`, /pricing, /account |
| 24 Oct | Ashpreet | **Prices:** Basic ₹29, Family ₹69 (yearly = 2 months free), Pharmacy ₹499, Pro ₹1,499. Paid WhatsApp capped at 50/number/month so every plan profits | §23, `api/billing.py`, `api/whatsapp.py`, /pricing, /account |
| 24 Oct | Ashpreet | **Real WhatsApp (Meta Cloud API)**, free setup: reply "1" ticks the dose, send a batch number to get the alert check. Needs keys, see docs/setup/WHATSAPP_SETUP.md | §23, `api/whatsapp.py` |
| 24 Oct | Ashpreet | **/demo checked end to end on real data** + 3 new steps (tablets counted, ₹ saving, alert on judge's phone); recalled medicine now Namik-MR; price matching fixed (Warf 5mg, Crocin 500) | §22, /demo, `api/prices.py` |
| 24 Oct | Ashpreet | **Competitor features:** medicine info page, refill reminders, install as app + phone notifications, Jan Aushadhi finder | §22 |
| 24 Oct | Ashpreet | **Setup for existing machines:** `api\.venv\Scripts\pip install pywebpush`, `cd web && npm install && npm run build` | Shift 2 log |

**Ashpreet, start here (25 Oct, from Mukul):** `git pull origin main`, then `api\.venv\Scripts\pip install -r api\requirements.txt` and `cd web && npm run build`. Try it with two browsers (normal = Papa, incognito = son): Papa opens **/family → Someone looks after me**, picks Papa, ticks consent, makes a code; son opens **/family**, enters the code, accepts; Papa goes to **/dadi** and types or says "BP 190/120" and "beta ko bulao"; the son's dashboard shows it, the son sends a reminder, it appears in Papa's chat. **Still open on §34:** create the Telegram bot (5 min, docs/setup/TELEGRAM_SETUP.md) and test phone notifications on a real phone (needs HTTPS: the deployed Vercel/Render URLs or a cloudflared tunnel; iPhone needs "Add to Home Screen" first). Stage idea: two real phones, Papa speaks the BP, the son's phone buzzes.

**Previous shift:** 3 · **Who:** Ashpreet · **Updated:** 24 Oct 2026 · **Branch:** `main` (we both work on main now, no feature branches) · **Tests:** 103 API tests pass, web typecheck + production build pass, full crawl 0 errors (desktop + phone)
**Mukul, start here:** read **[docs/handoffs/HANDOFF_MUKUL.md](docs/handoffs/HANDOFF_MUKUL.md)** (everything from 24 Oct in one page). Then: (1) `git pull origin main`, restart the API once (startup now warms caches + builds the medicine search index, ~10 s). (2) Open **pitch/KinCare_Pitch_Deck.pptx**: 13 slides mapped to the evaluation (workflow, MVP, tech, progress, team), script in the speaker notes. (3) Press → through **/stage** once; it follows the deck's demo order. (4) **/status** is our answer to "is this real?". **Still open:** deploy (docs/setup/DEPLOY.md) and put the URL on slide 7, connect WhatsApp keys, record the backup video, state regulator sources (§3). Setup: `api\.venv\Scripts\pip install -r api\requirements.txt`, `cd web && npm install && npm run build`.
**Demo ready?** ✅ (local, `run.bat`) · **Core loop working (scan → match → alert)?** ✅ · **Real data:** 6,865 CDSCO alerts, 246,068 medicine prices, 53 ICU patient recordings, openFDA labels. See [docs/DATASETS.md](docs/DATASETS.md)

---

## 🎯 The Idea (one-minute version)

### Problem
- CDSCO flags **~170–280 drug samples a month** as NSQ (Not of Standard Quality) or spurious.
- FY 2025-26: **3,012 NSQ + 283 spurious** out of 1.41 lakh samples (~2.3%).
- Risk is **batch-level**. One bad batch does not make the brand bad, only the batch number tells you.
- Findings sit in **monthly PDF lists** on regulator portals. Patients never see them. **India has no consumer drug recall system.**

### Solution
1. **Scan** a medicine strip or a pharmacy bill → OCR reads brand, batch, maker, expiry → user confirms.
2. **Check** against a nightly-refreshed database of every alert, built by TinyFish agents reading regulator PDFs and portals.
3. **Verdict** with the regulator's own link: "Alert found" or "No alert found as of <time>". **Never says "safe".**
4. **Watch** the batch. When a new list drops and the batch is flagged → **WhatsApp + Hindi voice call** to the patient.

### The winning demo moment: "60-second recall"
On stage: a new CDSCO list arrives → agents parse it live → match against pharmacy sales → **a judge's phone rings** with a Hindi voice that can answer questions → map lights up. Timer stops: *"A recall that takes months took 52 seconds."*

---

## 🏗️ Architecture

```
┌──────────────┐   ┌──────────────┐   ┌───────────────────┐   ┌────────────────────┐
│  Next.js PWA │──▶│ Vision OCR   │──▶│ FastAPI backend   │──▶│ TinyFish Agent API │
│ scan / chat  │   │ strip + bill │   │ matcher, scoring  │   │ 1 agent per source │
│ dashboards   │   └──────────────┘   │ trust score, chat │   │ JSON rows back     │
└──────┬───────┘                      └────────┬──────────┘   └─────────┬──────────┘
       │ realtime                              │                        │
       ▼                                       ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Supabase (Postgres + Realtime + Storage)                                      │
│ alerts · sources · manufacturers · users · watchlist · pharmacies · sales     │
└──────────────────────────────────────────────────────────────────────────────┘
       │ new match on a watched/sold batch
       ▼
┌──────────────────────────────────────┐
│ Notifier: Twilio WhatsApp + Voice     │
│ Hindi TTS/STT (Sarvam AI) + LLM agent │
└──────────────────────────────────────┘
```

### Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui | Fast to build, PWA camera support |
| Backend | FastAPI (Python) | PDF parsing + AI libs are Python |
| DB | Supabase (Postgres + Realtime + Storage) | Free, realtime events for command screen |
| Agents | TinyFish Agent API | Regulator sources are PDFs/portals with no API |
| PDF parsing | pdfplumber, LLM fallback for messy tables | Deterministic first, auditable |
| OCR | Vision LLM | Reads foil strips and bills |
| Notify | Twilio WhatsApp sandbox + Voice | Real phone rings on stage |
| Voice | Sarvam AI (Hindi TTS/STT) | Natural Hindi |
| Map / graph | react-leaflet / react-force-graph | Visual wow |
| Deploy | Vercel (web) + Render/Railway (API) | Free tiers, public demo URL |

### Repo structure (planned)

```
kincare/
├── PROGRESS.md            ← this file
├── README.md
├── .env.example
├── dev.sh                 ← one command to run everything
├── web/                   ← Next.js app
│   ├── app/scan/          ← strip + bill scan flow
│   ├── app/result/        ← verdict screen
│   ├── app/watchlist/
│   ├── app/ask/           ← "Ask the regulator" chat
│   ├── app/pharmacy/      ← pharmacy dashboard
│   └── app/live/          ← command screen (demo)
├── api/                   ← FastAPI
│   ├── parsers/           ← CDSCO / state PDF parsers
│   ├── agents/            ← TinyFish source goals
│   ├── matcher/           ← normalise + score
│   ├── notify/            ← WhatsApp + voice
│   └── chat/              ← regulator Q&A
├── data/
│   ├── raw_pdfs/          ← downloaded alert PDFs
│   └── seed/              ← demo pharmacy, patients, sales
└── docs/
    └── BatchGuard.pdf     ← Round 1 idea deck
```

---

## 🗄️ Data model (draft)

| Table | Key columns |
|---|---|
| `sources` | id, name, url, type (cdsco_nsq / cdsco_spurious / state / manufacturer / bulletin), last_checked_at |
| `alerts` | id, source_id, product_name, batch_no, batch_norm, manufacturer, manufacturer_norm, reason, category (NSQ / spurious), alert_month, alert_url, pdf_page, raw_row (jsonb), created_at |
| `manufacturers` | id, name_norm, alias[], alert_count, spurious_count, last_alert_at, trust_score |
| `users` | id, name, phone, language (hi / en), role (patient / caregiver / pharmacy) |
| `watchlist` | id, user_id, product_name, batch_no, batch_norm, manufacturer, added_at, last_verified_at, status |
| `scans` | id, user_id, image_url, ocr_json, confirmed_json, verdict, matched_alert_ids[], created_at |
| `pharmacies` | id, name, city, state, lat, lng |
| `stock` | id, pharmacy_id, product_name, batch_no, batch_norm, qty |
| `sales` | id, pharmacy_id, user_id, product_name, batch_no, sold_at |
| `notifications` | id, user_id, alert_id, channel (whatsapp / voice / sms), status, sent_at |
| `events` | id, type, payload (jsonb), created_at ← feeds live command screen |

**Batch normalisation rule:** uppercase, strip spaces / `-` / `/` / `.`, map `O→0`, `I→1`, `S→5` only when the OCR confidence is low. **Match = exact `batch_norm` + same manufacturer (fuzzy).** Fuzzy only on brand and maker names, never on batch.

---

## ✅ Task Checklist

### 0. Pre-hackathon prep (before hour 0)
- [ ] Confirm hackathon rules on pre-built code vs accounts/data prep
- [ ] TinyFish account + API key, run one test call
- [ ] Twilio account, WhatsApp sandbox joined, voice tested
- [ ] Twilio top-up (~$20) so it can call unverified numbers
- [ ] Sarvam AI (or other Hindi TTS/STT) key, test one Hindi sentence
- [ ] Supabase project created
- [ ] LLM API key for OCR / chat
- [ ] Vercel + Render/Railway accounts
- [x] Download last 12 months of CDSCO NSQ + spurious alert PDFs into `data/raw_pdfs/`
- [ ] List 5 alert source URLs (CDSCO NSQ, CDSCO spurious, 2 state regulators, 1 bulletin)
- [ ] Get a real strip from a flagged batch (or best available)
- [ ] Reference photos of 2–3 genuine packs for visual check
- [ ] Ashpreet added as GitHub collaborator
- [ ] Both laptops: Node, Python, git, Claude Code working

### 1. Repo & infra setup — Shift 1 (Mukul)
- [x] Monorepo with `web/` and `api/`
- [x] `.gitignore` (node_modules, .env, __pycache__, .venv)
- [x] `.env.example` with every key name (no real values)
- [x] Next.js + Tailwind + shadcn/ui scaffold
- [x] FastAPI scaffold with `/health`
- [ ] Supabase client in both web and api
- [ ] DB schema migration (all tables above)
- [x] `dev.sh` runs web + api with one command
- [ ] README with setup steps
- [ ] Deploy web to Vercel (empty shell)
- [ ] Deploy api to Render/Railway (`/health` live)
- [ ] CORS + env vars working in deployed versions

### 2. Alert database & PDF parser — Shift 1 (Mukul)
- [x] Inspect PDF formats (table layout, columns, multi-page tables)
- [x] pdfplumber table extraction for CDSCO NSQ format
- [x] Parser for CDSCO spurious format
- [x] Handle multi-line cells and page breaks
- [ ] LLM fallback for tables pdfplumber can't read
- [x] Extract: product, batch, manufacturer, reason, month, source URL, page
- [x] Batch normalisation function + unit tests
- [x] Manufacturer name normalisation (Ltd/Limited/Pvt, punctuation)
- [x] Load 12 months of alerts into `alerts`
- [ ] Spot-check 50 random rows against the PDF by hand
- [ ] Record extraction accuracy % (for pitch)
- [x] Dedupe repeated rows
- [x] `GET /api/check?batch=&maker=&brand=` returns matches
- [x] `GET /api/alerts` with filters (maker, month, category)
- [x] Count stats endpoint (total alerts, by month, by state)

### 3. TinyFish agent ingester — Shift 2 (Ashpreet)
- [x] TinyFish client wrapper with retries + timeout
- [x] One goal per source, returns JSON: product, batch_no, manufacturer, reason, alert_date, link
- [x] Source 1: CDSCO NSQ page → find newest PDF link
- [x] Source 2: CDSCO spurious list
- [ ] Source 3–4: two state regulators
- [ ] Source 5: manufacturer notices / bulletin
- [x] Parallel fan-out (asyncio), total time = slowest agent
- [x] Upsert new rows into `alerts`, update `sources.last_checked_at`
- [x] Emit `events` rows for live screen (agent started / found N / done)
- [x] Capture live stream URL for UI
- [x] Nightly scheduled run (02:00 IST in the API, logged in `ingest_runs`)
- [ ] **Replay mode:** recorded run that streams the same events (demo fallback)

### 4. Matcher engine — Shift 2 (Ashpreet)
- [x] Exact match on `batch_norm`
- [x] Fuzzy manufacturer match (rapidfuzz, threshold tuned)
- [x] Fuzzy brand match as supporting signal only
- [x] Score breakdown returned (batch / maker / brand) so verdict is auditable
- [x] Confidence levels: strong match / possible match / no match
- [ ] Never "possible match" on batch alone
- [x] Tests with 20 real flagged batches (must all match): benchmark uses 400 real batches × 6 spellings, 100% caught (`test_quality.py`)
- [x] Tests with 20 clean batches (must not match): 798 near-miss + clean batches, 0 false alarms
- [x] Re-check all watchlist + stock batches when new alerts land
- [x] Trigger notifier on new match

### 5. Scan flow (strip + bill OCR) — Shift 2 (Ashpreet)
- [x] Camera capture page (mobile PWA)
- [x] Upload from gallery fallback
- [x] Vision OCR on strip → brand, salt, batch, maker, expiry + confidence
- [x] Vision OCR on pharmacy bill → list of items with batch numbers
- [x] Confirm screen: user edits fields before check runs
- [x] Manual entry fallback (type batch)
- [ ] Read barcode / QR if present
- [x] Store image + OCR JSON in `scans`
- [x] Loading state showing sources being checked
- [ ] Test on 10 real strips (record accuracy)
- [ ] Test on 3 real bills
- [x] Error handling (blurry photo, no batch found)
- [ ] Works on phone over deployed URL

### 6. Verdict UI & watchlist — Shift 2 (Ashpreet)
- [x] "ALERT FOUND" screen (red): reason, month, regulator link, "Stop use. Ask your pharmacist or doctor."
- [x] "NO ALERT FOUND as of <time>" screen (teal) + "This is not a safety guarantee."
- [x] Per-source rows: match / no match
- [x] Last verified timestamp
- [x] "Open regulator notice" button (PDF link + page)
- [x] "Watch this batch" → saves to watchlist
- [x] Watchlist page with status per batch
- [x] Phone number + language capture (for alerts)
- [x] Bill scan result: list view, one verdict per medicine
- [x] Hindi / English toggle
- [ ] Elder mode: big text, big buttons, read-aloud verdict
- [x] Mobile layout polished

### 7. Manufacturer trust score — Shift 2 (Ashpreet)
- [x] Aggregate alerts per manufacturer
- [ ] Score formula: count, spurious vs NSQ weight, recency decay
- [ ] Store in `manufacturers.trust_score`
- [x] Show badge on verdict screen ("7 alerts in 18 months")
- [x] Manufacturer detail page with alert history
- [ ] "Rising risk" rule: same salt + maker failing in 2+ states in 60 days
- [x] Clear disclaimer: based only on public regulator alerts

### 8. WhatsApp + Hindi voice call — Shift 3 (Mukul)
- [x] Twilio WhatsApp message on new match (template with regulator link)
- [x] Hindi + English message templates
- [x] Twilio outbound voice call
- [x] Hindi TTS audio for alert script
- [x] Voice script: medicine, batch, regulator, action ("upyog band karein")
- [ ] **Talk-back:** patient asks a question, STT → LLM → TTS reply
- [ ] Voice agent answers ONLY from the regulator notice (grounded)
- [x] Log every send in `notifications`
- [x] "New alert" trigger endpoint for demo
- [x] End-to-end: trigger → match → phone rings (test 5 times)
- [ ] Fallback: SMS if WhatsApp fails
- [ ] Rate limit / no duplicate alerts
- [ ] Test with a non-team phone number

### 9. "Ask the regulator" chat — Shift 4 (Ashpreet)
- [x] Chat UI page
- [x] Natural language → SQL / filter over `alerts` (safe, read-only)
- [ ] Answers in Hindi or English
- [x] Every answer cites source PDFs with links
- [x] Example chips: "Has <maker> had failed batches this year?"
- [ ] Refuses medical advice, points to doctor
- [x] Handles "no results" honestly
- [x] Test 15 questions, note failures
- [ ] Linked from verdict screen ("Ask about this maker")

### 10. Visual pack check — Shift 4 (Ashpreet)
- [ ] Reference image store for genuine packs
- [ ] Vision model compares scanned strip vs reference
- [ ] Output differences: logo, font, colour, alignment
- [ ] Shown as **"risk hint"**, never a verdict
- [ ] Side-by-side view with highlighted differences
- [ ] Works for the 2–3 demo brands
- [ ] Disclaimer text
- [ ] Graceful "no reference available" state

### 11. Pharmacy dashboard — Shift 4 (Ashpreet)
- [ ] Seed demo pharmacy, 50 patients, stock, sales in `data/seed/`
- [x] Stock table with batch status
- [ ] Invoice upload (photo/PDF) → OCR → stock rows
- [x] Review tasks: status flow (open → verifying → quarantined → returned → resolved), assignee, notes
- [x] Audit trail of every check/action + exportable recall report CSV
- [x] Flagged items highlighted red with alert link
- [x] "Patients who bought this batch" list
- [x] "Notify all" button → WhatsApp + voice to each
- [x] Notification status per patient
- [x] Summary cards (batches checked, flagged, patients notified)
- [x] CSV upload of stock as fallback

### 12. Live command screen — Shift 4 (Ashpreet)
- [x] Full-screen `/live` page for the projector
- [x] Big timer (start / stop)
- [x] TinyFish agent live view (or replay) panel
- [x] Realtime event stream from `events` (Supabase Realtime)
- [x] Steps light up: fetched → parsed → matched → notified
- [ ] India map with pharmacies lighting up where batch was sold
- [ ] Recall graph: maker → distributor → pharmacy → patient (synthetic, labelled)
- [x] Counter: patients notified
- [x] "Trigger new alert" hidden button for presenter
- [ ] Works offline in replay mode

### 11b. Business & revenue (see docs/BUSINESS.md)
- [x] docs/BUSINESS.md: positioning, customers, pricing, financial model, GTM, roadmap
- [x] /pricing page: tiers, live revenue calculator, unit economics, roadmap
- [x] Printable pharmacy return note (/return) from alert verdicts
- [ ] Interview 10 pharmacists (quotes for pitch)
- [ ] 1 letter of interest from a pharmacy / chain

### 13. Stretch features (only if ahead)
- [ ] WhatsApp bot: send photo → get verdict
- [x] Public "Drug Alert Index" dashboard (trends by maker / state / month)
- [x] Open API docs page
- [x] Report suspicious pack (photo + note) → cluster view
- [x] PvPI-style export of reports
- [ ] Voice-only elder mode ("point camera, hear answer")
- [ ] More languages (Tamil, Bengali, Marathi)
- [ ] PWA install + push notifications

### 15. Early Signal: patients as sensors (NEW, the headline innovation)
Regulator lists arrive months after a batch is sold. Patients notice in days. We pool anonymous symptom reports per batch and run the disproportionality test drug-safety agencies use, so a bad batch can be flagged **before** CDSCO lists it.
- [x] `reports` table, one report per device per batch (one phone can't stuff a signal)
- [x] `POST /api/reports` with symptom whitelist (EN + HI labels)
- [x] Check-in answers after a recall also feed the signal pool
- [x] PRR + Yates chi-square, Evans criteria (n ≥ 3, PRR ≥ 2, χ² ≥ 4)
- [x] Cluster fallback when there is too little background data, labelled in UI
- [x] Urgent level when 2+ people report red-flag symptoms
- [x] Cross-check against regulator DB: "not listed yet" vs "patients reported it first"
- [x] `/signals` page: live KPIs, signal cards, symptom bars with PRR, auto-refresh
- [x] Report form on every result page + standalone on /signals
- [x] PvPI / state drug controller draft CSV (`/api/signals.csv`)
- [x] Demo seeder `python -m simulate` (every row marked simulated; UI badge; `--clear`)
- [x] 4 tests (disproportion not volume, anti-stuffing, red-flag urgent, input validation)
- [ ] City map of signals
- [ ] Auto-draft email to the state drug controller when a batch turns "signal"
- [ ] Time-to-signal metric vs regulator listing date (pitch number)

### 16. Next innovative build (pick top-down)
- [ ] **TinyFish key in:** set `TINYFISH_API_KEY` in `api\.env.bat`, run /live, confirm agents show `tinyfish` (code path already done)
- [ ] TinyFish goals for 2 state regulators (Kerala, Maharashtra FDA) → section 3 sources 3–4
- [ ] **Rising risk rule:** same salt + maker failing in 2+ states within 60 days → warning on result
- [ ] **Batch Passport:** pharmacy prints a QR on each bill line; anyone scans it later and gets the live verdict
- [ ] Visual pack check as a "risk hint" (section 10)
- [ ] Elder mode: big text, read-aloud verdict
- [ ] Deploy (Vercel + Render) so check-in links and phones work outside localhost

### 35. Hard test of §34 + fixes (NEW, Mukul)
- [x] Intent words matched as whole words ("le lijiye" ≠ "le li", "betadine" ≠ "beta", "abandoned" ≠ "done")
- [x] No false missed-dose alerts 00:00–00:59; night dose tickable after 23:15
- [x] Dadi chat + Telegram speak for the member who has a caregiver; "Who is talking?" picker
- [x] Live (camera / watch) urgent vitals alert caregivers
- [x] Server clock: `TZ=Asia/Kolkata` in render.yaml (fixes the old WhatsApp reminder timing too)
- [x] SOS screen labels caregiver alerts correctly
- [x] 55 edge-case tests (`api/test_caregiver_hard.py`): words, midnight, scopes, other members private, expired/used/bad codes, revoke, re-accept, two caregivers, reminder limit, view-log throttle, login merge, Telegram junk, caregiver chat can't act as the elder
- [x] Two-browser UI run (Papa + son, desktop + 390 px phone): consent gate, scope preview, chat, dose tick, son sees urgent BP, reminder reaches Papa, access log, revoke cuts off, bad-code message, no sideways scroll

### 34. Dadi chat + Family caregivers + free Telegram (NEW, Mukul)
- [x] `/dadi` rebuilt as a conversation: saved history (app + Telegram in one thread), mic, spoken replies with mute, big bubbles, quick chips
- [x] Today's doses pinned on top of the chat, one-tap tick
- [x] Chat actions: "dawa le li" ticks the dose, spoken vitals logged and graded, "beta ko bulao" alerts family, emergency → 108 + SOS caregivers
- [x] `/family` elder side: invite code with chosen scopes + consent checkbox, list of caregivers, stop sharing, access log
- [x] `/family` caregiver side: code preview before accepting, dashboard (today, 7-day adherence, vitals + BP trend, medicines)
- [x] Caregiver reminders reach the elder (push, Telegram, read out in the Dadi chat), 5 per hour max
- [x] Alerts to caregivers: missed dose (1 h), urgent vitals, SOS, each sent once, all in the elder's access log
- [x] Telegram bot: link by one-time code, chat = Dadi mode, caregiver alerts; long-poll (no public URL) or webhook with a secret
- [x] Links follow phone login (auth.merge)
- [x] Tests: `test_caregiver.py`, `test_voice.py` restored
- [x] Real Telegram bot created (@KinCareDadiBot), with every WhatsApp feature (photo, batch, "1", reminders, recall alerts)
- [ ] Test phone notifications on a real phone over HTTPS (deployed URL or cloudflared tunnel)

### 33. Measured engineering depth + navigation (NEW, Ashpreet)
- [x] Matcher benchmark on the real alert table (`api/quality.py`, `test_quality.py`)
- [x] Fix: makers sharing only an industry word were a "strong" match (25/399 → 0/399)
- [x] p95 under 32 parallel clients 12,098 ms → 33 ms (cached aggregates, single flight, startup warm-up)
- [x] Medicine search on an FTS5 trigram index (90 → 8 ms, identical results)
- [x] Nightly ingest scheduled + `ingest_runs` log; recall-gap cache refreshes after an ingest
- [x] `/api/status` + `/status` page: live accuracy, latency, freshness
- [x] Nav grouped by audience from `web/lib/routes.ts` + ⌘K command palette

### 32. Hard test + reliability fixes (NEW, Ashpreet)
- [x] One DB connection per thread: 15/240 parallel requests failed with 500s, now 0/600
- [x] openFDA labels warmed at startup: first /demo 23 s → ~5 s
- [x] Branded 404 + error pages
- [x] Clear offline message instead of "Failed to fetch"; /controller Retry instead of endless spinner
- [x] No developer command shown to users on a missing medicine

### 31. Judge mode: the whole story on one screen (REMOVED 24 Oct: the product now speaks for itself; the deck carries the story)
Judges see 30 features across 25 pages; they remember one story. /stage tells it in 8 scenes without leaving the page.
- [x] `/stage`: full-screen dark deck over the site, progress bar with scene names, → / Space / ← / F / Esc, `?s=N` deep link for rehearsing or recovering mid-pitch
- [x] Every scene is live: stats + recall gap, `/api/whatsapp/simulate` reply, `/api/voice/ask` answer (spoken in Hindi on click), blast radius, pack radar, controller KPIs/trend/action queue
- [x] Blast and radar scenes seed their labelled demo data only when empty, once per visit (two seeds racing left a half-built ring); `/demo` → Reset demo data clears it
- [x] One-click "Alert N people · next dose first" in the blast scene; dots turn teal in order
- [x] Closing scene: business model + KinCare vs pharmacy apps vs govt portal comparison
- [x] Scene entrance is CSS, not JS, so a slow laptop can never leave a slide invisible. Linked from home hero + footer

### 30. Drug-controller dashboard: KinCare as public-health infrastructure (NEW, Mukul)
- [x] `api/controller.py` + `GET /api/controller?state=`: alerts by testing-lab state (insights.state_of), last 12 m vs previous 12 m, fakes, critical findings, median manufacture → listing lag (timeline.month_index), 18-month trend, top failures / drug groups ("Other" left out) / makers
- [x] Ground data joined in: flagged batches held by anyone (blast.flagged_with_holders + exposure), copied pack codes (packs.radar), symptom signals (signals.detect), urgent check-ins
- [x] **Action queue** ranked most urgent first (fakes + doses due within 24 h, copied codes, urgent signals), each linking to the blast radius / radar / signals / pharmacy page; simulated items labelled
- [x] /controller page: state dropdown, 7 KPI tiles, queue, trend bars, 3 ranked lists, "still in homes" table, PvPI + signals CSV, print, Load / Clear demo (24 simulated holders on Namik-MR AT25-0938A + the copied-code ring); footer link "For drug controllers"
- [x] Real numbers (all India): 2,468 alerts in 12 months (+49% vs the year before), 30 fakes, 113 critical findings in 24 m, wrong strength 1,474 / doesn't dissolve 1,166; 0.05–0.16 s
- [x] 1 test (`api/test_controller.py`, cleans up after itself). **85 API tests pass**

### 29. Fake-pack radar: every QR scan is a sensor (NEW, Mukul)
H2 QR codes carry a serial for ONE pack. Counterfeiters copy the code; copies give themselves away.
- [x] `api/packs.py`: `pack_scans` (device, serial, GTIN, batch, expiry, lat/lng rounded to 2 dp ~1 km, nearest city); signals: **far** (>50 km within 24 h on different phones), **mismatch** (same serial, different batch/expiry), **phones** (≥3 phones); level ok / watch / clone
- [x] `POST /api/packs/scan`, `GET /api/packs/radar`, admin `POST`/`DELETE /api/packs/demo`
- [x] /scan → QR: after reading a code with a serial, asks for location (optional) and shows "first scan" / "you scanned this before" / **"⚠️ this pack code looks copied"** with reasons + link to the radar
- [x] /radar: KPIs, dark India map (lat/lng projection, 24 reference cities), each copied serial drawn as an animated route in time order, detail card (reasons, scans/phones/cities, timeline, printed-batch mismatch), SIMULATED DEMO badge
- [x] Demo ring = the /scan QR test code (Telma H 05240198, real CDSCO spurious batch, serial TST0001): Delhi → Lucknow → Patna → Kolkata (tampered batch) → Ranchi → Varanasi in 20 h. **Stage:** /radar → Load demo ring → judge scans the test code with their phone → clone warning
- [x] 6 tests (`api/test_packs.py`), incl. "days apart is not flagged". **84 API tests pass**
- [x] Checked with headless Edge: map, route, card; card no longer depends on a fade-in

### 28. Dadi mode: ask in Hindi, hear the answer (NEW, Mukul)
For parents who will never use an app's menus.
- [x] `/dadi`: one 250 px mic button, हिंदी / English, browser speech recognition (hi-IN / en-IN) and a slower Hindi voice for the answer; big text; one-tap example questions; type instead; 108 always on screen
- [x] `api/voice.py` + `POST /api/voice/ask`: emergency first (साँस, chest pain, बेहोश → call 108 + SOS), greeting, batch check, today's doses, price (+ cheapest same-salt brand from a maker with no alerts), what it's for (salt + plain-Hindi common use + how many samples of that salt failed tests)
- [x] Hindi transcripts write brands in Devanagari: transliteration with schwa drop (थायरोनॉर्म → thayronorm), brand matched by **sound** on the first word (krosin = Crocin, ikosprin = Ecosprin, ऐ-loanwords पैन = Pan), spoken strength ranked first (name > salt)
- [x] Checked on the real DB: Dolo 650, Telma 40, Pan 40, Crocin, Zerodol, Glycomet 500, Ecosprin 75, Thyronorm 50, Amlong 5 all found from Hindi speech text, 0.1–0.3 s each
- [x] Common-use list (~60 salts → BP, sugar, thyroid…) is general information and says "take it only as your doctor advised"; never start/stop/switch advice
- [x] 4 tests (`api/test_voice.py`). **78 API tests pass**
- [x] Nav decluttered so it fits at 1280 px: Signals → footer, "Install" label only on wide screens

### 27. WhatsApp photo check: no app needed (NEW, Mukul)
Most families will never install a health app; everyone has WhatsApp.
- [x] Webhook accepts **photos** (image, or an image sent as a document): downloads from Meta's Graph API, OCR, batch check, reply in the patient's language; OCR runs after the 200 so Meta never retries
- [x] Reply: flagged → the full alert text; clean → "read from your photo: brand, batch, expiry… not on any list, as of today"; **expired strip → "don't take it, return it"**; unreadable → how to retake
- [x] `POST /api/whatsapp/simulate` (text or photo): the same bot without keys, nothing sent
- [x] **/whatsapp** page: WhatsApp-style phone, send test strips with one tap or upload a photo, quick replies "hi" / "1" / a batch; "WhatsApp" in the nav
- [x] Checked on the real DB: Namik-MR and Chymoral Forte photos → alert in Hindi; clean Amlodipine → not on any list
- [x] 3 tests (`api/test_wa_photo.py`): image parsing, expiry dates, photo → alert / clean. **74 API tests pass**

### 26. Score boosters: real number, phone login, deploy, pitch (NEW, Ashpreet)
- [x] **Recall gap** (`api/timeline.py`, `GET /api/insights/recall-gap`): reads every date shape on alerts (Aug-2025, 08/2025, 2025-08, Sept. 2024); median **10 months** manufacture → CDSCO listing (quarter take 15+), **99.5%** still in date when listed, median **14 months** shelf life left. Premium home section: 3 stats, to-scale timeline, histogram, link to blast radius
- [x] **Phone login** (`api/auth.py`): `POST /api/auth/start`, `/verify`, `GET /api/auth/me`. Codes hashed (HMAC), 10 min, 5 tries, 3 sends / 10 min, only the newest code works. One account device id per phone; a new phone adopts it and its own data merges in (every table with a `device` column). No WhatsApp configured → code returned + "demo mode" banner
- [x] `/login` premium page (value panel + 2-step form, 6-box code with paste/auto-advance, resend timer, success animation); Nav "Sign in" ↔ masked number; Account "Signed in as … · Sign out"
- [x] **Deploy kit:** `render.yaml` (Starter + 1 GB disk at /var/data, generated ADMIN_TOKEN + OTP_SECRET), `api/start.sh` (first boot builds DB in background, then restarts), **docs/setup/DEPLOY.md** (Render + Vercel + connect + pre-demo checklist + free tunnel option)
- [x] **pitch/PITCH_SCRIPT.md** rewritten: 3-minute single story (recall gap → /demo → blast radius → business), stage checklist, 90-second backup video shot list, judges' Q&A
- [x] 4 tests (`api/test_auth.py` 3 + recall gap 1). **71 API tests pass**
- [ ] **You:** deploy (docs/setup/DEPLOY.md, ~15 min, needs Render + Vercel accounts)
- [ ] **You:** Meta WhatsApp keys (docs/setup/WHATSAPP_SETUP.md) so codes + alerts really go out
- [ ] **You:** show KinCare to 2–3 chemists; get one "I'd pay ₹499" quote for the business slide
- [ ] **You:** record the backup video (Win+Alt+R) from the shot list

### 25. Recall blast radius + body signal (NEW, headline innovation, Ashpreet)
Regulators publish *which batch* failed. KinCare knows *who holds it*, *when their next tablet is due*, and *whether their body changed* since starting it.
- [x] `api/blast.py`: exposure from 3 sources (prescription purchases with dose schedules, pharmacy sales, watchlists), next untaken dose per holder (overdue = due now), ranked soonest first
- [x] **Body signal:** median vitals 14 days before starting the batch vs since (pulse +10, SpO₂ −3, systolic +15, temp +0.8 = flagged); batch level "X of Y holders with vitals changed, most often: resting pulse". Worded as "changed since", never "caused by"
- [x] `GET /api/blast` (inbox: flagged batches someone holds), `GET /api/blast/{batch}`, `POST /api/blast/{batch}/alert` (WhatsApp + phone notification, soonest dose first, never twice; admin-protected), `GET /api/care/batch-effects`
- [x] Demo seeding `POST /api/blast/{batch}/demo` (admin): simulated holders on a **real** CDSCO batch with prescriptions, ~85% adherence, vitals before/after (every 3rd shows a pulse rise); device ids `sim-…`, labelled in the UI, **never messaged**; `DELETE …/demo` clears
- [x] Premium UI `/blast`: dark recall-desk panel, animated radar (rings = 1 h / 6 h / 24 h / no schedule; red pulsing = dose within the hour; dashed ring = vitals changed; turns teal as alerts go out in order), KPIs, alert-order queue with countdowns, before→after vital bars, hover cards. Checked with headless Edge screenshots
- [x] Care > Today: "Since starting each batch" card with the patient's own before → after vitals
- [x] /demo recall step links to the blast radius for that batch; nav: Scan · Care · Save · **Recall** · Pharmacy · Signals
- [x] 4 tests (`api/test_blast.py`). **67 API tests pass**
- **Stage demo:** open `/blast?batch=AT250938A` → (if empty) "Load simulated holders" → "Alert N people · next dose first". Reset: Clear, then Load again

### 24. Business model enforced + polish & focus (NEW, Ashpreet)
- [x] `api/entitlements.py`: tiers free < basic < family < pharmacy < pharmacy_pro; `GET /api/account/entitlement`
- [x] 14-day Family trial for every new device (no card); `KINCARE_ALL_ACCESS=1` unlocks all for stage demos
- [x] Enforced: people per plan (free/basic 1, family+ 6 → HTTP 402 with an upgrade message) and WhatsApp reminder numbers (basic 1, family 3)
- [x] Safety never gated: a free user still gets the recall alert on WhatsApp at purchase; only routine reminders need a plan
- [x] **Pharmacy-sponsored Basic:** a phone on a paying pharmacy's sales gets WhatsApp reminders free ("covered by Sharma Medicos")
- [x] Pharmacy plans: first month free (Stripe trial); trials count as active (`no_payment_required`), in checkout confirm + webhook
- [x] Bug fixed: yearly plans were treated as expired after 31 days
- [x] Web: plan badge (trial days left / free) on Care + Account, trial lines and "How KinCare grows" on /pricing, plain-words WhatsApp result after purchase
- [x] **Polish:** `.card` moved into Tailwind's components layer: coloured cards (Family plan, home stats, revenue, safe/brown panels) were rendering blank. Checked with headless Edge screenshots (desktop + 500 px phone)
- [x] **Focus:** nav = Scan · Care · Save · Pharmacy · Signals + Demo button; Watchlist, Pricing, Live recall, How it works, Admin in footer
- [x] docs/BUSINESS.md: new pricing, growth loop, worst-case unit economics per plan, year-1 path
- [x] 5 tests (`api/test_entitlements.py`). **63 API tests pass**, web build passes
- [ ] Before the demo, either use a fresh browser (trial) or set `KINCARE_ALL_ACCESS=1` in `api\.env.bat` so nothing is gated on stage

### 23. Real WhatsApp (free) + fair pricing (NEW, Ashpreet)
- [x] **Meta WhatsApp Cloud API** (`api/whatsapp.py`): free setup, no Twilio markup; Twilio kept as fallback, voice calls still Twilio. Setup in [docs/setup/WHATSAPP_SETUP.md](docs/setup/WHATSAPP_SETUP.md)
- [x] Cost trick: free text inside WhatsApp's 24 h window, approved Utility template (~₹0.115 + GST) only outside it. Every reminder says "Reply 1 once taken"; the reply reopens the window
- [x] **WhatsApp bot** (`POST /api/whatsapp/webhook`, signature-checked): "1"/"le li"/"done" ticks the dose just reminded; a batch number gets the alert check back (stretch task "send batch, get verdict" done); "hi"/"JOIN" gets a welcome
- [x] "Say hi to KinCare on WhatsApp" button (Care tab + /demo), shown only when `WHATSAPP_NUMBER` is set
- [x] **New prices** (`api/billing.py`, one place): Free (scans, recall alerts, phone notifications) · **Basic ₹29/mo or ₹299/yr** (1 person) · **Family ₹69/mo or ₹699/yr** (6 members, WhatsApp for 3 numbers) · Pharmacy ₹499/mo or ₹4,999/yr · Pharmacy Pro ₹1,499/mo
- [x] **Clear packs:** Free (scans, alerts, recall WhatsApp + voice, info, cheaper brands, Jan Aushadhi, phone notifications, watchlist, SOS) → Basic adds WhatsApp reminders, refills, Rx scan, interactions, doctor link, report → Family adds 6 members, 3 WhatsApp numbers, SOS to family, family savings → Pharmacy adds stock matching, find customers, 300 recall alerts, check-in queue, exports → **Pro adds multi-location, 2,000 alerts, Early Signal, live recall screen, API, priority support = everything**
- [x] **Profit guard:** paid WhatsApp messages capped at 50 per number per month (`whatsapp.PAID_CAP`); past it, reminders go as free phone notifications; recall + SOS messages are never capped. Worst-case profit per month: Basic ₹18, Family ₹44, Pharmacy ₹440, Pro ₹1,180 (after WhatsApp, ~3% payment fee, infra). A test fails if any plan's worst-case WhatsApp cost goes over 40% of its price
- [x] /account monthly/yearly toggle; /pricing tiers + calculator + unit economics updated; admin MRR counts yearly plans as 1/12
- [x] 6 tests (`api/test_whatsapp.py`). **58 API tests pass**
- [ ] Create the Meta app, put keys in `api\.env.bat`, open a tunnel, verify webhook, and send "hi" from a real phone (see docs/setup/WHATSAPP_SETUP.md)
- [ ] Submit the `kincare_update` Utility template for approval

### 22. Competitor parity: medicine info, refills, phone notifications, Jan Aushadhi (NEW, Ashpreet)
What 1mg / PharmEasy / Medisafe / Sugam do that we didn't, each with a KinCare twist (batch alerts, clean-maker prices).
- [x] **Medicine info page** `/medicine/[id]` + `GET /api/medicines/{id}/info` (`api/medinfo.py`): uses, how to take, side effects, warnings, "do not take if", pregnancy, per salt, from the official US FDA label (openFDA, cached in `fda_info`). Indian salt names mapped (paracetamol → acetaminophen, etc.)
- [x] Info page also shows CDSCO alerts for that salt (with "scan your batch"), price rank, cheapest clean-record brand. Linked from /save ("Uses, side effects, warnings" + every alternative's name)
- [x] **Refill reminder:** "Tablets bought" on the purchase form (blank = one strip from the medicine dataset); tablets left = bought − doses ticked since; "Bought more" adds to what's left
- [x] WhatsApp + phone notification **once** when ≤ 3 days left, with the cheapest clean-record brand of the same salt; no reminder if the course ends first or for SOS medicines (`care.refill_status`)
- [x] Care > Today: "Tablets at home" card (left, days, bar, low → amber + link to /save); `GET /api/care/refills`
- [x] **Install as app (PWA):** `app/manifest.ts`, icons in `public/icons/`, service worker `public/sw.js`, "Install app" button in the nav when the browser offers it
- [x] **Phone notifications (Web Push, `api/push.py`):** "Turn on reminders" now also subscribes the phone; server pushes doses, refills, recall-at-purchase and watchlist batches that turn flagged, even with KinCare closed. VAPID keys auto-made in `data/vapid_private.pem` (or env `VAPID_PRIVATE_KEY_FILE` / `VAPID_PUBLIC_KEY`)
- [x] Dose reminders from the open tab and from the server share a tag, so no double notification
- [x] **Jan Aushadhi Kendra finder** (`api/stores.py`, `components/JanAushadhi.tsx`) on /save and the info page: nearest Kendras from OpenStreetMap with distance + directions, always with a Google Maps search fallback
- [x] 6 tests (`api/test_refill_info.py`): refill rules, purchase qty + refill adds up, refill message once with clean brand, info page data, push validation, store parse/sort/dedupe. **51 API tests pass**, web build passes
- [x] **/demo upgraded + verified end to end on real data** (6,865 alerts, 246k medicines): recalled medicine is now a readable real brand (Namik-MR, batch AT25-0938A, same as `test-strips/namik-mr.png`) instead of codes like "D5"; new steps "15 tablets counted at home" and "Same medicines, ₹1,206 a year less"; optional "Also alert this phone" sends the recall as a real notification
- [x] Prescription → price matching fixed: "Warf 5mg" → Warf 5 Tablet, "Crocin 500" → Crocin Advance (brand stem + strength checked against the salt). Dadi's demo saving went ₹50 → ₹1,206/yr. Test added (52 API tests)
- [ ] Test push on a real Android phone (needs HTTPS or localhost; deploy first, see section 16). iPhone: only after "Add to Home Screen", iOS 16.4+
- [ ] Public Overpass servers were overloaded on 24 Oct (timeouts / 504), so the finder fell back to the maps link. Re-test; if still flaky, load the official PMBJP Kendra list (data.gov.in) as a table

### 21. Pack QR / Data Matrix scan (NEW)
- [x] /scan → QR tab: live camera (ZXing, works on Windows Chrome too) + upload a photo; QR and Data Matrix
- [x] Parser for the 3 real shapes: GS1 element strings (raw/bracketed, FNC1/GS, symbology prefix), maker verification URLs + GS1 Digital Link, "Batch No:" text
- [x] Reads batch, expiry (red "expired, do not use" if passed), mfg, GTIN, serial; editable, then the normal alert check
- [x] Test codes with real flagged batches (labelled), and "show this code" so a judge scans it with their own phone
- [x] Honest limit shown: a QR can be copied onto a fake pack; KinCare checks the batch, it can't prove the pack is genuine
- [x] Checked: 7 code formats parse correctly; GS1 QR encode → decode round-trip keeps the GS separator
- [ ] Try on 3-4 real H2 packs (Dolo, Pan, Thyronorm...) and add any new format we see

### 20. Same medicine, lower price (NEW)
- [x] `python -m ingest.medicines`: Indian Medicine Dataset (MIT), 246,068 brands on sale with MRP, maker, pack, salts
- [x] Exact match only: same salts + strengths + dosage form incl. release type (SR never matches plain); compared per tablet / ml
- [x] Every maker linked to its CDSCO alert record (exact normalised name; 458 of 7,624 makers have alerts)
- [x] /save page: search, price strip (cheapest / median / dearest), "cheapest with no alerts", monthly + yearly saving at 1-3 a day
- [x] Care > Today: family's monthly medicine spend vs clean-record cheapest, per medicine, links into /save
- [x] Savings never point to a maker with alerts; generic-name lines priced at the median brand and marked "typical price"
- [x] 3 tests (pack/salt normalising, SR excluded + maker record, search + plan savings skip risky maker)
- Real numbers for the pitch: Telma 40 is ₹8.20/tablet, Telmisoft 40 ₹0.65 (92% less). Pan 40: 1,842 brands, clean one 93% cheaper.

### 19. Live vitals + Doctor connect (NEW)
- [x] Live vitals from Bluetooth heart-rate watches/straps (GATT 0x180D), straight from the browser, no app
- [x] Bluetooth pulse oximeter: standard PLX (0x1822, SFLOAT) + BerryMed fingertip protocol (SpO₂, pulse, pleth wave)
- [x] Phone-camera pulse (PPG): flash on, fingertip over lens, peak detection with a noise check before showing a number
- [x] Made-up demo stream replaced by **real data**: replay any of 53 real ICU patients (PhysioNet BIDMC, MIMIC-II, ODC-By), monitor pulse/SpO₂ at 1 Hz + pleth wave, "jump to worst minute"
- [x] `python -m ingest.bidmc`: downloads + caches BIDMC (resumable, retries; waveform optional per record because physionet.org is slow)
- [x] Camera-pulse algorithm mirrored in `api/ppg.py` and scored against the ICU monitor pulse on real pleth; score shown in the app. First result (5 patients, 466 twelve-second windows): **MAE 1.72 bpm, 100% within 5 bpm, answered 95% of windows**
- [x] Algorithm hardened: 30% peak floor (ignores dicrotic notch) + rhythm (autocorrelation) check so noise gets no number
- [x] Server judges on a 30 s median (one bad beat never alarms); saves one reading to history every 5 min per source
- [x] Doctor connect: private expiring link (24 h to 30 d), revocable, "opened by doctor" status, WhatsApp share
- [x] /doctor/[token] console: live pulse/SpO₂ charts (2 s), NEWS2 early-warning score (partial, says so), 24 h stats, history, medicines + adherence, openFDA interactions, open SOS with map
- [x] Two-way messages; doctor "Advice" goes straight into the patient's daily reminders; urgent shown in red
- [x] Video consult (Jitsi room derived from the token hash, token never leaves KinCare) + patient "request a consult"
- [x] 5 tests (NEWS2 bands, live median + history, link/messages/revoke/cross-device, PPG clean vs noise, BIDMC record)
- [ ] Try with a real Bluetooth watch/oximeter on Android Chrome before the demo

### 18. Purchase → dose loop, interactions, judge demo (NEW)
- [x] "I bought it": batch, expiry, maker, pharmacy, WhatsApp number per prescribed medicine (`/api/care/purchase`)
- [x] Batch checked against every alert at purchase; flagged → recall alert instead of reminder
- [x] WhatsApp "take your dose now" / "next dose at HH:MM" in Hindi or English
- [x] Background loop: WhatsApp at every dose time, never twice, skips doses already ticked
- [x] Drug-interaction check across a patient's medicines from openFDA labels (open data, cached), Indian brand → generic map
- [x] `/demo`: one-click patient journey with timer + WhatsApp phone mockup, uses a real CDSCO batch
- [ ] Real TinyFish key + Twilio sandbox set, demo rehearsed on deployed URL

### 17. Payments, SOS, admin, vitals trends (NEW)
- [x] Stripe Checkout (test mode), plans priced on the server (Family ₹49, Pharmacy ₹999, Pro ₹2,499 /month)
- [x] Payment confirmed by asking Stripe server-side (URL alone proves nothing) + optional webhook
- [x] /account page: plans, active plan, test-card hint, cancel handling
- [x] SOS: emergency contacts (max 5, +91 normalised), one-tap SOS with GPS location, latest vitals, current medicines
- [x] SOS delivery: Twilio WhatsApp if keys set, otherwise tap-to-send WhatsApp links
- [x] /sos page: 112 / 108 call buttons, nearest hospitals on maps, doctor card; SOS pill in nav + floating button on phones
- [x] Urgent vital reading offers "Call 108" and "Send SOS to family"
- [x] Vitals trend chart for temperature, oxygen, pulse, BP with red-flag lines
- [x] /admin: open SOS (resolve), urgent check-ins, urgent vitals, signals, users, MRR, revenue, payments, data freshness, fetch-alerts button
- [x] Admin protected by ADMIN_TOKEN (or this-computer-only when unset)
- [x] Nav simplified: Scan, Care, Watchlist, Pharmacy, Signals (Alerts, Insights, Ask, Pricing, API hidden from menus)
- [x] 5 tests (SOS message, phone validation, checkout without key, cross-device confirm blocked, admin token)
- [ ] Put a real `sk_test_` key in `api\.env.bat` and do one test payment for the demo
- [x] Gate Family features (members > 1, WhatsApp numbers) behind the active plan → done in §24

### 14. Demo, pitch & submission — Shift 5 (Both)
- [ ] Freeze features at hour 24, bugs only after
- [x] Demo script written (pitch/PITCH_SCRIPT.md + speaker notes in the deck)
- [ ] Seed data final, demo phone numbers verified
- [ ] Judge phone number flow tested
- [ ] Full rehearsal #1
- [ ] Full rehearsal #2
- [ ] Full rehearsal #3
- [ ] Full rehearsal #4
- [ ] Full rehearsal #5 (timed under 3 min)
- [ ] **Backup video** of full flow recorded
- [ ] Replay mode tested with Wi-Fi off
- [x] Slides: pitch/KinCare_Pitch_Deck.pptx (13 slides, mapped to the evaluation criteria)
- [ ] Numbers ready: alerts parsed, extraction accuracy %, OCR accuracy %
- [ ] README polished with screenshots + demo link
- [ ] Submission form filled, repo public, deployed URL live
- [ ] Phones charged, hotspot ready, laptop charger packed

---

## ⏱️ Relay Shift Plan (~30 hours)

| Shift | Who | Hours | Sections | Must be working at handoff |
|---|---|---|---|---|
| 1 | Mukul | 0 – 6 | 1, 2 | `/api/check` returns real matches from 12 months of alerts |
| 2 | Ashpreet | 6 – 12 | 3, 4, 5, 6, 7 | Scan a strip/bill in UI → see verdict + trust score |
| 3 | Mukul | 12 – 18 | 8 | Trigger an alert → a real phone rings in Hindi |
| 4 | Ashpreet | 18 – 24 | 9, 10, 11, 12 | Full 60-second recall demo runs end to end |
| 5 | Both | 24 – 30 | 14 (+13 if ahead) | Demo frozen, rehearsed, backup video saved |

**Golden rule:** if a feature is not working by the end of its shift, **cut it**. Never hand broken work to the next person.

### Cut order (if behind)
1. ❌ Stretch features (13)
2. ❌ Recall graph / map
3. ❌ Visual pack check (10)
4. ❌ Voice talk-back (keep one-way call)
5. ❌ Pharmacy invoice OCR (use CSV)

**Never cut:** PDF parser, matcher, scan → verdict, WhatsApp alert, live agent view (or replay).

---

## 🤝 Handoff Protocol

At the **end of every shift**:
1. All working code merged to `main`, half-done work on `wip/<name>` branch.
2. Tick boxes above + update Progress Dashboard.
3. Fill a shift log entry below (what works, what's broken, how to run, next task).
4. Any new env var added to `.env.example`. Real keys shared privately, **never committed**.
5. 15-minute call: show what works.
6. Push.

At the **start of every shift**:
1. `git pull`
2. Read the latest shift log.
3. Run `dev.sh`, confirm everything still works before writing code.
4. Start Claude Code session with: *"Read PROGRESS.md and the latest shift log, then continue."*

### Commit message style
`feat: cdsco nsq parser` · `fix: batch normalisation for O/0` · `chore: seed demo pharmacy` · `docs: update progress`

### Claude Pro usage tips
- Keep sessions focused on one section; start fresh sessions often.
- Heavy usage early (scaffold, parser), save some for late-night debugging.
- Paste the schema from this file instead of re-explaining.

---

## 🎤 Demo Script (3 minutes)

| Time | What happens | Who talks |
|---|---|---|
| 0:00 – 0:20 | **Hook:** "Last month CDSCO flagged 280 drug samples. How many patients were told? Zero." | Mukul |
| 0:20 – 0:50 | Ravi scans his mother's pharmacy bill → 4 medicines checked → trust score + visual hint | Ashpreet |
| 0:50 – 2:00 | **60-second recall:** start timer → "new CDSCO list" → agents browse live → batch matched → pharmacy patients found → **judge's phone rings** in Hindi → map lights up → stop timer | Mukul |
| 2:00 – 2:30 | "Ask the regulator": "Which other batches from this maker are flagged?" → cited answer | Ashpreet |
| 2:30 – 3:00 | **Scale + close:** alerts parsed, 8 lakh pharmacies, business model. "India has no drug recall system. We built one in 30 hours." | Mukul |

### Fallbacks
| If this fails | Do this |
|---|---|
| TinyFish slow / down | Replay mode button |
| Voice call fails | WhatsApp still arrives, show it |
| Wi-Fi dies | Phone hotspot → then backup video |
| OCR misreads | Edit on confirm screen (that's a feature) |

---

## 💼 Business Model

| Customer | Offer | Price idea |
|---|---|---|
| Patients & caregivers | Scan, watchlist, alerts | **Free forever** |
| Retail pharmacies (8–10 lakh in India) | Auto stock checks, patient recall | ₹299–499 / month |
| Hospitals & procurement | Batch audits, compliance reports | Subscription |
| E-pharmacies, insurers | Alert API, exposure tracking | Usage-based API |

---

## ⚠️ Honest Limits & Risk Mitigation

| Risk | Mitigation |
|---|---|
| False reassurance | Never says "safe". Shows "no alert found as of <time>" + sources checked |
| False alarm | Exact batch + maker match only; score breakdown shown |
| Fake copying a real batch number | Cannot detect from lists; visual pack check gives a hint only |
| OCR errors | User confirms before check runs; manual entry |
| Stale data | Nightly refresh + last-verified time on every result |
| Liability | Only regulator statements, always linked to source |
| Site changes | Plain-language agent goals, no CSS selectors |

---

## 📈 Pitch Numbers (fill during build)

| Metric | Value |
|---|---|
| Alert PDFs parsed | 24 PDFs (132 alert documents incl. portal months) |
| Total alert rows in DB | 6,865 (CDSCO NSQ 3,058 · state NSQ 3,756 · spurious 51), Jan 2019 – Sep 2026 |
| Manufacturers tracked | 3,040 in alerts · 7,624 in price data (458 linked to alerts) |
| Medicine brands priced | 246,068 on sale, 11,021 distinct salt combinations |
| Price gap, same salt + form | Telma 40 ₹8.20/tab vs ₹0.65 (92% less) · Pan 40: 1,842 brands, clean one 93% cheaper |
| Camera pulse accuracy (real ICU pleth, BIDMC) | MAE 1.72 bpm, 100% within 5 bpm, 95% of windows answered (5 patients) |
| PDF extraction accuracy (50-row spot check) | — % |
| Strip OCR accuracy (10 strips) | — % |
| Avg agent fan-out time (5 sources) | — s |
| Recall demo time (alert → phone rings) | — s |
| Pharmacists interviewed | — |

---

## 📝 Shift Log

### Shift 0 — Planning (Mukul)
- **Done:** Idea finalised, name chosen (**KinCare**), repo created, this tracker written.
- **Works:** —
- **Broken / blockers:** —
- **How to run:** —
- **Next task:** Finish Section 0 (pre-hackathon prep), then Shift 1.

### Shift 1 — Mukul (in progress)
- **Done:** FastAPI `/api/check` + batch matcher (exact batch, fuzzy maker/brand, 6 tests passing). Seed alerts (Telma H 05240198 is real, rest marked `demo`). Premium Next.js UI: landing page, scan page (camera/upload + confirm form + sample chips), live verdict page with staggered agent fan-out.
- **Works:** `./dev.sh` → open http://localhost:3000, scan → Telma H sample → ALERT FOUND.
- **UI v2:** switched to light premium theme (cream/brown). 6 pages: Home, Scan, Result, Alerts explorer, Watchlist (saved per device, re-check all), How it works.
- **Business build:** pharmacy recall desk (/pharmacy), pricing + revenue calculator (/pricing), return note (/return), `POST /api/inventory/check`, docs/BUSINESS.md.
- **Broken / blockers:** OCR not wired (manual entry for now). Watchlist is per-device (localStorage) until Supabase. No real DB yet (JSON seed).
- **How to run:** see top of `dev.sh` for first-time install, then `./dev.sh`.
- **New env vars:** `NEXT_PUBLIC_API_URL` (see `.env.example`).
- **Real data build:** CDSCO scraper (follows iframe PDF links) + pdfplumber parser → SQLite, 1,090 real alerts / 24 PDFs (Nov 2024–Jun 2025). Local OCR (RapidOCR) `/api/scan`. Watchlist + pharmacy state server-side per device. All sample data removed. 11 tests.
- **Recall build:** /live command screen (parallel agents via TinyFish SDK or direct fallback, SSE), Hindi/English WhatsApp + voice via Twilio (outbox + browser speech without keys), /ask regulator Q&A with citations, pharmacy customer sales + notify, watchlist phone/language, result Hindi toggle. Portal ingest: 6,865 alerts 2019→Sep 2026. 17 tests.
- **Add-ons build:** failure explainer (EN/HI, severity) on every match; /insights national dashboard (by failure type, drug group, form, testing state, critical findings); bill scan (/scan → Bill); family cabinet (member + expiry countdowns); post-recall check-in link in every WhatsApp alert → /checkin → triage (urgent/review/ok) → pharmacist queue on /pharmacy + PvPI CSV export; /care: vitals red flags (doctor-only advice, never medicines), prescription OCR → confirm → dose schedule + reminders + doctor's advice, printable doctor report; /developers API page. 23 tests.
- **Early Signal build:** patient symptom reports per batch → PRR/Evans signal detection → /signals page, report form on results, PvPI draft CSV, labelled simulator. Home page figures now computed live from the alert DB (were typed in). run.bat one-click launcher. 27 tests.
- **Payments + SOS + admin build:** Stripe test-mode checkout, /sos emergency (location, vitals, medicines to family), /admin ops panel, multi-vital trend chart, simplified nav. 32 tests.
- **Live vitals + Doctor connect build:** Bluetooth watch / oximeter / camera pulse / demo stream into /care Vitals; private doctor link with live console, NEWS2, adherence, interactions, two-way messages (advice joins reminders), video consult. Real ICU replay (PhysioNet BIDMC, 53 patients) instead of simulated vitals; camera pulse scored on real pleth. 41 tests.
- **Same medicine, lower price build:** 246k Indian brands; same salt+strength+form, per-tablet price, maker CDSCO record, family monthly savings. 44 tests.
- **Pack QR build:** /scan → QR tab reads the Schedule H2 QR / Data Matrix code (GS1, maker links, text) → batch + expiry → alert check; test codes a judge can scan with their phone. 44 API tests, 7 code formats checked.
- **Datasets doc:** [docs/DATASETS.md](docs/DATASETS.md) lists every dataset, what it powers, licence, how to load it.
- **Keys still needed for real delivery:** TINYFISH_API_KEY, TWILIO_*, STRIPE_SECRET_KEY, optional ADMIN_TOKEN (see .env.example).
- **Next task:** Hindi voice mode for elders, one-button stage demo, deploy (Render + Vercel), pitch deck. Scan 3-4 real H2 packs to confirm QR formats.
- **Old gap (fixed by portal ingest):** CDSCO moved NSQ alerts after Jun 2025 to a JS page; needs TinyFish agent to reach newer months.
- **Next task (old):** CDSCO PDF parser → load 12 months of real alerts; Supabase schema.

### Shift 2 — Ashpreet (24 Oct, competitor parity)
- **Done:** Section 22: medicine info page, refill reminders, install-as-app + phone push notifications, Jan Aushadhi finder. Also checked who our competitors are (CDSCO lists, govt QR, mPedigree, PvPI app, 1mg / PharmEasy / Truemeds, Medisafe, Marg ERP); substitutes, dose reminders and interactions we already had.
- **Works:** /save → pick a medicine → "Uses, side effects, warnings" → /medicine/[id]. Care → Today → "Turn on reminders" (asks permission + subscribes push) → buy a medicine with tablets bought → "Tablets at home" card. Nav shows "Install app" on Chrome/Edge.
- **Broken / blockers:** Jan Aushadhi live list depends on public OpenStreetMap servers, which were timing out today; the maps link always works. Push not yet tried on a real phone.
- **How to run:** `run.bat` as before, **but** existing setups need: `api\.venv\Scripts\pip install pywebpush` (new in requirements.txt) and `cd web && npm install` (QR packages from the last pull). Then rebuild web (`npm run build`).
- **New env vars (optional):** `VAPID_PRIVATE_KEY_FILE`, `VAPID_PUBLIC_KEY`, `VAPID_SUB` (mailto). Without them a key pair is created in `data/`.
- **Demo check (24 Oct):** replayed every /demo API call on a fresh real DB: prescription ✓, Warf+Ecosprin and Crocin+Warf interactions from openFDA ✓ (~6 s, first call fetches labels), clean purchase + Hindi WhatsApp ✓, tablets counted ✓, Namik-MR recalled batch caught ✓, savings ✓. All pages + manifest + sw.js return 200 on `next start`.
- **Heads-up:** on a fresh machine `python -m ingest.portal` once crashed with `UNIQUE constraint failed: documents.url` (government portal hiccup); re-running it finished cleanly with all 6,865 alerts. If a first run looks short of alerts, just run it again.
- **Next task:** deploy (HTTPS needed for push on phones), try push on Android, then the innovation list: recall "blast radius", vitals-vs-batch link, counterfeit radar (clone serials / impossible batches).

### Shift 2b — Ashpreet (24 Oct, WhatsApp + pricing)
- **Done:** Section 23. Real WhatsApp through Meta Cloud API with a reply-"1" bot, batch check by WhatsApp, new fair prices with yearly plans.
- **Works without keys:** everything falls back to the outbox like before; the "Say hi" button stays hidden.
- **To switch on real WhatsApp:** follow docs/setup/WHATSAPP_SETUP.md (Meta app, 5 env vars in `api\.env.bat`, `cloudflared tunnel --url http://localhost:8000`, webhook + subscribe `messages`).
- **Pricing rationale:** recall alerts free for everyone (mission). Basic ₹29 / Family ₹69 so the startup profits on every plan even in the worst case (50 paid WhatsApp messages per number per month, then free phone notifications). Pharmacy ₹499 is below what small chemists pay for billing software.
- **WhatsApp cost, plainly:** setup free; messages people send us free; our replies within 24 h of their last message free or near-free; messages we start outside that window ~₹0.115 + GST (~14 paise) each.
- **Next task:** real phone test of WhatsApp + push after deploy; then recall "blast radius".

<!-- Copy this template for each shift:

### Shift N — <Name> (hours X–Y)
- **Done:**
- **Works:**
- **Broken / blockers:**
- **How to run:**
- **New env vars:**
- **Next task:**

-->
