# KinCare: Business Model & Plan

> **Free for patients. Paid by pharmacies.**
> One source-linked database of official drug alerts powers a free consumer check and paid recall software for organisations.

All prices and numbers below are **hypotheses to test with pilot customers**, not validated market rates or forecasts.

---

## 1. Positioning

KinCare is a **medicine-batch alert and recall-response platform**. It:
- checks whether a batch appears in a **published regulator alert** (CDSCO, state regulators, manufacturer notices),
- traces that batch through **recorded inventory and sales**,
- gives organisations a **tracked, auditable response workflow**.

It does **not** test medicines, certify authenticity, guarantee safety, or replace official recall procedures.

**Why now:** CDSCO's 2024 recall and rapid-alert guidelines (QMS/37/Guideline/2024) assign recall responsibilities across manufacturers, distributors, stockists and retailers. That makes recall-response tooling relevant, though it does not prove these buyers will pay.

---

## 2. Who pays and why

| Customer | Pays | Job to be done | Why they pay |
|---|---|---|---|
| Patients | **Free forever** | "Is this batch named in an alert?" | They don't: safety is never paywalled. Free users are the top of the funnel and the Early Signal network |
| One person on regular medicines | ₹29/month | Never miss a dose, never run out | WhatsApp reminders with reply-1, refill alerts, doctor link |
| Families caring for elders | ₹69/month | "Is Dadi taking her medicines, and are they safe?" | 6 members, WhatsApp for 3 numbers, SOS to family, family savings |
| Independent pharmacies | **₹499/month (first revenue)** | "Does my stock contain a newly flagged batch, and who did I sell it to?" | Stock matching, find and alert customers, audit trail; avoiding one recall complaint pays for a year |
| Chains and hospital pharmacies | ₹1,499/month, enterprise from ₹15k | "Which branches are exposed, and who acted?" | Multi-location, Early Signal, live recall screen, API |

---

## 3. Pricing (in the app: `api/billing.py`, one place)

Each plan includes everything in the plan below it. **Pharmacy Pro has every KinCare feature.**

| Plan | Price | Adds |
|---|---|---|
| Free | ₹0 | Scans, batch checks, recall alerts on WhatsApp + Hindi voice, medicine info, cheaper same-salt brands, Jan Aushadhi finder, phone notifications, watchlist, SOS |
| Basic | ₹29/mo · ₹299/yr | WhatsApp dose reminders (1 person, reply 1 to tick), refill reminders, prescription scan, interactions, doctor link, report |
| Family | ₹69/mo · ₹699/yr | 6 members, WhatsApp on 3 numbers, SOS to family, family spend + savings |
| Pharmacy | ₹499/mo · ₹4,999/yr | Stock matching, find customers who bought a flagged batch, 300 customer recall alerts/mo, check-in queue, PvPI exports, **customers get Basic free** |
| Pharmacy Pro | ₹1,499/mo | Multi-location, 2,000 alerts/mo, Early Signal reports, live recall screen, Alert API, priority support |
| Enterprise / API | from ₹15k/mo | Hospital groups, distributors, custom integrations, SLAs |

**Trials:** every new account gets **14 days of Family**, no card. Pharmacies get **the first month free** (Stripe trial).
**Enforced in the app** (`api/entitlements.py`): member and WhatsApp-number limits per plan. Safety is never gated: a free user still gets the recall alert on WhatsApp.
**Principles:** never charge for a patient's safety check. No ads. No sale of health data.

---

## 4. Growth loop: pharmacies bring the patients

1. A pharmacy subscribes (₹499, first month free). Its stock is checked against every new alert.
2. **Its customers get Basic free**: phone numbers on the store's sales records get WhatsApp reminders, paid for by the pharmacy. KinCare gets users without paying to advertise.
3. When a batch is flagged, KinCare finds who bought it and alerts them before the next dose. The store looks responsible, and customers come back.
4. Customers add parents and grandparents with Family (₹69). Their symptom reports feed Early Signal for every store.

## 5. Unit economics (worst case, every message paid)

WhatsApp via Meta Cloud API: ~₹0.115 + GST (₹0.136) per message we *start* outside the 24-hour window; messages people send us are free; replies inside the window are free or near-free. Paid messages are **capped at 50 per number per month** (then free phone notifications); recall and SOS alerts are never capped.

| Plan | Price/mo | Worst-case WhatsApp | Payment + infra | **Profit/mo** |
|---|---|---|---|---|
| Basic | ₹29 | ₹7 | ₹4 | **₹18 (62%)** |
| Family | ₹69 | ₹20 | ₹5 | **₹44 (64%)** |
| Pharmacy | ₹499 | ₹41 | ₹18 | **₹440 (88%)** |
| Pharmacy Pro | ₹1,499 | ₹271 | ₹48 | **₹1,180 (79%)** |

A test (`api/test_whatsapp.py`) fails if any plan's worst-case WhatsApp cost exceeds 40% of its price. Typical cost is far lower: "reply 1" keeps the free window open.

### Illustrative year-1 path (hypotheses, not forecasts)
| Stage | Mix | MRR |
|---|---|---|
| Pilot (month 3) | 10 pharmacies, 300 Basic, 100 Family | ₹20,600 |
| Traction (month 9) | 60 pharmacies, 5 Pro, 2,000 Basic, 800 Family | ₹1.5 L |
| Year 1 | 200 pharmacies, 20 Pro, 3 enterprise, 8,000 Basic, 3,000 Family | ₹6.6 L (₹79 L/yr) |

Lean fixed cost ₹30k–90k/month → break-even at roughly **70–200 pharmacies**, before any consumer revenue.

---

## 6. Go-to-market

1. **Interview 10 independent pharmacists.** How do they hear about alerts? Do they record batch-level stock? What happens when a batch is flagged?
2. **Recruit 3–5 design partners.** 30-day pilot: CSV upload + matching + review dashboard. Be explicit about what's live and what's simulated.
3. **Measure value.** Correct matches, detection speed, staff time saved, workflow completion.
4. **Convert to paid.** First month free, then ₹499. Interview everyone who declines.
5. **Distribute through partners.** Integrate with existing pharmacy software (Marg, GoFrugal) and pharmacy groups instead of asking stores to switch.

**Sales line:** *"KinCare helps pharmacies find batches named in official alerts in their recorded stock, act on them, and keep a record, without replacing their pharmacy software."*

---

## 7. Competitive positioning

- **Not another billing/inventory system.** Many already track batches and expiry. KinCare adds cross-source regulator monitoring on top of them.
- **Complements government QR codes.** QR shows the pack came from the maker; KinCare shows whether a regulator flagged the batch.
- **Never presented as an official verification service.**
- **Moat:** a normalised, source-linked alert database + integrations + measured match accuracy + a network of pharmacies acting on it. Not the OCR or the agent alone.

### Prior art on GitHub (checked 24 Oct 2026)

| Project | What it does well | What we took | Where KinCare goes further |
|---|---|---|---|
| [medcheck](https://github.com/ankithsurapani/medcheck) | Searchable NSQ database, 2019 → 2026, via CDSCO's public JSON portal | Discovered the portal endpoint (we wrote our own client; their dataset is CC0) | Scan + OCR, watchlist, pharmacy recall workflow |
| [AushadhIQ](https://github.com/manojk909/AushadhIQ) | Batch lookup, careful manufacturer entity resolution, "never says safe" enforced by tests | Strip only legal forms when normalising makers; show grouped spellings; a test that fails if a result says "safe" | Inventory bulk check, review tasks + audit trail, return note, notifications |
| [pharmawatch](https://github.com/COSMICnoob80/pharmawatch) (blueprint) | WhatsApp-shareable alert cards | One-tap WhatsApp share of a verdict with the source link | Working product, Indian data |

**Our position:** others make the data *searchable*; KinCare makes it *actionable*: scan a strip, watch a batch, and run a pharmacy's recall response end to end.

---

## 8. Roadmap

| Phase | When | Goal | Key work |
|---|---|---|---|
| 1 | 0–30 days | Prove the tech | Scanner, alert DB, source-linked matching, stock upload. Tested on known notices incl. negative and ambiguous cases |
| 2 | 1–3 months | Validate | 3–5 pharmacy pilots, import reliability, audit logs, first paying customers |
| 3 | 3–6 months | Repeatable revenue | Multi-branch, scheduled monitoring, software integrations, support process |
| 4 | 6–12 months | Expand | Hospital groups, distributors, alert API, wider source coverage |

### Founder milestones
- **Technical:** reliable extraction and matching on a hand-verified test set; zero dangerous false positives in the alert workflow.
- **Customer:** 3 pharmacies complete a real pilot.
- **Commercial:** 2 pilots convert to paid.
- **Operational:** track source freshness, failed checks, missed test alerts, match errors, response time.

Get legal and regulatory advice on claims, data protection and recall responsibilities before commercial launch.

---

## 9. Ideas considered and parked

| Idea | Why parked |
|---|---|
| Foil micro-texture / pill colour "authentication" | Phone cameras can't support these claims reliably; risks false reassurance. A visual pack check stays a *hint*, never a verdict |
| Blockchain traceability | Adds no value over a normal audit log for this problem |
| Automatic ERP stock freezing | Needs deep integrations and carries liability; start with tasks + human confirmation |
| Geo-anomaly "batch sold outside its region" | Requires distributor shipment data we don't have yet (Phase 4 with distributor partners) |
| Crowdsourced adverse-reaction risk scores | Medically and legally sensitive; route reports to PvPI instead of scoring batches ourselves |
| "Verified stock" storefront badges | Implies a certification we can't give |
| Manufacturer-paid recall push to consumers who scanned a batch | Good later-stage revenue once there's a scan network; needs explicit consent |
