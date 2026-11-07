# Handoff for Mukul (24 Oct, Ashpreet's shift)

Everything below is on `main`. We now both work on `main` only (no feature branches): pull before you start, push when you finish.

## Start here (5 minutes)
1. `git pull origin main`
2. Restart the API once. On startup it now warms its caches and builds the medicine search index in the background (~10 s).
3. Open **`pitch/archive/KinCare_Pitch_Deck_v1.pptx` (superseded by `pitch/KinCare_Pitch_Deck_v2.pptx`)** (repo root). 13 slides; the spoken script is in the **speaker notes**.
4. Open **`/status`** on the site: live accuracy, response times and data freshness. That page is our answer to "is this real?".

## What changed today, and why

### 1. Bugs found by hard-testing the whole site (`1fa1d72`)
| Problem | Fix |
|---|---|
| API crashed under parallel load: 15 of 240 parallel requests returned 500 (`/controller`, `/blast`). One SQLite connection was shared by every request thread | One connection per thread (`api/db.py` → `ThreadConnection`). Now 0 of 600 fail |
| First `/demo` after a restart took 23 s (one openFDA call timed out) | Drug labels for common brands are fetched in the background at startup. Demo runs in ~5 s |
| Unknown URL showed Next's black 404; a crash showed "Application error" | Branded `not-found.tsx` and `error.tsx` |
| Raw "Failed to fetch" when the API is down; `/controller` spun forever | Clear "Can't reach the KinCare server" message; Retry button |
| Users could see "Run: python -m ingest.medicines" | Plain message |

### 2. Engineering depth, measured (`38962d3`)
- **Matcher benchmark on the real alert table** (`api/quality.py`, enforced by `test_quality.py`): 400 real flagged batches typed 6 ways (2,400 probes) → **100% caught**; 798 near-miss and clean batch numbers → **0 false alarms**.
- **Real matcher bug it found:** two *different* companies sharing a word like "Pharmaceuticals" were a "strong" maker match (25 of 399). Maker matching now compares the distinctive words → 0 of 399; the same company spelled differently is still recognised 99.7% of the time.
- **Speed:** with 32 users at once, the slowest 5% of requests went from **12 s to 33 ms**. Heavy summaries (`/controller`, stats, insights, recall gap) are cached until new alerts arrive and pre-filled at startup; medicine search uses a trigram index (90 → 8 ms, identical results).
- **Nightly ingest is actually scheduled now** (02:00 IST, every run logged in `ingest_runs`; a failure is logged, never crashes the API). The recall-gap number now refreshes after an ingest (it never did before).
- **`/api/status` + `/status` page.**
- **103 API tests pass.**

### 3. Professional UI pass (`9373b89`)
- **Removed** judge mode (`/stage`) and the "Install app" button. Chrome's own install banner is suppressed too: KinCare is a website. Push notifications still work.
- **Header:** Families · Pharmacies · Regulators menus (every page with a one-line description), search (⌘K or `/`), Sign in, one **Check a batch** button. SOS is in the Families menu and is the red button on phones.
- **All pages are listed in one file:** `web/lib/routes.ts`. Add a new page there and it appears in the menus, footer and search automatically.
- **Home page is one flow:** hero → the 10-month recall gap → how it works (3 steps) → built for families / pharmacies / regulators → real data → call to action.
- **All headings are sentence case** ("Know the batch, not just the brand.").

### 4. Pitch deck (`5c76f77`, updated in `9373b89`)
`pitch/archive/KinCare_Pitch_Deck_v1.pptx` (superseded by `pitch/KinCare_Pitch_Deck_v2.pptx`): one section per evaluation criterion — **Workflow** (slides 4–5), **MVP execution** (6–7), **Technical feasibility & architecture** (8–10), **Progress** (11), **Team contribution** (12). Every number comes from the repo, git or `/status`. Slide 7 is the live `/demo` walkthrough. `pitch/PITCH_SCRIPT.md` points to it.

### 5. PROGRESS.md
Dashboard recounted: **246 / 345 tasks (71%)**, tracks 32–33 added, team table recounted from git with one method for both of us (Mukul 66% of lines, Ashpreet 34%).

## Still open (in priority order)
1. **Deploy** (docs/setup/DEPLOY.md: Render + Vercel), then put the live URL on deck slide 7. Biggest win left.
2. **WhatsApp keys** (docs/setup/WHATSAPP_SETUP.md) so a judge's own phone gets the alert.
3. **Record the backup video** (shot list in pitch/PITCH_SCRIPT.md).
4. **State regulator sources** (§3 in PROGRESS.md).
5. Before presenting: `/demo` → **Reset demo data**.
