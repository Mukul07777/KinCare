# KinCare pitch: v2 deck script (about 6 minutes)

Deck: `pitch/KinCare_Pitch_Deck_v2.pptx`. The same words are in each slide's speaker notes.
Before you start, open `/demo` and press **Reset demo data**. Keep the backup video ready in a second tab.

| # | Slide | Time | Say this |
|---|---|---|---|
| 1 | Know the batch | 0:00 | Hands up if you've bought medicine for your parents. Keep it up if you know whether that exact batch failed a government test. ... Nobody. We're Team Avengers, and this is KinCare: know the batch, not just the brand. The red card is our real verdict screen, on a real batch CDSCO listed as spurious. Everything today runs live on real government data. |
| 2 | Nobody tells Dadi | 0:30 | Meet Dadi. Her BP tablet was made in January. Ten months later a lab finds that batch substandard, and CDSCO adds one line to a monthly PDF. A month later the strip is still in her pill box, two tablets a day. India publishes its failed batches every month. It has no way to tell the people holding them. KinCare is that missing last mile. |
| 3 | 10 months in homes | 1:00 | Dadi isn't an exception. From the dates printed on 6,000+ real CDSCO alerts: a failed batch takes a median of 10 months to be listed, and 99.5% are still in date when listed, with 14 months left. The red half is the regulator's problem. The amber half is ours, and KinCare closes it. |
| 4 | Three front doors | 1:30 | One alert database, three front doors. Families check a strip, QR or bill, or just send a WhatsApp photo. Pharmacies upload stock and every flagged batch becomes a task. Regulators see, for the first time, who still holds a failed batch. Pharmacies pay, so patients never do. |
| 5 | Workflow | 2:00 | Agents read every CDSCO list nightly. Each alert keeps a link to the regulator's PDF. We match the batch exactly, never fuzzily, so a near-miss can't raise a false alarm. Then we find who holds it and reach them on WhatsApp and a Hindi call, soonest next dose first. And we never say "safe", only "no alert found as of" a date and time. |
| 6 | Designed for Dadi | 2:30 | We design for Dadi, not developers. No app: a WhatsApp photo gets a Hindi answer. Hindi first, with English one tap away. Anyone else goes from photo to verdict in one tap. Honest words only. When the network drops: a plain message and a retry button, never an error dump. Phone-first, screen-reader friendly, a red SOS button always one tap away. |
| 7 | Live demo | 3:00 | **Switch to the browser, `/demo`, Start.** One patient, prescription to first dose. Risky combination flagged from FDA labels. Every batch checked. **Pause on step 4:** a recalled batch, caught before the first tablet. Who else holds it, ₹1,206 a year saved, WhatsApp reminders. Every step was a real API call. *If it fails: play the backup video and keep talking.* |
| 8 | Measured | 4:00 | We measure; we don't claim. 400 real flagged batches typed six ways: every one caught. 798 near-misses: zero false alarms. The benchmark caught a real bug (two companies sharing the word "Pharmaceuticals") and we fixed it. Under 32 users at once, the slowest requests went from 12 seconds to 33 ms. |
| 9 | Architecture | 4:30 | Deliberately simple: Next.js, one FastAPI service, one SQLite file. The data is 100 MB and changes nightly, so no database server is needed. A trigram index and cached summaries answer in milliseconds. 103 tests. Postgres later is one change. |
| 10 | Business | 5:00 | Patients free forever. Pharmacies pay ₹499 a month and their customers get KinCare free, so every store is a distribution channel. Worst case, with every WhatsApp message paid, every plan is profitable, and a test fails if that changes. On the right: the risks we designed for. |
| 11 | Progress | 5:20 | 345 tasks across 33 tracks in one shared file; 246 done, 71%, every line visible in our repo. What's left is honest: deploy, state sources, pilots. |
| 12 | Team | 5:40 | Two people as a relay: one codes, one rests, and every shift ends with a handoff note. Mukul: data foundation, WhatsApp, fake-pack radar, controller dashboard. Ashpreet: matcher, scan flow, pharmacy desk, blast radius, business model, performance. Every commit is in git. |
| 13 | Thank you | 6:00 | Next 30 days: ten pilot pharmacies, two state drug controllers. And one request for tonight: check the batch on your parents' medicines. Thank you. `/status` is open for live numbers. |

## Likely judge questions
- **"What if OCR misreads the batch?"** The user confirms every field, and matching is exact, so a misread finds nothing rather than a wrong alert.
- **"Is the data real?"** Yes: 6,865 alerts parsed from CDSCO PDFs, each linked to its source. Open `/status` for live accuracy.
- **"Liability?"** We never say safe, stop or switch. We show the regulator's notice and tell people to talk to their pharmacist.
- **"Why would pharmacies pay?"** Recall handling with an audit trail, plus customer loyalty, for ₹499 a month.
