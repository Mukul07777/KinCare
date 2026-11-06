"""Fake-pack radar: every pack QR scan is a sensor.

Schedule H2 QR / GS1 codes carry a serial that belongs to ONE physical pack. So the same serial
seen on several phones, in places too far apart to travel between, or with a different batch or
expiry than the first time it was seen, means the code was copied onto other packs.

Locations are rounded to 2 decimals (~1 km) before they are stored.
"""
import math
import sqlite3
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS pack_scans (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    serial TEXT NOT NULL,
    gtin TEXT,
    batch TEXT,
    expiry TEXT,
    lat REAL, lng REAL,
    city TEXT,
    origin TEXT NOT NULL DEFAULT 'user',
    at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pack_serial ON pack_scans(gtin, serial);
"""

FAR_KM = 50          # one pack can't be scanned in two places this far apart...
FAR_WINDOW_H = 24    # ...within this many hours
MANY_PHONES = 3      # a single pack is rarely scanned by this many different phones

# Reference cities, for a readable "near ..." label and the radar's backdrop.
CITIES = [
    ("Delhi", 28.61, 77.21), ("Mumbai", 19.08, 72.88), ("Kolkata", 22.57, 88.36), ("Chennai", 13.08, 80.27),
    ("Bengaluru", 12.97, 77.59), ("Hyderabad", 17.39, 78.49), ("Ahmedabad", 23.02, 72.57), ("Pune", 18.52, 73.86),
    ("Jaipur", 26.91, 75.79), ("Lucknow", 26.85, 80.95), ("Patna", 25.59, 85.14), ("Bhopal", 23.26, 77.41),
    ("Chandigarh", 30.73, 76.78), ("Guwahati", 26.14, 91.74), ("Bhubaneswar", 20.30, 85.82), ("Kochi", 9.93, 76.27),
    ("Indore", 22.72, 75.86), ("Nagpur", 21.15, 79.09), ("Varanasi", 25.32, 82.97), ("Srinagar", 34.08, 74.80),
    ("Raipur", 21.25, 81.63), ("Ranchi", 23.34, 85.31), ("Dehradun", 30.32, 78.03), ("Visakhapatnam", 17.69, 83.22),
]


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = map(lambda p: (math.radians(p[0]), math.radians(p[1])), (a, b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def near_city(lat: float | None, lng: float | None) -> str | None:
    if lat is None or lng is None:
        return None
    name, d = min(((n, km((lat, lng), (la, lo))) for n, la, lo in CITIES), key=lambda x: x[1])
    return name if d < 150 else None


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def assess(scans: list[dict]) -> dict:
    """Clone signals for one serial's scans (oldest first)."""
    first = scans[0]
    phones = {s["device"] for s in scans}
    reasons = []
    # Same serial, different batch or expiry: the code was copied and the pack's print doesn't match it.
    changed = [s for s in scans if (s["batch"] and first["batch"] and s["batch"] != first["batch"]) or
               (s["expiry"] and first["expiry"] and s["expiry"] != first["expiry"])]
    if changed:
        reasons.append({"kind": "mismatch", "text": f"Same serial with a different batch or expiry ({changed[0]['batch'] or changed[0]['expiry']} vs {first['batch'] or first['expiry']})"})
    # Two places too far apart for one pack in a day.
    placed = [s for s in scans if s["lat"] is not None]
    far = None
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            d = km((a["lat"], a["lng"]), (b["lat"], b["lng"]))
            hours = abs((_ts(b["at"]) - _ts(a["at"])).total_seconds()) / 3600
            if d > FAR_KM and hours <= FAR_WINDOW_H and a["device"] != b["device"] and (not far or d > far[0]):
                far = (d, a, b, hours)
    if far:
        reasons.append({"kind": "far", "text": f"Scanned {far[0]:.0f} km apart within {max(far[3], 0.1):.0f} h ({far[1]['city'] or 'one place'} and {far[2]['city'] or 'another'})"})
    if len(phones) >= MANY_PHONES:
        reasons.append({"kind": "phones", "text": f"Scanned on {len(phones)} different phones"})
    level = "clone" if (changed or far) else "watch" if len(phones) >= MANY_PHONES else "ok"
    return {"level": level, "reasons": reasons, "scans": len(scans), "phones": len(phones),
            "cities": sorted({s["city"] for s in scans if s["city"]}), "first_at": first["at"], "last_at": scans[-1]["at"]}


def record(conn: sqlite3.Connection, device: str, serial: str, gtin: str | None, batch: str | None, expiry: str | None,
           lat: float | None, lng: float | None, origin: str = "user", at: str | None = None) -> dict:
    lat = round(lat, 2) if lat is not None else None
    lng = round(lng, 2) if lng is not None else None
    conn.execute("INSERT INTO pack_scans (device, serial, gtin, batch, expiry, lat, lng, city, origin, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (device, serial, gtin, batch, expiry, lat, lng, near_city(lat, lng), origin, at or datetime.now(timezone.utc).isoformat()))
    conn.commit()
    scans = history(conn, gtin, serial)
    res = assess(scans)
    res["seen_before"] = len(scans) > 1
    res["you_before"] = sum(s["device"] == device for s in scans) > 1
    return res


def history(conn: sqlite3.Connection, gtin: str | None, serial: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM pack_scans WHERE serial = ? AND COALESCE(gtin, '') = COALESCE(?, '') ORDER BY at, id", (serial, gtin))]


def radar(conn: sqlite3.Connection) -> dict:
    """Every serial worth a look, plus totals, for the radar page."""
    keys = conn.execute("SELECT COALESCE(gtin, '') AS gtin, serial, COUNT(*) AS n FROM pack_scans GROUP BY 1, 2").fetchall()
    rings = []
    for k in keys:
        if k["n"] < 2:
            continue
        scans = history(conn, k["gtin"] or None, k["serial"])
        a = assess(scans)
        if a["level"] == "ok":
            continue
        rings.append({**a, "serial": k["serial"], "gtin": k["gtin"] or None, "batch": scans[0]["batch"],
                      "simulated": all(s["origin"] == "simulated" for s in scans),
                      "points": [{"lat": s["lat"], "lng": s["lng"], "city": s["city"], "at": s["at"], "batch": s["batch"]} for s in scans if s["lat"] is not None]})
    rings.sort(key=lambda r: (r["level"] != "clone", -r["scans"]))
    tot = conn.execute("SELECT COUNT(*), COUNT(DISTINCT COALESCE(gtin,'') || '|' || serial), COUNT(DISTINCT device) FROM pack_scans").fetchone()
    return {"scans": tot[0], "packs": tot[1], "phones": tot[2], "clones": sum(r["level"] == "clone" for r in rings),
            "rings": rings, "cities": [{"name": n, "lat": la, "lng": lo} for n, la, lo in CITIES]}


# A clone ring for the stage: one real flagged batch, one copied serial, seen across cities in hours.
DEMO_ROUTE = [("Delhi", 0, None), ("Lucknow", 3, None), ("Patna", 7, None), ("Kolkata", 11, "TAMPERED"), ("Ranchi", 15, None), ("Varanasi", 19, None)]


def seed_demo(conn: sqlite3.Connection, gtin: str, serial: str, batch: str, expiry: str | None) -> int:
    clear_demo(conn)
    start = datetime.now(timezone.utc) - timedelta(hours=20)
    pos = {n: (la, lo) for n, la, lo in CITIES}
    for i, (city, h, flag) in enumerate(DEMO_ROUTE):
        la, lo = pos[city]
        record(conn, f"sim-radar-{i}", serial, gtin, batch if not flag else batch[:-1] + "X", expiry, la + 0.03, lo - 0.02,
               origin="simulated", at=(start + timedelta(hours=h)).isoformat())
    return len(DEMO_ROUTE)


def clear_demo(conn: sqlite3.Connection) -> int:
    n = conn.execute("DELETE FROM pack_scans WHERE origin = 'simulated'").rowcount
    conn.commit()
    return n
