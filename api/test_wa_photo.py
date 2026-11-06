import os
import tempfile
from pathlib import Path

os.environ.setdefault("KINCARE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import whatsapp  # noqa: E402

client = TestClient(main.app)
STRIPS = Path(__file__).resolve().parents[1] / "web" / "public" / "test-strips"


def test_incoming_images_reads_photo_and_image_document_only():
    body = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "919812345678", "type": "image", "image": {"id": "MEDIA1", "mime_type": "image/jpeg", "caption": "check"}},
        {"from": "919812345678", "type": "document", "document": {"id": "DOC1", "mime_type": "image/png"}},
        {"from": "919812345678", "type": "document", "document": {"id": "PDF1", "mime_type": "application/pdf"}},
        {"from": "919812345678", "type": "text", "text": {"body": "hi"}},
    ]}}]}]}
    assert whatsapp.incoming_images(body) == [("+919812345678", "MEDIA1", "check"), ("+919812345678", "DOC1", "")]


def test_expired_strip_dates():
    assert main._expired("01/2020") and main._expired("3-21")
    assert not main._expired("10/2099") and not main._expired(None) and not main._expired("13/2020")


def test_simulated_photo_of_flagged_strip_gets_alert():
    if not (STRIPS / "namik-mr.png").exists():
        return
    main.conn.execute("""INSERT INTO alerts (source, category, product_name, brand, batch_no, batch_norm, manufacturer, reason, alert_month, alert_url)
                         VALUES ('state_nsq', 'nsq', 'Aceclofenac, Paracetamol & Chlorzoxazone Tablets', 'Namik-MR', 'AT25-0938A', 'AT250938A',
                                 'Aspo Pharmaceuticals LLP.', 'Assay', '2026-09', 'https://cdsco.gov.in/x')""")
    main.conn.commit()
    with open(STRIPS / "namik-mr.png", "rb") as f:
        r = client.post("/api/whatsapp/simulate", files={"image": ("s.png", f, "image/png")}).json()
    assert r["read"]["batch"] == "AT25-0938A" and r["read"]["verdict"] == "alert_found"
    assert r["reply"].startswith("📷") and "Namik-MR" in r["reply"]
    with open(STRIPS / "amlodipine-clean.png", "rb") as f:
        clean = client.post("/api/whatsapp/simulate", files={"image": ("c.png", f, "image/png")}).json()
    assert clean["read"]["verdict"] == "no_alert_found" and "AML24017" in clean["reply"]
    assert client.post("/api/whatsapp/simulate", params={"text": "hi"}).json()["reply"]
