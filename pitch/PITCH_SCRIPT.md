# KinCare pitch script (Hinglish, ~3½ min, one story)

One line per idea. Pause at line breaks. **[ACTION]** = do this on stage.
**Run it from `pitch/KinCare_Pitch_Deck.pptx`** (script in the speaker notes) and switch to the live site at the demo slide: `/demo` → `/whatsapp` → `/blast` → `/radar` → `/controller`. Keep `/status` open for "is this real?".
The story: **Dadi's medicine fails a government test. KinCare knows she has it, sees her body react, and reaches her before her next tablet.**
Short on time? Drop 3b and 4b first (the story still works); never drop 4 or 5.

---

### 1. Hook (15 s)
Good morning judges. Hum hain Team Avengers.
Aap mein se kitne logon ne mummy-papa ke liye dawai khareedi hai? Sab ne.
Kitne logon ko pata hai ki woh exact batch sarkari test mein fail hua ya nahi? Kisi ko nahi.
**Know the batch, not just the brand.** Yeh hai KinCare.

### 2. The number nobody has shown you (25 s)
**[ACTION: home page → scroll to "Ten months in homes"]**
Humne CDSCO ke **6,000 se zyada** real alerts ki manufacture aur expiry dates nikaali.
Ek fail batch, banne ke baad, CDSCO list tak pahunchne mein median **10 mahine** leta hai.
Aur jab list hota hai, **99.5%** batches tab bhi expiry ke andar hote hain, median **14 mahine** baaki.
Matlab: list aane tak dawai ghar mein hai, log kha rahe hain. Aur unhe koi batata hi nahi.

### 3. Live: Dadi's journey (45 s)
**[ACTION: /demo → Start the demo (tick "Also alert this phone")]**
Doctor ka prescription: chaar dawaiyan. KinCare ne turant pakda: Warf aur Ecosprin saath mein risky hain, official label se.
Dadi ne Crocin khareedi: batch check, saaf. WhatsApp: "abhi dawai lijiye", aur **reply 1** karo, dose tick ho jaata hai.
Ab chauthi dawai... **[pause]** batch AT25-0938A. Yeh real CDSCO list par hai.
Pehli goli se pehle hi, alert. Aur yeh dekhiye, judge ke phone par bhi notification.
Saath mein: wahi salt, clean company se, **₹1,206 saal ki bachat.**

### 3b. No app needed: WhatsApp (15 s)
**[ACTION: /whatsapp → tap "Namik-MR strip"]**
Lekin Dadi app nahi kholti. Woh WhatsApp pe strip ki **photo** bhejti hain.
KinCare photo se batch padhta hai, check karta hai, aur Hindi mein jawab: "yeh batch fail hai, dawai mat lijiye."

### 4. The innovation: blast radius (45 s)
**[ACTION: in the recall step click "Who else holds this batch" → /blast]**
Regulator sirf batata hai kaunsa batch fail hua. KinCare jaanta hai **kis ke paas hai**.
Yeh radar hai. Har dot ek insaan jiske ghar yeh batch hai. Laal matlab: **agli goli ek ghante mein.**
Aur yeh dekhiye: **"Is this batch hurting anyone?"** lagbhag ek-tihai logon ki pulse, yeh batch shuru karne ke baad, badh gayi.
Yeh diagnosis nahi hai. Yeh signal hai, jo regulator ki list se pehle aata hai.
**[ACTION: "Alert 30 people · next dose first"]**
Ek click. Jiski goli sabse pehle, use sabse pehle message. **[dots turn teal]**
(Yeh log simulated hain, par batch real CDSCO wala hai. Simulated logon ko kabhi message nahi jaata.)

### 4b. Fakes give themselves away: pack radar (25 s)
**[ACTION: /radar (demo ring loaded) → hand a judge your phone at /scan → QR → scan the Telma H test code on the laptop]**
2023 se top 300 brands ke pack par QR code hai, har pack ka alag serial.
Nakli banane wale yeh code copy karte hain. Par ek pack ek hi jagah ho sakta hai.
Yahi serial Delhi, Lucknow, Patna, Kolkata mein, 20 ghante mein scan hua, aur Kolkata mein batch number bhi alag. **Copy pakdi gayi.**
**[judge's phone shows "⚠️ This pack code looks copied"]** Har scan ek sensor hai.

### 4c. For the regulator (10 s)
**[ACTION: /controller]**
Aur drug controller ke liye ek screen: kaunsa fail batch abhi bhi gharon mein hai, kitno ko alert gaya, kaunse code copy hue. Sabse urgent pehle.

### 5. Business (20 s)
**[ACTION: /pricing]**
Safety hamesha free. Har patient ko recall alert free.
Basic ₹29, Family ₹69 mahina, WhatsApp reminders aur poore parivaar ke liye.
Asli revenue pharmacies se: ₹499 mahina, pehla mahina free.
Aur jo pharmacy pay karti hai, uske customers ko reminders free milte hain. **Pharmacy humara distribution hai.**
Har plan worst case mein bhi profit mein hai. Humne WhatsApp ka kharcha cap kiya hai, aur test likha hai jo fail ho jaata hai agar kabhi loss ho.

### 6. Close (15 s)
Real data: 6,865 CDSCO alerts, 2.46 lakh medicine brands, real ICU recordings, openFDA. Kuch bhi hardcoded nahi. 86 automated tests.
Agle 30 din: 10 pilot pharmacies, real WhatsApp, state drug controllers ke saath baat.
Aur aaj raat ek kaam kijiye: **apne mummy-papa ki dawai ka batch check kijiye.** Thank you!

---

## Before going on stage (checklist)
- [ ] Deployed URL open on the laptop **and** on one phone (docs/setup/DEPLOY.md). Sign in once on the phone.
- [ ] `/demo` run once beforehand (warms the openFDA labels; the first run is ~6 s slower).
- [ ] `/demo` → **Reset demo data** (one click clears every simulated row; real users are never touched).
- [ ] `/blast?batch=AT250938A`: *Load simulated holders*, so it's fresh and un-alerted.
- [ ] `/radar`: *Load demo ring*. Keep the Telma H QR test code open on the laptop (`/scan` → QR → the small QR icon) for the judge to scan.
- [ ] Phone notifications ON on the stage phone (Care → Turn on reminders).
- [ ] If WhatsApp keys are set: judge's number added in Meta as a test recipient; they send "hi" first.
- [ ] Optional: `KINCARE_ALL_ACCESS=1` so no plan limit appears on stage.
- [ ] Backup video ready (below) in case Wi-Fi fails.

## Backup video (~2 min, record with Win+Alt+R)
1. Home page: the "Ten months in homes" section (5 s)
2. /demo: Start, all steps appear, then the phone mockup messages (25 s)
3. /whatsapp: send the Namik-MR strip photo, the Hindi alert comes back (10 s)
4. /blast: radar, then the body-signal panel, then *Alert* with the dots turning teal (25 s)
5. /radar: the copied-code route across cities, then a phone scanning the test code and getting the warning (15 s)
6. /controller: the action queue (5 s), then /pricing (10 s)

## Judges' likely questions
- **"Is the data real?"** Yes: CDSCO's own portal, 2019–2026. The 10-month figure is computed from the dates printed on each alert (`/api/insights/recall-gap`).
- **"False alarms?"** The batch number is matched exactly, never fuzzy. A near-miss never raises an alert.
- **"Do you tell people to change medicines?"** Never. We show prices and record facts; switching is the doctor's or pharmacist's call.
- **"The body signal is just correlation."** Yes, and we say so on screen: "changed since starting, not caused by". It's a reason to see a doctor and an early signal for regulators, not a diagnosis.
- **"Can't a fake pack copy the QR?"** Yes, and that's how we catch it. One pack has one serial: the same serial in cities hours apart, on many phones, or printed with a different batch is a copied code (`/radar`). We still never claim a single pack is genuine.
- **"Voice in Hindi, really?"** Browser speech recognition (hi-IN). Brand names come back in Devanagari (डोलो), so KinCare transliterates and matches by sound; tested on Dolo, Telma, Pan, Crocin, Ecosprin, Thyronorm, Glycomet.
- **"Who pays for the controller view?"** It's free for regulators: it makes KinCare the trusted channel, and pharmacies pay because the regulator watches recalls through it.
- **"Why won't 1mg build this?"** They earn by selling stock. Warning about failed stock and pointing to cheaper makers works against them. KinCare is independent and works on what the patient actually holds.
- **"How do you get users?"** Pharmacies pay ₹499, and their customers get KinCare free. Every store is a distribution channel.
