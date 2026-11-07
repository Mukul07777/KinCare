"""Narration for the KinCare demo video: scenes -> cues. About 70% English, 30% Hindi (Hinglish).

Hindi is written in Devanagari so the Hindi neural voice pronounces it naturally; English stays in Latin script.
Each cue is synthesised separately so on-screen animations start exactly when their line is spoken.
"""

VOICE = "hi-IN-SwaraNeural"   # warm, natural Hinglish: Hindi in Devanagari, English in Latin
RATE = "+12%"

SCENES = [
    ("who", [
        "Meet Dadi. She's seventy-two, and takes five medicines a day.",
        "Her son Rahul lives in Bengaluru, Priya picks up her medicines, and Mr. Verma is their pharmacist.",
        "तो असल में, यह है दादी की care team.",
    ]),
    ("problem", [
        "Here's what most families don't know. CDSCO lists every batch that fails a quality test. We went through seven thousand, nine hundred and twenty real alerts.",
        "A batch shows up on that list about ten months after it was made. And by then, ninety-nine point six percent are still within expiry.",
        "मतलब, वो दवाई अभी भी घरों में है।",
        "That's about two hundred batches a month. And one in four, is something elders take daily.",
        "और दादी को, कोई बताता ही नहीं।",
    ]),
    ("solution", [
        "So, we built KinCare. Know the batch, and decide together.",
        "It turns the family's Telegram group into a Switch room, with four AI agents.",
        "People and agents, all working from one room, and one shared record.",
    ]),
    ("web", [
        "And it's not only chat. KinCare is a full website too.",
        "Scan a real strip, and every government source is checked, in seconds.",
        "The Care network page shows every agent, every family room, and the Pharmacy Desk, live.",
        "Search every alert, look after parents from anywhere, और Dadi mode, जो बोलकर जवाब देता है।",
    ]),
    ("demo", [
        "Dadi sends a photo, and the Scan agent reads the exact batch.",
        "It's flagged. And it tells her, in Hindi and English: दवाई अपने आप बंद मत करना।",
        "Then, on its own, it passes the case to the Pharmacist agent.",
        "Same three salts, from makers with no alerts, and the price per tablet.",
        "But nothing changes, until a real pharmacist says yes.",
        "Mr. Verma replies: approve one.",
        "The decision and task are saved as Switch room documents, and Dose Buddy moves Dadi's nine A.M. dose.",
        "सब कुछ, एक ही room में।",
    ]),
    ("proof", [
        "And this is real. Our team, a real Telegram group, Claude Code agents on Switch.",
    ]),
    ("desk", [
        "The Pharmacy Desk shows every home a flagged batch reached. एक alert, हर घर तक।",
    ]),
    ("tech", [
        "Real CDSCO data, our own OCR, two hundred thirty-three tests. Free for families, pharmacies pay.",
    ]),
    ("close", [
        "KinCare. क्योंकि दादी की दवाई, पूरे परिवार की ज़िम्मेदारी है।",
    ]),
]
