"""Narration for the KinCare demo video: scenes -> cues. About 70% English, 30% Hindi (Hinglish).

Hindi is written in Devanagari so the Hindi neural voice pronounces it naturally; English stays in Latin script.
Each cue is synthesised separately so on-screen animations start exactly when their line is spoken.
"""

VOICE = "hi-IN-SwaraNeural"   # warm, natural Hinglish: Hindi in Devanagari, English in Latin
RATE = "+12%"

SCENES = [
    ("who", [
        "Meet Dadi. She's seventy-two, and she takes five medicines, every single day.",
        "Her son Rahul lives in Bengaluru. Her daughter Priya picks up the medicines. And Mr. Verma, their local pharmacist, knows every strip she takes.",
        "तो असल में, यह है दादी की care team.",
    ]),
    ("problem", [
        "Now, here's something most families don't know. India's drug regulator, CDSCO, lists every batch that fails a quality test. We went through seven thousand, nine hundred and twenty real alerts.",
        "A batch shows up on that list about ten months after it was made. And by then, ninety-nine point six percent are still within expiry.",
        "मतलब, वो दवाई अभी भी घरों में है।",
        "That's about two hundred batches a month. And one in four, is something elders take daily.",
        "और दादी को, कोई बताता ही नहीं।",
    ]),
    ("solution", [
        "So, we built KinCare. Know the batch, and decide together.",
        "It turns the family's Telegram group into a Switch room, with four AI agents: Scan, Pharmacist, Dose Buddy, and Recall Watcher.",
        "People and agents, all working from one room, and one shared record.",
    ]),
    ("demo", [
        "Let's see it. Dadi sends a photo of her strip, and the Scan agent reads the exact batch.",
        "It's flagged. And it tells her, in Hindi and English: दवाई अपने आप बंद मत करना।",
        "Then, on its own, it passes the case to the Pharmacist agent.",
        "Same three salts, from makers with no alerts, and the price per tablet.",
        "And here's the important part. Nothing changes, until a real pharmacist says yes.",
        "Mr. Verma replies: approve one.",
        "The decision and the task are saved as Switch room documents. Rahul picks up the new strip, and Dose Buddy moves Dadi's nine A.M. dose.",
        "सब कुछ, एक ही room में।",
    ]),
    ("proof", [
        "And yes, this is real. Our team, in a real Telegram group, with Claude Code agents running on Switch.",
    ]),
    ("desk", [
        "For pharmacists, the Pharmacy Desk shows every home a flagged batch has reached. एक alert, हर घर तक।",
    ]),
    ("tech", [
        "It runs on real CDSCO data, our own OCR, and two hundred and thirty-three tests. Families use it free. Pharmacies pay.",
    ]),
    ("close", [
        "KinCare. क्योंकि दादी की दवाई, पूरे परिवार की ज़िम्मेदारी है। Built on Switch, by Team Avengers.",
    ]),
]
