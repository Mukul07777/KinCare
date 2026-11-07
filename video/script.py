"""Narration for the KinCare demo video: scenes -> cues. About 70% English, 30% Hindi (Hinglish).

Hindi is written in Devanagari so the Hindi neural voice pronounces it naturally; English stays in Latin script.
Each cue is synthesised separately so on-screen animations start exactly when their line is spoken.
"""

VOICE = "hi-IN-MadhurNeural"   # reads Hinglish naturally: Hindi in Devanagari, English in Latin
RATE = "+20%"

SCENES = [
    ("who", [
        "This is Dadi. Seventy-two, five medicines a day.",
        "Her son Rahul is in Bengaluru, her daughter Priya buys the medicines, and Mr. Verma is their pharmacist.",
        "यह है दादी की care team.",
    ]),
    ("problem", [
        "India's regulator, CDSCO, lists every batch that fails a quality test. We pulled seven thousand nine hundred and twenty real alerts.",
        "A batch is listed about ten months after it was made, and ninety-nine point six percent are still within expiry.",
        "मतलब दवाई अभी भी घर में है।",
        "About two hundred a month, and one in four is an elder's daily medicine.",
        "और दादी को, कोई नहीं बताता।",
    ]),
    ("solution", [
        "Meet KinCare. Know the batch, decide together.",
        "It turns the family's Telegram group into a Switch room, with four AI agents: Scan, Pharmacist, Dose Buddy and Recall Watcher.",
        "One room, one shared record, for every person and every agent.",
    ]),
    ("demo", [
        "Dadi sends a photo. The Scan agent reads the exact batch.",
        "Flagged. Hindi और English में बताता है: दवाई अपने आप बंद मत करो।",
        "Then it hands off to the Pharmacist agent, on its own.",
        "Same three salts, makers with no alerts, price per tablet.",
        "But nothing changes, until a human pharmacist approves.",
        "Mr. Verma replies: approve one.",
        "The decision and task are saved as Switch room documents. Rahul buys it, and Dose Buddy moves Dadi's nine A.M. dose.",
        "सब कुछ, एक ही room में।",
    ]),
    ("proof", [
        "And this is real. Our team, in a real Telegram group, with Claude Code agents run by Switch Console.",
    ]),
    ("desk", [
        "For pharmacists, the Pharmacy Desk room shows every home a flagged batch reached. One alert, हर घर तक।",
    ]),
    ("tech", [
        "Real CDSCO data, our own OCR, two hundred and thirty-three tests in CI. Free for families, pharmacies pay.",
    ]),
    ("close", [
        "KinCare. क्योंकि दादी की दवाई, पूरे परिवार की ज़िम्मेदारी है। Built on Switch, by Team Avengers.",
    ]),
]
