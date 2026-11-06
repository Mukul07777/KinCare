# KinCare

> Know the batch, not just the brand.

Drug recall system for India. Scan a medicine strip or pharmacy bill, live agents check every regulator alert source, and patients get a WhatsApp + Hindi voice alert if their batch is flagged. Elders can talk to KinCare in Hindi (Dadi mode), and family caregivers can look after a parent's doses and vitals, with the parent's consent.

Team Avengers: Mukul (Team Lead), Ashpreet Singh Saini. Flip the Switch 2026.

**Start here:** [PROGRESS.md](PROGRESS.md) (what's done, what's open, latest handoff).

## Folder structure

```
Flip-the-Switch/
├── README.md              this file
├── PROGRESS.md            build plan, progress dashboard, shift handoffs (read first)
├── run.bat                Windows one-click: install, build, start, open browser
├── dev.sh                 macOS / Linux / Git Bash: start API + web
├── render.yaml            API deploy blueprint (Render)
├── .env.example           every setting, for reference
│
├── api/                   FastAPI backend (Python 3.12)
│   ├── main.py            the app: middleware, lifespan (background jobs), includes every router
│   ├── core.py            shared: database connection, alert matching, device ids, alerts to a device
│   ├── routes/            HTTP routes, one file per area (alerts, care_plan, family, dadi, telegram_bot, …)
│   ├── env.example.bat    key template; run.bat copies it to api/.env.bat (git-ignored, your keys)
│   ├── ingest/            download + parse CDSCO / state alerts, medicines, ICU recordings
│   ├── matcher/           batch + maker + brand matching
│   ├── care.py            prescriptions, doses, vitals, refills
│   ├── caregiver.py       family caregivers: consent, scopes, access log, missed-dose alerts
│   ├── voice.py           Dadi mode: Hindi / English understanding
│   ├── telegram.py        free chat + alert channel
│   ├── whatsapp.py        WhatsApp Cloud API
│   ├── ...                ocr, prices, blast, packs, controller, sos, auth, billing, push
│   └── test_*.py          pytest suite
│
├── web/                   Next.js 15 frontend
│   ├── app/               one folder per page (/scan, /care, /dadi, /family, /pharmacy, …)
│   ├── components/        shared UI pieces
│   └── lib/               API client (api.ts), route registry (routes.ts), push helpers
│
├── data/                  kincare.db and downloaded PDFs (created by run.bat, git-ignored)
│
├── docs/
│   ├── BUSINESS.md        business model, plans, unit economics
│   ├── SECURITY.md        what protects the medical data, how it is tested, what is still open
│   ├── DATASETS.md        every dataset behind KinCare and where it comes from
│   ├── setup/
│   │   ├── DEPLOY.md          Render + Vercel deployment
│   │   ├── TELEGRAM_SETUP.md  free Telegram bot (chat + caregiver alerts)
│   │   └── WHATSAPP_SETUP.md  Meta WhatsApp Cloud API
│   └── handoffs/          one-page shift handoffs
│
└── pitch/                 decks (.pptx) and spoken scripts
```

## Run locally

**Windows, one click:** double-click `run.bat`. The first run installs everything, downloads the real alert data and builds the web app; later runs rebuild the web app only when the code changed (after a `git pull`). Keys go in `api\.env.bat` (created on first run from `api\env.example.bat`, git-ignored). Everything is optional: with no keys KinCare runs in demo mode.

**Manually:**

```bash
# API (Python 3.12)
cd api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m ingest.fetch --limit 24   # download real CDSCO alert PDFs
.venv/Scripts/python -m ingest.load               # parse them into data/kincare.db
.venv/Scripts/python -m ingest.portal             # add CDSCO portal history (2019 → latest)
.venv/Scripts/python -m pytest -q                 # tests
# Web
cd ../web && npm install
# Both
cd .. && ./dev.sh   # API :8000, web :3000
```

## Docs

| Need to… | Read |
|---|---|
| See progress / pick up a shift | [PROGRESS.md](PROGRESS.md) |
| Deploy | [docs/setup/DEPLOY.md](docs/setup/DEPLOY.md) |
| Turn on Telegram (free) | [docs/setup/TELEGRAM_SETUP.md](docs/setup/TELEGRAM_SETUP.md) |
| Turn on WhatsApp | [docs/setup/WHATSAPP_SETUP.md](docs/setup/WHATSAPP_SETUP.md) |
| Understand the business model | [docs/BUSINESS.md](docs/BUSINESS.md) |
| Know where the data comes from | [docs/DATASETS.md](docs/DATASETS.md) |
| Understand security and privacy | [docs/SECURITY.md](docs/SECURITY.md) |
| Pitch | [pitch/](pitch/) |

Data: 6,865 real alert rows (Jan 2019 – Sep 2026) from the CDSCO public NSQ/spurious portal plus 24 alert PDFs. Portal endpoint discovery credit: [medcheck](https://github.com/ankithsurapani/medcheck). OCR runs locally with RapidOCR (no API key).
