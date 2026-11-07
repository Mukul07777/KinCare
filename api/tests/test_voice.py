import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from testutil import auth_as  # noqa: E402
import prices  # noqa: E402
import voice  # noqa: E402
from ingest.medicines import maker_key, parse_pack, salt_part  # noqa: E402

client = TestClient(main.app)
ROWS = [  # as in the Indian Medicine Dataset
    (8101, "Dolo 650 Tablet", 34.25, "Micro Labs Ltd", "strip of 15 tablets", "Paracetamol (650mg)"),
    (8102, "Alice 650mg Tablet", 4.97, "Alice Pharma Pvt Ltd", "strip of 15 tablets", "Paracetamol (650mg)"),
    (8103, "PAN 40 Tablet", 155.0, "Alkem Laboratories Ltd", "strip of 15 tablets", "Pantoprazole (40mg)"),
    (8104, "Pain X MR Tablet", 60.0, "Some Pharma Ltd", "strip of 10 tablets", "Aceclofenac (100mg)"),
    (8105, "Crocin Advance Tablet", 20.0, "GlaxoSmithKline", "strip of 15 tablets", "Paracetamol (500mg)"),
]


def setup_module():
    for mid, name, price, maker, pack, comp in ROWS:
        form, qty, unit = parse_pack(pack)
        main.conn.execute("INSERT OR REPLACE INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (mid, name, name.lower(), price, maker, maker_key(maker), pack, salt_part(comp), salt_part(comp), form, qty, unit, price / qty))
    main.conn.commit()
    prices._maker_alerts = None


def test_transliteration_and_sound():
    assert voice.translit("डोलो 650") == "dolo 650"
    assert voice.translit("टेल्मा") == "telma"
    assert voice.translit("थायरोनॉर्म") == "thayronorm"
    assert voice.sound("Crocin") == voice.sound("krosin")


def ask(text, lang="hi"):
    return client.post("/api/dadi/chat", json={"text": text, "lang": lang}, headers=auth_as("voice-test")).json()


def test_hindi_price_question_finds_brand_and_clean_cheaper_one():
    r = ask("डोलो 650 कितने की आती है")
    assert r["kind"] == "price" and r["data"]["medicine"]["name"] == "Dolo 650 Tablet"
    assert r["data"]["cheapest"]["name"] == "Alice 650mg Tablet" and "डॉक्टर" in r["say"]


def test_brand_word_matched_by_sound_not_substring():
    assert ask("पैन 40 कितने का है")["data"]["medicine"]["name"] == "PAN 40 Tablet"  # not "Pain X MR"
    # No strength spoken, so any Crocin is a right answer (other test files add Crocin 1000mg too).
    assert ask("क्रोसिन कितने की है")["data"]["medicine"]["name"].startswith("Crocin")


def test_emergency_first_greeting_and_help():
    e = ask("दादी को साँस नहीं आ रही, डोलो दी थी")
    assert e["kind"] == "emergency" and "108" in e["say"]
    assert ask("namaste")["kind"] == "hello"
    assert ask("kuch bhi random baat")["kind"] == "help"
    assert ask("how much is Dolo 650", "en")["say"].startswith("Dolo 650 Tablet costs")
