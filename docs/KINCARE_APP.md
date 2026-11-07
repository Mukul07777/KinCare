# KinCare

> Know the batch, not just the brand.

Drug recall system for India. Scan a medicine strip or pharmacy bill, live agents check every regulator alert source, and patients get a WhatsApp + Hindi voice alert if their batch is flagged. Elders can talk to KinCare in Hindi (Dadi mode), and family caregivers can look after a parent's doses and vitals, with the parent's consent.

Team Avengers: Mukul (Team Lead), Ashpreet Singh Saini. Flip the Switch 2026.

**Start here:** [PROGRESS.md](planning/PROGRESS.md) (what's done, what's open, latest handoff).

## Folder structure

```
Flip-the-Switch/
â”œâ”€â”€ README.md              this file
â”œâ”€â”€ PROGRESS.md            build plan, progress dashboard, shift handoffs (read first)
â”œâ”€â”€ run.bat                Windows one-click: install, build, start, open browser
â”œâ”€â”€ dev.sh                 macOS / Linux / Git Bash: start API + web
â”œâ”€â”€ render.yaml            API deploy blueprint (Render)
â”œâ”€â”€ .env.example           every setting, for reference
â”‚
â”œâ”€â”€ api/                   FastAPI backend (Python 3.12)
â”‚   â”œâ”€â”€ main.py            the app: middleware, lifespan (background jobs), includes every router
â”‚   â”œâ”€â”€ core.py            shared: database connection, alert matching, device ids, alerts to a device
â”‚   â”œâ”€â”€ routes/            HTTP routes, one file per area (alerts, care_plan, family, dadi, telegram_bot, â€¦)
â”‚   â”œâ”€â”€ env.example.bat    key template; run.bat copies it to api/.env.bat (git-ignored, your keys)
â”‚   â”œâ”€â”€ ingest/            download + parse CDSCO / state alerts, medicines, ICU recordings
â”‚   â”œâ”€â”€ matcher/           batch + maker + brand matching
â”‚   â”œâ”€â”€ care.py            prescriptions, doses, vitals, refills
â”‚   â”œâ”€â”€ caregiver.py       family caregivers: consent, scopes, access log, missed-dose alerts
â”‚   â”œâ”€â”€ voice.py           Dadi mode: Hindi / English understanding
â”‚   â”œâ”€â”€ telegram.py        free chat + alert channel
â”‚   â”œâ”€â”€ whatsapp.py        WhatsApp Cloud API
â”‚   â”œâ”€â”€ ...                ocr, prices, blast, packs, controller, sos, auth, billing, push
â”‚   â””â”€â”€ test_*.py          pytest suite
â”‚
â”œâ”€â”€ web/                   Next.js 15 frontend
â”‚   â”œâ”€â”€ app/               one folder per page (/scan, /care, /dadi, /family, /pharmacy, â€¦)
â”‚   â”œâ”€â”€ components/        shared UI pieces
â”‚   â””â”€â”€ lib/               API client (api.ts), route registry (routes.ts), push helpers
â”‚
â”œâ”€â”€ data/                  kincare.db and downloaded PDFs (created by run.bat, git-ignored)
â”‚
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ BUSINESS.md        business model, plans, unit economics
â”‚   â”œâ”€â”€ SECURITY.md        what protects the medical data, how it is tested, what is still open
â”‚   â”œâ”€â”€ DATASETS.md        every dataset behind KinCare and where it comes from
â”‚   â”œâ”€â”€ setup/
â”‚   â”‚   â”œâ”€â”€ DEPLOY.md          Render + Vercel deployment
â”‚   â”‚   â”œâ”€â”€ TELEGRAM_SETUP.md  free Telegram bot (chat + caregiver alerts)
â”‚   â”‚   â””â”€â”€ WHATSAPP_SETUP.md  Meta WhatsApp Cloud API
â”‚   â””â”€â”€ handoffs/          one-page shift handoffs
â”‚
â””â”€â”€ pitch/                 decks (.pptx) and spoken scripts
```

## Run locally

**Windows, one click:** double-click `run.bat`. The first run installs everything, downloads the real alert data and builds the web app; later runs rebuild the web app only when the code changed (after a `git pull`). Keys go in `api\.env.bat` (created on first run from `api\env.example.bat`, git-ignored). Everything is optional: with no keys KinCare runs in demo mode.

**Manually:**

```bash
# API (Python 3.12)
cd api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m ingest.fetch --limit 24   # download real CDSCO alert PDFs
.venv/Scripts/python -m ingest.load               # parse them into data/kincare.db
.venv/Scripts/python -m ingest.portal             # add CDSCO portal history (2019 â†’ latest)
.venv/Scripts/python -m pytest -q                 # tests
# Web
cd ../web && npm install
# Both
cd .. && ./dev.sh   # API :8000, web :3000
```

## Docs

| Need toâ€¦ | Read |
|---|---|
| See progress / pick up a shift | [PROGRESS.md](planning/PROGRESS.md) |
| Deploy | [docs/setup/DEPLOY.md](setup/DEPLOY.md) |
| Turn on Telegram (free) | [docs/setup/TELEGRAM_SETUP.md](setup/TELEGRAM_SETUP.md) |
| Turn on WhatsApp | [docs/setup/WHATSAPP_SETUP.md](setup/WHATSAPP_SETUP.md) |
| Understand the business model | [docs/BUSINESS.md](BUSINESS.md) |
| Know where the data comes from | [docs/DATASETS.md](DATASETS.md) |
| Understand security and privacy | [docs/SECURITY.md](SECURITY.md) |
| Pitch | [pitch/](pitch/) |

Data: 6,865 real alert rows (Jan 2019 â€“ Sep 2026) from the CDSCO public NSQ/spurious portal plus 24 alert PDFs. Portal endpoint discovery credit: [medcheck](https://github.com/ankithsurapani/medcheck). OCR runs locally with RapidOCR (no API key).

