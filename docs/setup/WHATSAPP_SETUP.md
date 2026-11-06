# Real WhatsApp for KinCare (free to start)

KinCare talks to **Meta's own WhatsApp Cloud API** (no Twilio markup). Setup is free; Meta's test
number can message up to 5 phones you verify, which is enough for the demo.

## What it costs (India, Meta rates, 2026)

| Message | Cost |
|---|---|
| Anything a patient sends us ("hi", "1", a batch number) | Free |
| Our reply within 24 h of their last message | Free or near-free (Meta's rules for this changed in Oct 2026, so check the rate card) |
| A reminder outside that 24 h window (needs an approved *Utility* template) | ~₹0.115 + 18% GST |

KinCare keeps most messages inside the window: every reminder ends with **"Reply 1 once taken"**.
The reply ticks the dose in KinCare and reopens the 24 h window for the next reminder.

## 15-minute setup

1. **Create the app.** Go to <https://developers.facebook.com/apps>, then *Create app* → *Business* → add the **WhatsApp** product.
2. **Copy the keys.** On *WhatsApp → API Setup*, copy the **temporary access token** and the **Phone number ID**. Under *To*, add your phone and the judges' phones (up to 5) and verify each with the code.
3. **Add them to `api\.env.bat`** (this file is gitignored):
   ```bat
   set WHATSAPP_TOKEN=EAAG...
   set WHATSAPP_PHONE_ID=1234567890
   set WHATSAPP_NUMBER=+1 555 xxx xxxx
   set WHATSAPP_VERIFY_TOKEN=kincare-verify-123
   set WHATSAPP_APP_SECRET=xxxxxxxx
   ```
   - `WHATSAPP_NUMBER` is the test number shown on the API Setup page; it powers the "Say hi" button.
   - `WHATSAPP_VERIFY_TOKEN` is any string you choose; use the same one in step 4.
   - `WHATSAPP_APP_SECRET` is under *App settings → Basic*.
4. **Webhook (so replies reach KinCare).** The API must be reachable over HTTPS. Locally, run:
   ```
   cloudflared tunnel --url http://localhost:8000
   ```
   or use `ngrok http 8000`. Then in Meta go to *WhatsApp → Configuration → Webhook*:
   - Callback URL: `https://<your-tunnel>/api/whatsapp/webhook`
   - Verify token: the same `WHATSAPP_VERIFY_TOKEN`
   - Click *Verify and save*, then **subscribe to `messages`**.
5. **Try it.** Restart `run.bat`. In KinCare → Care (or /demo), tap **Say hi to KinCare on WhatsApp** and send.
   - Reply `1` to tick the latest dose.
   - Send `AT25-0938A` to get the alert check back.

## Optional: reminders when the window is closed

Without a template, KinCare only messages people who wrote in the last 24 h, which is free. To also
reach people outside that window, create a template in *WhatsApp Manager → Message templates*:

- Category **Utility**, name `kincare_update`, language **English**
- Body: `KinCare update: {{1}}`

Then set `WHATSAPP_TEMPLATE=kincare_update`. Approval usually takes minutes. KinCare automatically uses
it only when the window is closed.

## Going live after the hackathon

- **Permanent token.** The temporary token expires in 24 h. Make a permanent one under *Business Settings → System users*.
- **Your own number.** Add your own business number, set a display name, and complete Meta Business
  Verification to message more than 250 new people a day.
- **Fallback.** Twilio still works if `TWILIO_*` is set and `WHATSAPP_*` is not. Voice calls always use Twilio.
