# Telegram: free chat and caregiver alerts

WhatsApp Cloud API bills every message sent outside the 24-hour window (about ₹0.13 each in India), and needs Meta business verification plus approved templates. Telegram's Bot API costs nothing at any volume, has no window and needs no approval. So KinCare uses Telegram for:

- **Dadi mode chat**: the elder talks to KinCare in Telegram exactly as in the app ("दवा ले ली", "BP 130/85", "डोलो 650 कितने की है?", "बेटे को बुलाओ"). Both channels share one chat history.
- **Caregiver alerts**: a dose still unticked an hour after its time, an urgent reading, or an SOS, sent only to caregivers the elder chose for that kind of data.

Web Push (already built in) stays as the second free channel. WhatsApp is still supported where it's configured.

## Setup (5 minutes)

1. In Telegram, open **@BotFather** and send `/newbot`. Pick a name and a username ending in `bot`, e.g. `KinCareDadiBot`.
2. Open `api\.env.bat` (run.bat creates it from `api\env.example.bat` on its first run; it is git-ignored) and fill in:
   ```
   set "TELEGRAM_BOT_TOKEN=123456:ABC..."
   set "TELEGRAM_BOT_NAME=KinCareDadiBot"
   ```
   On Render, add the same two keys under Environment instead.
3. Restart the API. With no `TELEGRAM_WEBHOOK_SECRET` set, KinCare long-polls Telegram, so it works on a laptop with no public URL.
4. Open `/dadi` and press **Talk to KinCare on Telegram**. Telegram opens; press **Start**. Done.
   Caregivers press **Get alerts on Telegram** on their `/family` dashboard.

## Production (webhook)

Pick any random string as `TELEGRAM_WEBHOOK_SECRET`, then register it:

```
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d url=https://YOUR-API/api/telegram/webhook -d secret_token=$TELEGRAM_WEBHOOK_SECRET
```

## Privacy

A chat is tied to a device only through a one-time, 24-hour link code that the person opens themselves. KinCare can't message anyone who hasn't pressed Start. Caregivers get only what the elder ticked when making the invite, every look and alert appears in the elder's access log on `/family`, and either side can end the link at any time.
