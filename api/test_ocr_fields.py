from ocr import extract_fields


def batch(*texts):
    lines = [{"text": t, "conf": 0.9, "height": 20, "top": i * 30, "left": 0} for i, t in enumerate(texts)]
    return extract_fields(lines)["fields"]["batch"]


def test_batch_read_with_ocr_zero_for_o():
    # Real OCR output from a strip: "No." came back as "N0."
    assert batch("Namik-MR", "B.N0.AT25-0938A", "EXP.10/2027") == "AT25-0938A"
    assert batch("Telma H", "B.No. 05240198") == "05240198"
    # A batch that starts with 0 right after "B.N" keeps its zero.
    assert batch("B.N05240198") == "05240198"
    assert batch("Batch N0: KT24117") == "KT24117"


# ---- clean-up of real-foil OCR (first real strip: Micro Labs paracetamol, read as "aracelamolTableisIP") ----
from ocr import tidy_brand, tidy_maker  # noqa: E402

SALTS = frozenset({"paracetamol", "amlodipine", "telmisartan", "propranolol", "baclofen", "mineral"})


def test_generic_line_is_repaired():
    assert tidy_brand("aracelamolTableisIP", SALTS) == "Paracetamol Tablets IP"   # lost first letter, glued, l read as i
    assert tidy_brand("AmlodipineTabletsIP", SALTS) == "Amlodipine Tablets IP"
    assert tidy_brand("Telmisartan Tablets IP 40 mg", SALTS) == "Telmisartan Tablets IP 40 mg"


def test_brand_lines_are_never_changed():
    # Without IP / BP / USP a line is a brand: correcting it renamed real brands (Bacfen -> Baclofen, Inderal -> Mineral)
    for b in ("Bacfen", "Inderal F 5 Tablet SR", "Mytrip 75mg", "DavaIndia Allopurinol 100mg", "Mucogel", "BACIPEN 500MG CAPSULE", "Telma H"):
        assert tidy_brand(b, SALTS) == b


def test_maker_boilerplate_removed():
    assert tidy_maker("MICRO LABS Trade Mark Proprietor") == "Micro Labs"
    assert tidy_maker("Regd. Trade Mark of SUN PHARMA LABORATORIES LTD") == "SUN Pharma Laboratories Ltd"
    assert tidy_maker("Glenmark Pharmaceuticals Ltd., Sikkim") == "Glenmark Pharmaceuticals Ltd"
    assert tidy_maker("Aspo Pharmaceuticals LLP") == "Aspo Pharmaceuticals LLP"
    assert tidy_maker(None) is None


# ---- real phone photos (Dolo-500, Dolo-650, Paracip-500): glued labels, 0 for O, warning text in large type ----

def brand(*lines):
    return extract_fields([{"text": t, "conf": 0.9, "height": h, "top": i * 30, "left": 0} for i, (t, h) in enumerate(lines)])["fields"]["brand"]


def test_batch_glued_to_next_label_and_zero_for_o():
    assert batch("B.NoDFNY0223MFG.MAY2026EXP.APR.2030") == "DFNY0223"
    assert batch("B.No. D0BS4480 MFG.MAY.2026") == "DOBS4480"
    assert batch("B.No. 05240198") == "05240198"   # digits only: zeros stay


def test_brand_skips_warnings_and_reads_misread_strength():
    assert brand(("Overdose may be injurious to Liver", 90), ("Dolo-650", 60), ("Dolo-650", 30)) == "Dolo-650"
    assert brand(("Dol0-500", 182), ("Dolo-500 Dolo-500", 170), ("Dolo-500", 85)) == "Dolo-500"
    assert brand(("TollFreeNo:1800120143143", 300), ("Paracetamol IP", 229),
                 ("PARACIP-500 Antipyretic & Relief from Body Pain", 617), ("q.s PARACIP-500 500mg", 427)) == "PARACIP-500"
