"""Parse CDSCO / state alert PDFs into alert rows.

Columns differ between files, so headers are mapped by keyword. Tables that
continue onto later pages without a header reuse the last header seen.
"""
import re
from pathlib import Path

import pdfplumber

COLUMNS = {
    "product": ("product", "drug name", "name of"),
    "batch": ("batch",),
    "mfg_date": ("manufactur", "date of manuf", "mfg"),
    "expiry": ("expiry",),
    "manufacturer": ("manufactured by", "manufacturer"),
    "reason": ("nsq result", "reason", "result", "failure"),
    "reported_by": ("reported by", "drawn by", "laboratory"),
    "remarks": ("firm", "remarks"),
}


def clean(cell) -> str:
    s = (cell or "").replace("�", "'").replace("\n", " ")
    return " ".join(s.split()).strip(" '")


def map_header(row: list) -> dict | None:
    cells = [clean(c).lower() for c in row]
    # Header cells are short labels; data rows can mention "batch" inside long remarks.
    if not any("batch" in c and len(c) < 20 for c in cells) or max(len(c) for c in cells) > 60:
        return None
    mapping: dict[str, int] = {}
    # "manufactured by" must win over the "manufacturing date" column, so match specific keys first.
    for key in ("batch", "expiry", "manufacturer", "reported_by", "remarks", "product", "reason", "mfg_date"):
        for i, c in enumerate(cells):
            if i in mapping.values():
                continue
            if any(k in c for k in COLUMNS[key]):
                mapping[key] = i
                break
    return mapping if "product" in mapping and "batch" in mapping else None


def maker_name(full: str) -> str:
    """'M/s. Tam-Bran Pharmaceuticals Pvt. Ltd., Plot No...' -> 'Tam-Bran Pharmaceuticals Pvt. Ltd.'"""
    s = re.sub(r"^(m/s\.?|m/s)\s*", "", full, flags=re.I).strip()
    name = s.split(",")[0]
    # Drop address text glued after the company suffix: "Affine Formulations Ltd.1947/3" -> "... Ltd."
    name = re.sub(r"\b(Ltd|Limited|LLP)\b\.?.*$", lambda m: m.group(1) + ".", name, flags=re.I)
    return name.strip(" ,") or s


def brand_of(product: str) -> str:
    """Brand is usually before the bracket: 'Telma H (Telmisartan ...)' -> 'Telma H'.
    Generic-first names keep the bracket brand: '... Injection I.P. (Dexacos)' -> 'Dexacos'."""
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", product)
    if not m:
        return product
    head, inner = m.group(1).strip(), m.group(2).strip()
    generic = re.search(r"\b(i\.?p\.?|b\.?p\.?|u\.?s\.?p\.?|tablets?|injection|capsules?|syrup|suspension)\b", head, re.I)
    if generic and len(inner.split()) <= 3:
        return inner
    return head


def parse_pdf(path: Path) -> list[dict]:
    rows, header = [], None
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for raw in table:
                    h = map_header(raw)
                    if h:
                        header = h
                        continue
                    if not header or len(raw) <= max(header.values()):
                        continue
                    get = lambda k: clean(raw[header[k]]) if k in header else ""
                    # Some files split the product header over empty merged columns.
                    product = next((clean(raw[i]) for i in range(header["product"], header["batch"]) if clean(raw[i])), "")
                    batch = get("batch")
                    if not product or not batch or batch in ("-", "NA", "N/A"):
                        continue
                    full_maker = get("manufacturer")
                    rows.append({
                        "product_name": product,
                        "brand": brand_of(product),
                        "batch_no": batch,
                        "mfg_date": get("mfg_date"),
                        "expiry": get("expiry"),
                        "manufacturer": maker_name(full_maker) if full_maker else "",
                        "manufacturer_full": full_maker,
                        "reason": get("reason"),
                        "reported_by": get("reported_by"),
                        "remarks": get("remarks"),
                        "pdf_page": page_no,
                    })
    return rows
