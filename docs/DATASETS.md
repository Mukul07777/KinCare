# Datasets used in KinCare

All numbers in KinCare come from public datasets. The only simulated data is Early Signal's demo seed, which the app labels.

| Dataset | Size | Used for | Licence |
|---|---|---|---|
| CDSCO drug alerts | 6,865 alerts, 2019 – Sep 2026 | Batch check, recall, maker record | Govt public data |
| Indian Medicine Dataset | 246,068 brands | Cheaper same medicine | MIT |
| PhysioNet BIDMC | 53 ICU patients | Live vitals replay, pulse accuracy | ODC-By 1.0 |
| openFDA drug labels | Per medicine, cached | Interaction warnings | Public domain |

---

## 1. CDSCO drug alerts
**What:** Monthly government lists of medicine batches that failed quality tests (NSQ) or are fake (spurious).
**Source:** [cdsco.gov.in](https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/) PDFs + [cdscoonline.gov.in](https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug) portal.
**Size:** 3,756 state NSQ · 3,058 CDSCO NSQ · 51 spurious · 3,040 makers.
**Used for:**
- Batch check from a strip photo, pack QR or bill
- Live recall alerts (WhatsApp + Hindi call)
- Watchlist and pharmacy stock re-checks
- Insights dashboard
- Maker record on the Save page

**Limit:** an alert covers one batch, not the whole brand.
**Load:** `python -m ingest.fetch`, `ingest.load`, `ingest.portal`

## 2. Indian Medicine Dataset
**What:** Indian medicine brands with MRP, maker, pack size and salts.
**Source:** [junioralive/Indian-Medicine-Dataset](https://github.com/junioralive/Indian-Medicine-Dataset) (MIT).
**Size:** 246,068 brands on sale · 7,624 makers (458 have CDSCO alerts).
**Used for:**
- **/save:** brands with the same salt, strength and form, cheapest per tablet first
- **Care → Today:** the family's monthly medicine spend, and how much they could save

**Example:** Telma 40 is ₹8.20 a tablet; the same salt is ₹0.65 (92% less).
**Limit:** listed MRPs, so shop prices can differ.
**Load:** `python -m ingest.medicines`

## 3. PhysioNet BIDMC
**What:** 8-minute bedside monitor recordings of 53 real ICU patients: pulse, SpO₂, breathing and the pulse waveform.
**Source:** [physionet.org/content/bidmc](https://physionet.org/content/bidmc/1.0.0/) (Pimentel et al., IEEE TBME 2016).
**Used for:**
- Live vitals demo: replays a real patient, not made-up numbers
- Testing the camera pulse reader against the hospital monitor

**Result:** 1.72 bpm average error, 100% within 5 bpm (5 patients).
**Limit:** only 5 of 53 pulse waveforms are downloaded so far.
**Load:** `python -m ingest.bidmc`

## 4. openFDA drug labels
**What:** Official US medicine labels, including their drug-interaction sections.
**Source:** [api.fda.gov/drug/label.json](https://open.fda.gov/apis/drug/label/).
**Used for:**
- Warnings when two of a patient's medicines mention each other (Care and the doctor console)

**Limit:** these are US labels; the app says "ask your doctor", never gives advice.

---

**Rules in code (not datasets):**
- NEWS2 early-warning score (RCP 2017)
- Adult vital-sign red flags
- PRR signal detection (Evans 2001)

**Storage:** everything is in `data/kincare.db` (gitignored). Raw downloads are in `data/raw/`. `run.bat` rebuilds it all.
