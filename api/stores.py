"""Nearest Jan Aushadhi Kendras (government generic-medicine stores), live from OpenStreetMap.

OSM coverage is partial, so the page always offers a maps search too. Results cached per ~1 km cell.
"""
import math
import re
import time

import requests

OVERPASS = ("https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter")
HEADERS = {"User-Agent": "KinCare/1.0 (medicine-safety app)"}
NAME = "jan ?aushadh|janaushadh|jan ?aushdh|pmbj|bhartiya jan"
_NAME_RE = re.compile(NAME, re.I)
_cache: dict[tuple, tuple[float, list]] = {}
TTL = 3600


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def parse(elements: list[dict], lat: float, lon: float) -> list[dict]:
    out, seen = [], set()
    for e in elements:
        t = e.get("tags", {})
        y, x = e.get("lat", e.get("center", {}).get("lat")), e.get("lon", e.get("center", {}).get("lon"))
        if y is None or x is None:
            continue
        key = (round(y, 4), round(x, 4))
        if key in seen:
            continue
        seen.add(key)
        addr = ", ".join(v for v in (t.get("addr:housenumber"), t.get("addr:street"), t.get("addr:suburb"), t.get("addr:city"), t.get("addr:postcode")) if v)
        out.append({"name": t.get("name", "Jan Aushadhi Kendra"), "address": addr or None, "phone": t.get("phone") or t.get("contact:phone"),
                    "hours": t.get("opening_hours"), "lat": y, "lon": x, "km": round(km(lat, lon, y, x), 2),
                    "directions": f"https://www.google.com/maps/dir/?api=1&destination={y},{x}"})
    return sorted(out, key=lambda s: s["km"])


def _query(lat: float, lon: float, radius_m: int) -> list[dict]:
    # Fetch every pharmacy nearby and match names here: a case-insensitive regex on the server times out.
    near = f"(around:{radius_m},{lat},{lon})"
    q = f"""[out:json][timeout:25];
(nwr["amenity"="pharmacy"]{near};
 nwr["shop"="chemist"]{near};);
out center tags;"""
    last = None
    for url in OVERPASS:
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=30)
            if r.ok:
                return [e for e in r.json().get("elements", []) if _NAME_RE.search(e.get("tags", {}).get("name", ""))]
            last = f"{url}: HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(last or "OpenStreetMap unavailable")


def nearest(lat: float, lon: float, limit: int = 10) -> dict:
    """Never fails: if the public OSM servers are down, the page still gets the maps search."""
    maps = f"https://www.google.com/maps/search/Jan+Aushadhi+Kendra/@{lat},{lon},13z"
    cell = (round(lat, 2), round(lon, 2))
    hit = _cache.get(cell)
    if hit and time.time() - hit[0] < TTL:
        stores = hit[1]
    else:
        try:
            stores = []
            for radius in (6000, 15000):  # widen once if nothing is close
                stores = parse(_query(lat, lon, radius), lat, lon)
                if stores:
                    break
        except RuntimeError as e:
            return {"stores": [], "error": f"OpenStreetMap is busy ({str(e)[:120]})", "maps_search": maps, "source": "OpenStreetMap"}
        _cache[cell] = (time.time(), stores)
    return {"stores": stores[:limit], "error": None, "source": "OpenStreetMap contributors (ODbL), live via Overpass", "maps_search": maps}
