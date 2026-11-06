# Security and privacy

KinCare holds medical data: prescriptions, doses, vitals, diagnoses, chats with family and doctors. This page lists what
protects it, how each protection is checked, and what is still open. Every item marked ✅ has a test in
`api/test_security.py` (or the file named), which runs in CI on every push.

## Who is calling

| | Protection | Checked by |
|---|---|---|
| ✅ | **Server-issued sessions, never a client-chosen id.** A visitor gets a random 256-bit session token on first visit; every row of personal data is keyed by a random account id the server never sends to the browser. Sending someone's id gets you nothing. | `test_a_device_id_header_or_a_forged_token_gives_nothing`, `test_device_id_header_is_ignored_…` |
| ✅ | **Every personal endpoint requires a session.** The test finds them automatically (60+) and checks each returns 401 without one. | `test_every_personal_endpoint_refuses_a_request_without_a_session` |
| ✅ | **Tokens stored only as SHA-256 hashes**, so a copy of the database can't be used to sign in as anyone. | `test_tokens_are_stored_only_as_hashes_and_are_256_bit` |
| ✅ | **HttpOnly, SameSite=Lax, Secure (HTTPS) cookie.** Page scripts can't read it; other sites can't send it on a POST. | `test_session_cookie_is_httponly_and_samesite`, browser test |
| ✅ | **Sessions expire** (30 days signed in, 90 guest, sliding) and are **revocable**: sign out, sign out other devices, list of signed-in devices on Account. | `test_revoked_and_expired_sessions_stop_working`, `test_sign_out_other_devices_keeps_this_one` |
| ✅ | **New session at login** (no session fixation); the guest token dies. | `test_auth.py::test_first_login_…` |
| ✅ | **Phone login** with one-time codes: hashed, 10-minute expiry, 5 tries, 3 sends per number per 10 minutes, plus per-IP rate limits. Codes are shown on screen **only** with `KINCARE_DEMO=1` (a demo laptop); otherwise sign-in needs WhatsApp delivery. | `test_production_never_shows_login_codes`, `test_login_and_invite_codes_are_rate_limited` |
| ✅ | **Sharing needs a verified phone.** Caregiver invites/accepts and doctor links refuse guest sessions. | `test_sharing_health_data_needs_a_verified_phone` |

## Who may do what (roles)

Every account is a **patient** and sees only its own data. Professional roles are granted, never assumed: a phone-verified
user asks on Account (pharmacy name + drug licence, or office + officer ID), an admin checks it and approves. Roles count only
on a signed-in session, take effect and end immediately, and every decision is in the audit log. **Admin** can't be requested;
an existing admin grants it (the `ADMIN_TOKEN` holder is the first admin). On the laptop demo (`KINCARE_DEMO=1`) requests are
approved at once and marked so in the log. Caregivers and doctors are not roles: the patient shares with one person, with
chosen scopes (see Stored data).

| Permission | Patient | Pharmacist | Regulator | Admin | Endpoints |
|---|:-:|:-:|:-:|:-:|---|
| Own shop's sales register | | ✅ | | | `/api/sales`, `/api/pharmacy/state` |
| Message own shop's buyers of a flagged batch | | ✅ | | | `/api/pharmacy/notify` |
| Run a recall | | ✅ | ✅ | ✅ | `/api/recall/run`, `/api/recall/stream` |
| Controller dashboard | | | ✅ | ✅ | `/api/controller` |
| See who holds a flagged batch (names, phones, next dose), alert them | | | ✅ | ✅ | `/api/blast*` |
| Messages KinCare sent | | | masked phones | full | `/api/notifications` |
| Message a typed-in demo number, seed demo data, fetch new alerts | | | | ✅ | `/api/recall/run` with `demo_phone`, `/api/*/demo`, `/api/admin/ingest` |
| Approve / revoke roles, read the audit log, operations | | | | ✅ | `/api/admin/*` |

| | Protection | Checked by |
|---|---|---|
| ✅ | **Every guarded endpoint allows exactly the roles above.** The test finds the 25 guarded endpoints from the app and calls each as every role: denied roles get 403, no session gets 401. | `test_rbac.py::test_every_guarded_endpoint_allows_exactly_the_roles_it_should`, `…_refuses_a_request_without_a_session` |
| ✅ | **Request → approve → revoke**, pending gives nothing, revoked stops the same session at once. | `test_request_approve_revoke_lifecycle`, browser test |
| ✅ | **No self-promotion**: admin can't be requested, nobody approves their own request, guests can't request. | `test_nobody_can_make_themselves_admin_or_approve_themselves` |
| ✅ | **Roles need a phone-verified session**: a guest session on an account with a role gets patient rights only. | `test_roles_only_count_on_a_phone_verified_session` |
| ✅ | **Pharmacies are isolated**: one shop never sees another's customers. | `test_pharmacies_never_see_each_others_customers` |
| ✅ | **Audit log**: role requests and decisions, every look at batch holders, every holder alert, recall and buyer message. A refused call leaves no "viewed" entry. Account ids are shown as masked phones, even to admins. | `test_looking_at_holders_is_audited_…`, `test_the_audit_log_never_shows_account_ids_even_to_admins` |

## Requests

| | Protection | Checked by |
|---|---|---|
| ✅ | **Same-origin API.** The web app calls `/api/*` on its own domain (Next.js forwards it), so the API allows no other origin (CORS limited to `KINCARE_ORIGINS`). | `test_cors_allows_only_configured_origins` |
| ✅ | **CSRF.** A cookie-authenticated change must carry the app's `X-KinCare` header and an allowed `Origin`. | `test_csrf_cookie_requests_need_the_app_header_and_origin`, browser test (forged POST with a real cookie → 403) |
| ✅ | **Headers.** API: `nosniff`, `DENY` framing, `no-referrer`, `default-src 'none'` CSP, `Cache-Control: no-store` on every `/api` response, HSTS on HTTPS. Web: CSP (`frame-ancestors 'none'`, `object-src 'none'`, `connect-src 'self'`), `DENY`, `no-referrer`, Permissions-Policy, HSTS in production. | `test_security_headers_and_no_caching_of_medical_data`, browser test |
| ✅ | **Rate limits** on session creation, login codes and invite codes (6-letter codes would otherwise be guessable). | `test_login_and_invite_codes_are_rate_limited` |
| ✅ | **Admin needs `ADMIN_TOKEN` (constant-time compare) or the admin role** on a signed-in session. With neither configured, admin is closed. | `test_admin_always_needs_the_token`, `test_admin_grants_by_phone_…` |
| ✅ | **Webhooks.** WhatsApp messages must carry Meta's signature (`WHATSAPP_APP_SECRET`); Telegram webhooks need `TELEGRAM_WEBHOOK_SECRET`; Stripe needs its signature. The `/whatsapp` simulator acts only as a fixed sandbox number. | `test_unsigned_whatsapp_webhooks_are_refused_outside_demo`, `test_whatsapp_simulator_cannot_act_as_a_real_phone` |
| ✅ | **Capability links** (doctor 144-bit, check-in 128-bit tokens) expire or can be revoked; `no-referrer` keeps them out of other sites' logs. | `test_doctor.py` |

## Stored data

| | Protection | Checked by |
|---|---|---|
| ✅ | **Encryption at rest** for chats (Dadi / Telegram), doctor ↔ patient messages and diagnoses: AES-256-GCM, random nonce per value, bound to its table and column. Older rows are encrypted at startup. Key: `KINCARE_DATA_KEY` (or `data/data.key`, mode 600). | `test_chats_doctor_messages_and_diagnoses_are_encrypted_at_rest`, `test_ciphertext_cannot_be_tampered_…`, `test_old_plaintext_rows_get_encrypted` |
| ✅ | **Consent** for caregivers: chosen scopes, one family member, access log of every look, revocable by either side. | `test_caregiver*.py` |
| ✅ | **DPDP Act rights**: download everything (Account), delete everything (also ends every session and caregiver link). | `test_privacy.py` |
| ✅ | **Retention**: raw live vitals 7 days, chats 180 days, login codes 1 day, access log 365 days. | `test_retention_purges_only_old_raw_data` |
| ✅ | Photos of strips and prescriptions are read in memory on our server (local OCR, no third party) and never stored. | code review: `routes/alerts.py`, `routes/care_plan.py` |

## Running it safely

- **Production (Render):** `ADMIN_TOKEN` and `KINCARE_DATA_KEY` are generated by `render.yaml`; `COOKIE_SECURE=1`. **Never set `KINCARE_DEMO`.** Set `WHATSAPP_APP_SECRET` before connecting WhatsApp.
- **Web (Vercel):** set `KINCARE_API_URL` to the API's URL; the browser never calls the API directly.
- **Laptop demo:** `run.bat` sets `KINCARE_DEMO=1` and makes an admin token in `api\.env.bat`.
- Back up `KINCARE_DATA_KEY` separately from the database: without it, encrypted fields can't be read.

## Still open (honest list)

- **Not everything is encrypted at rest.** Vitals numbers, medicine names and phone numbers (needed to send WhatsApp messages and to look people up) are stored in clear text in SQLite, protected by the server's disk encryption. Next step: encrypt phone numbers with a keyed hash for lookups.
- **The web CSP allows inline scripts** (`'unsafe-inline'`), which Next.js needs without per-request nonces. Next step: nonce-based CSP via middleware.
- **Sign-in depends on WhatsApp delivery.** Without a WhatsApp provider, production has no phone login (by design: no codes on screen).
- **No external audit or penetration test yet**, and KinCare is not a certified medical device.
