"""Matcher accuracy guards: real maker-name pairs from CDSCO alerts, plus the benchmark on the real alert table."""
import sqlite3
from pathlib import Path

import pytest

from matcher.core import _maker_score

# Different firms that only share an industry word. Before the fix these scored 84-90 ("strong").
DIFFERENT = [
    ("Biodeal Pharmaceuticals Ltd.", "Sakthi Ayurveda Pharmaceuticals"),
    ("Macmillon Pharmaceuticals Pvt Ltd.", "Concept Pharmaceuticals Ltd."),
    ("Zim Laboratories Limited.", "Ethicare Laboratories"),
    ("Modern Laboratories", "J.M.Laboratories"),
    ("Synokem Pharmaceuticals Ltd.", "VADSP Pharmaceuticals"),
    ("Swiss Garnier Life Sciences", "IHL Lifesciences Pvt. Ltd."),
    ("Mfg By: Revat Laboratories Pvt.Ltd.", "Tidal Laboratories Pvt. Ltd."),
]
# The same firm, written the way strips, bills and OCR write it.
SAME = [
    ("Paksons pharmaceuticals Private Limited", "M/s Paksons Pharmaceuticals Pvt. Ltd."),
    ("Glenmark Pharmaceuticals Ltd.", "glenmarkpharmaceuticals"),
    ("MMG Healthcare", "MMGHealthcare"),
    ("Hema Laboratories Pvt Ltd.", "HemaLaboratories"),
    ("IHL Lifesciences Pvt. Ltd.", "IHL LIFESCIENCES PVT. LTD."),
    ("Spen Formulations Pvt. Ltd.", "SpenFormulations"),
]


@pytest.mark.parametrize("a,b", DIFFERENT)
def test_shared_industry_word_is_not_a_maker_match(a, b):
    assert _maker_score(a, b) < 80


@pytest.mark.parametrize("a,b", SAME)
def test_same_maker_respelled_still_matches(a, b):
    assert _maker_score(a, b) >= 80


REAL_DB = Path(__file__).resolve().parent.parent / "data" / "kincare.db"


@pytest.mark.skipif(not REAL_DB.exists(), reason="needs the real alert database")
def test_benchmark_on_real_alerts():
    import quality
    from matcher import normalise_batch

    conn = sqlite3.connect(REAL_DB)
    conn.row_factory = sqlite3.Row
    lookup = lambda b: [dict(r) for r in conn.execute("SELECT * FROM alerts WHERE batch_norm = ?", (normalise_batch(b),))]  # noqa: E731
    r = quality.measure(conn, lookup, n=300)
    assert r["false_alarms"] == 0 and r["recall_pct"] == 100.0
    assert r["wrong_maker_marked_strong"] <= 2 and r["right_maker_strong_pct"] >= 98
