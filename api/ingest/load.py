"""Parse downloaded PDFs (data/raw_pdfs/index.json) into the alerts database.

Usage: python -m ingest.load        (after python -m ingest.fetch)
Safe to re-run: documents already ingested are skipped.
"""
import json
from pathlib import Path

from db import connect
from ingest.fetch import OUT
from ingest.parse import parse_pdf
from matcher import normalise_batch


def source_of(doc: dict) -> str:
    if doc["category_hint"] == "spurious":
        return "cdsco_spurious"
    return "state_nsq" if doc["issuer"] == "state" else "cdsco_nsq"


def load() -> dict:
    conn = connect()
    docs = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
    added_docs = added_rows = 0
    for d in docs:
        if conn.execute("SELECT 1 FROM documents WHERE url = ?", (d["url"],)).fetchone():
            continue
        path = Path(OUT / d["file"])
        if not path.is_file():
            # Listed in index.json but not downloaded (fetch --limit keeps only the newest). Skip it and
            # keep loading the rest; one missing file must never lose every other document's alerts.
            print(f"  skipped (not downloaded): {d['file']}")
            continue
        rows = parse_pdf(path)
        if not rows:
            print(f"  no table rows (scanned or notice): {d['title'][:60]}".encode("ascii", "replace").decode())
        src = source_of(d)
        link = d.get("pdf_url") or d["url"]
        cur = conn.execute(
            "INSERT INTO documents (title, source, alert_month, published, url, pdf_url, file, rows) VALUES (?,?,?,?,?,?,?,?)",
            (d["title"], src, d["alert_month"], d["published"], d["url"], d.get("pdf_url"), d["file"], len(rows)),
        )
        doc_id = cur.lastrowid
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO alerts (document_id, source, category, product_name, brand, batch_no, batch_norm,
                   mfg_date, expiry, manufacturer, manufacturer_full, reason, reported_by, remarks, alert_month, alert_url, pdf_page)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (doc_id, src, "spurious" if src == "cdsco_spurious" else "nsq", r["product_name"], r["brand"], r["batch_no"],
                 normalise_batch(r["batch_no"]), r["mfg_date"], r["expiry"], r["manufacturer"], r["manufacturer_full"],
                 r["reason"], r["reported_by"], r["remarks"], d["alert_month"], link, r["pdf_page"]),
            )
        added_docs += 1
        added_rows += len(rows)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    print(f"Added {added_docs} documents, {added_rows} rows. Alerts in DB: {total}")
    return {"documents": added_docs, "rows": added_rows, "total": total}


if __name__ == "__main__":
    load()
