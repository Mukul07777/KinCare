"""Same medicine, lower price; medicine info; Jan Aushadhi stores."""
from fastapi import APIRouter, HTTPException, Query

from core import conn

router = APIRouter()


# ---- same medicine, lower price (Indian Medicine Dataset, 246k brands) ----

@router.get("/api/medicines/search")
def medicines_search(q: str = Query(..., min_length=2)):
    import prices

    return prices.search(conn, q)


@router.get("/api/medicines/{mid}/alternatives")
def medicines_alternatives(mid: int, limit: int = 20):
    import prices

    r = prices.alternatives(conn, mid, min(limit, 50))
    if not r:
        raise HTTPException(404, "We couldn't find this medicine. Search for it by name on Save")
    return r


@router.get("/api/medicines/{mid}/info")
def medicines_info(mid: int):
    """Uses, how to take, side effects and warnings by salt (FDA label), plus CDSCO alerts for the salt and price rank."""
    import medinfo

    r = medinfo.info(conn, mid)
    if not r:
        raise HTTPException(404, "We couldn't find this medicine. Search for it by name on Save")
    return r


@router.get("/api/stores/janaushadhi")
def janaushadhi(lat: float = Query(..., ge=6, le=38), lon: float = Query(..., ge=68, le=98)):
    """Nearest Jan Aushadhi Kendras (OpenStreetMap). Bounds are India's, so a bad location fails loudly."""
    import stores

    return stores.nearest(lat, lon)
