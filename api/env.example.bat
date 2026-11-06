@echo off
REM ============================================================================
REM  KinCare keys. run.bat copies this file to api\.env.bat on first run and
REM  loads api\.env.bat every time it starts the servers.
REM
REM  Edit api\.env.bat (NOT this file): it is git-ignored, so your keys never
REM  reach GitHub. This template is the one that is shared.
REM
REM  Format:  set "NAME=value"   (keep the quotes; leave empty if you don't have it)
REM  Everything is optional: with no keys KinCare runs in demo mode.
REM  After editing, close both server windows and run run.bat again.
REM ============================================================================

REM ---- Telegram: FREE chat + caregiver alerts (docs/setup/TELEGRAM_SETUP.md) ----
REM  Telegram > @BotFather > /newbot > copy the token. Bot name without the @.
set "TELEGRAM_BOT_TOKEN="
set "TELEGRAM_BOT_NAME="
REM  Leave empty on a laptop (KinCare polls Telegram itself). Only for a webhook in production.
set "TELEGRAM_WEBHOOK_SECRET="

REM ---- Real WhatsApp, Meta Cloud API (docs/setup/WHATSAPP_SETUP.md) ----
set "WHATSAPP_TOKEN="
set "WHATSAPP_PHONE_ID="
set "WHATSAPP_NUMBER="
set "WHATSAPP_VERIFY_TOKEN="
set "WHATSAPP_APP_SECRET="
set "WHATSAPP_TEMPLATE="

REM ---- Twilio (optional: WhatsApp sandbox + Hindi voice calls) ----
set "TWILIO_ACCOUNT_SID="
set "TWILIO_AUTH_TOKEN="
set "TWILIO_WHATSAPP_FROM="
set "TWILIO_VOICE_FROM="

REM ---- TinyFish web agents (live regulator checks) ----
set "TINYFISH_API_KEY="

REM ---- Payments, Stripe test mode (sk_test_...) ----
set "STRIPE_SECRET_KEY="
set "STRIPE_WEBHOOK_SECRET="

REM ---- Admin panel: empty = /admin opens only on this computer ----
set "ADMIN_TOKEN="

REM ---- Links inside WhatsApp / Telegram messages point here ----
set "PUBLIC_WEB_URL=http://localhost:3000"
