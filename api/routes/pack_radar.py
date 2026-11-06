"""Fake-pack radar: every QR scan is a sensor."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import conn, current_account, require

router = APIRouter()


# ---- fake-pack radar: every QR scan is a sensor ----

class PackScanIn(BaseModel):
    serial: str
    gtin: str | None = None
    batch: str | None = None
    expiry: str | None = None
    lat: float | None = None
    lng: float | None = None


@router.post("/api/packs/scan")
def packs_scan(b: PackScanIn, account: str = Depends(current_account)):
    """Log one pack-code scan and say whether this serial looks copied."""
    import packs

    serial = b.serial.strip()[:64]
    if not serial:
        raise HTTPException(400, "This code has no pack serial")
    if (b.lat is None) != (b.lng is None) or (b.lat is not None and not (-90 <= b.lat <= 90 and -180 <= b.lng <= 180)):
        raise HTTPException(400, "Bad location")
    return packs.record(conn, account, serial, (b.gtin or "").strip()[:20] or None,
                        (b.batch or "").strip()[:32] or None, (b.expiry or "").strip()[:10] or None, b.lat, b.lng)


@router.get("/api/packs/radar")
def packs_radar():
    import packs

    return packs.radar(conn)


# The QR test code on /scan (Telma H, a real CDSCO spurious batch) carries this GTIN + serial.
DEMO_PACK = {"gtin": "08901234567890", "serial": "TST0001", "batch": "05240198", "expiry": "2027-01"}


@router.post("/api/packs/demo")
def packs_demo(_: dict = Depends(require("demo.seed"))):
    import packs

    return {"seeded": packs.seed_demo(conn, **DEMO_PACK), **DEMO_PACK}


@router.delete("/api/packs/demo")
def packs_demo_clear(_: dict = Depends(require("demo.seed"))):
    import packs

    return {"cleared": packs.clear_demo(conn)}
