"""Stripe Checkout for paid plans. Test mode works with free test keys (sk_test_...).

Patients stay free. Paid plans are what the business model sells: Family (more members,
SOS alerts to family) and the Pharmacy recall desk.
"""
import os

from checkin import PUBLIC_WEB_URL

# Prices in paise. One place to change them; the UI reads this through /api/billing/plans.
# Pricing rule: recall alerts stay free for everyone. Paid WhatsApp messages (Meta Utility template, ~Rs 0.115 + GST,
# only outside the free 24-hour window) are capped per number per month (whatsapp.PAID_CAP); past the cap,
# reminders go as free phone notifications. So the worst case is known and every plan keeps a margin (tested).
# Each plan includes everything in the one before it. Pharmacy Pro includes every feature KinCare has.
FREE = ["Unlimited strip, bill and QR scans", "Batch check against every CDSCO and state alert", "Recall alerts on WhatsApp and a Hindi voice call",
        "Medicine info: uses, side effects, warnings", "Cheaper same-salt brands from makers with no alerts", "Jan Aushadhi store finder",
        "Phone notifications for doses and refills", "Watchlist for your batches", "SOS button with 112 / 108 and nearby hospitals"]
_BASIC = ["Everything in Free, plus:", "WhatsApp dose reminders for 1 person (reply 1 to tick)", "Refill reminders with the cheapest clean brand",
          "Prescription scan into a dose schedule", "Drug-interaction check", "Private doctor link with live vitals and video consult", "Printable doctor report"]
_FAMILY = ["Everything in Basic, plus:", "Up to 6 family members", "WhatsApp reminders on up to 3 numbers", "SOS alerts to family on WhatsApp with location",
           "Monthly medicine spend and savings for the whole family"]
_PHARMACY = ["Everything in Family, plus:", "First month free", "Your customers get WhatsApp reminders free (Basic, on us)", "Stock CSV matched against every new alert", "Find customers who bought a flagged batch",
             "300 customer WhatsApp recall alerts a month", "Patient check-in queue after a recall", "Audit and PvPI exports"]
_PRO = ["Everything in Pharmacy, plus (all KinCare features):", "Multiple locations and staff logins", "2,000 customer WhatsApp alerts a month",
        "Early Signal reports: bad batches patients report before CDSCO lists them", "Live recall command screen", "Alert API access", "Priority support"]
PLANS = {
    "basic": {"name": "Basic", "amount": 2900, "interval": "month", "who": "One person on regular medicines", "wa_numbers": 1, "features": _BASIC},
    "basic_year": {"name": "Basic yearly", "amount": 29900, "interval": "year", "who": "Same as Basic, 2 months free", "wa_numbers": 1, "features": _BASIC},
    "family": {"name": "Family", "amount": 6900, "interval": "month", "who": "A household caring for elders", "wa_numbers": 3, "features": _FAMILY},
    "family_year": {"name": "Family yearly", "amount": 69900, "interval": "year", "who": "Same as Family, 2 months free", "wa_numbers": 3, "features": _FAMILY},
    "pharmacy": {"name": "Pharmacy", "amount": 49900, "interval": "month", "who": "One independent store", "wa_numbers": 300, "features": _PHARMACY},
    "pharmacy_year": {"name": "Pharmacy yearly", "amount": 499900, "interval": "year", "who": "Same as Pharmacy, 2 months free", "wa_numbers": 300, "features": _PHARMACY},
    "pharmacy_pro": {"name": "Pharmacy Pro", "amount": 149900, "interval": "month", "who": "Chains and hospital pharmacies", "wa_numbers": 2000,
                     "features": _PRO},
}
CURRENCY = "inr"


def ready() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def test_mode() -> bool:
    return os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_")


def _stripe():
    import stripe

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


def create_session(plan: str, device: str) -> tuple[str, str]:
    p = PLANS[plan]
    s = _stripe().checkout.Session.create(
        mode="subscription",
        line_items=[{
            "quantity": 1,
            "price_data": {"currency": CURRENCY, "unit_amount": p["amount"], "recurring": {"interval": p["interval"]},
                           "product_data": {"name": f"KinCare {p['name']}"}},
        }],
        # Pharmacies: first month free (pilot). Card taken now, charged after 30 days, cancel any time.
        subscription_data={"trial_period_days": 30} if plan.startswith("pharmacy") else {},
        client_reference_id=device,
        metadata={"plan": plan, "device": device},
        success_url=f"{PUBLIC_WEB_URL}/account?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{PUBLIC_WEB_URL}/account?cancelled=1",
    )
    return s.id, s.url


def fetch_session(session_id: str) -> dict:
    s = _stripe().checkout.Session.retrieve(session_id)
    # A trial (pharmacy first month) completes with no_payment_required: active too.
    return {"paid": s.status == "complete" and s.payment_status in ("paid", "no_payment_required"), "device": s.client_reference_id,
            "email": (s.customer_details or {}).get("email") if s.customer_details else None}


def parse_webhook(payload: bytes, signature: str):
    return _stripe().Webhook.construct_event(payload, signature, os.environ["STRIPE_WEBHOOK_SECRET"])
