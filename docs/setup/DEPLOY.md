# Deploy KinCare (about 15 minutes)

You need HTTPS so judges can open KinCare on their own phones, phone notifications work, and WhatsApp
can reach the webhook.

| Part | Where | Cost |
|---|---|---|
| API (FastAPI + SQLite on a 1 GB disk) | Render, from `render.yaml` | Starter ≈ $7/month (a persistent disk needs a paid instance) |
| Web (Next.js) | Vercel | Free (Hobby) |

## 1. API on Render

1. Go to <https://dashboard.render.com>, then *New → Blueprint*, and pick the `KinCare` repo. Render reads `render.yaml`.
2. When asked, fill these (the rest are generated or optional):
   - `PUBLIC_WEB_URL`: leave blank for now. You'll set it after step 2.
   - WhatsApp, Stripe and TinyFish keys: optional. Without them, KinCare uses the outbox and shows login codes on screen.
3. Deploy.
   - **The first boot builds the database (~10 minutes).** The API answers immediately with partial data, then restarts once with all 7,920 alerts and 246k medicines.
   - Watch the logs for `Database ready, restarting the API`.
4. Check that `https://kincare-api-XXXX.onrender.com/health` shows `"alerts": 7920`.

## 2. Web on Vercel

1. Go to <https://vercel.com/new>, import the repo, and set **Root Directory = `web`**.
2. Add the environment variables `KINCARE_API_URL = https://kincare-api-XXXX.onrender.com` (the site forwards `/api` there, so the session cookie stays first-party) and `NEXT_PUBLIC_API_URL` = the same URL (only shown on the developers page). On Render, set `KINCARE_ORIGINS` = your Vercel URL. Security settings: [docs/SECURITY.md](../SECURITY.md).
3. Deploy. You get `https://kincare-XXXX.vercel.app`.

## 3. Connect them

1. In Render → kincare-api → *Environment*, set `PUBLIC_WEB_URL = https://kincare-XXXX.vercel.app`. This is used in check-in links inside WhatsApp messages.
2. If you use WhatsApp, set the Meta webhook to `https://kincare-api-XXXX.onrender.com/api/whatsapp/webhook` (see docs/setup/WHATSAPP_SETUP.md).
3. Open the admin panel at `https://kincare-XXXX.vercel.app/admin` with the generated `ADMIN_TOKEN` (Render → Environment).
   - The recall blast radius and its demo button also need this token when you're not on localhost.

## 4. Before the demo

- [ ] Open the Vercel URL on a phone, then *Install app* and *Turn on reminders* (phone notifications need HTTPS, which you now have).
- [ ] `/demo`: run once to warm up the openFDA label cache (the first run takes about 6 seconds).
- [ ] `/blast?batch=AT250938A`: *Load simulated holders* (admin token), then try *Alert*, then *Clear* and *Load* again so it's fresh for the judges.
- [ ] `/login`: sign in with your number. Without WhatsApp keys, the code shows on screen (demo mode).
- [ ] Optional: set `KINCARE_ALL_ACCESS=1` on Render so no plan limit ever shows on stage.

## Free alternative (for a one-day demo)

Run KinCare on your laptop (`run.bat`) and expose it with a tunnel:
- `cloudflared tunnel --url http://localhost:3000` gives an HTTPS link for the web app.
- Only the web port needs a tunnel now: the site forwards `/api` to `localhost:8000` itself.

It's free and works on any phone while the laptop stays on.
