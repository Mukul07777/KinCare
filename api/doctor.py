"""Doctor connect: a private, expiring link that lets the patient's own doctor watch live vitals,
see medicines and adherence, and send advice back. Plus NEWS2, the early-warning score wards use.

KinCare still never suggests a medicine. Advice only ever comes from the doctor.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS vitals_live (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    member TEXT NOT NULL,
    at TEXT NOT NULL,
    pulse INTEGER, spo2 INTEGER,
    source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_live_dev ON vitals_live(device, member, id);
CREATE TABLE IF NOT EXISTS doctor_links (
    token TEXT PRIMARY KEY,
    device TEXT NOT NULL,
    member TEXT NOT NULL,
    doctor TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER DEFAULT 0,
    last_seen TEXT
);
CREATE TABLE IF NOT EXISTS doctor_messages (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL,
    device TEXT NOT NULL,
    member TEXT NOT NULL,
    author TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    at TEXT NOT NULL,
    read_at TEXT
);
"""

KINDS = {"note", "advice", "followup", "urgent", "call"}
SOURCES = {"ble_hr", "ble_oximeter", "camera", "replay", "health_connect", "healthkit"}  # replay = recorded ICU patient (BIDMC)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def setup(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def new_link(conn, device: str, member: str, doctor: str | None, hours: int) -> dict:
    token = secrets.token_urlsafe(18)
    expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    conn.execute("INSERT INTO doctor_links (token, device, member, doctor, created_at, expires_at) VALUES (?,?,?,?,?,?)",
                 (token, device, member, doctor, now(), expires))
    conn.commit()
    return {"token": token, "member": member, "doctor": doctor, "expires_at": expires, "room": room(token)}


def link(conn, token: str) -> dict | None:
    """The link if it's still valid. Expired or revoked links return None."""
    r = conn.execute("SELECT * FROM doctor_links WHERE token = ?", (token,)).fetchone()
    if not r or r["revoked"] or r["expires_at"] < now():
        return None
    return dict(r)


def room(token: str) -> str:
    # The video room name is derived, so the share token itself never reaches the video provider.
    return "kincare-consult-" + hashlib.sha256(token.encode()).hexdigest()[:16]


def news2(temp_c, sys_, pulse, spo2) -> dict:
    """NEWS2 (Royal College of Physicians, 2017) from the vitals we have.
    Respiration rate and consciousness aren't measured at home, so this is a partial score and says so."""
    parts = {}
    if spo2 is not None:
        parts["spo2"] = 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0
    if sys_ is not None:
        parts["bp"] = 3 if sys_ <= 90 or sys_ >= 220 else 2 if sys_ <= 100 else 1 if sys_ <= 110 else 0
    if pulse is not None:
        parts["pulse"] = 3 if pulse <= 40 or pulse >= 131 else 2 if pulse >= 111 else 1 if pulse <= 50 or pulse >= 91 else 0
    if temp_c is not None:
        parts["temp"] = 3 if temp_c <= 35.0 else 2 if temp_c >= 39.1 else 1 if temp_c <= 36.0 or temp_c >= 38.1 else 0
    score = sum(parts.values())
    if score >= 7:
        risk, action = "high", "Emergency assessment"
    elif score >= 5:
        risk, action = "medium", "Urgent review by a clinician"
    elif any(v == 3 for v in parts.values()):
        risk, action = "low-medium", "Urgent review (one parameter in the red zone)"
    else:
        risk, action = "low", "Routine monitoring"
    return {"score": score, "risk": risk, "action": action, "parts": parts, "partial": True,
            "missing": ["respiration rate", "consciousness (ACVPU)"]}


def latest(conn, device: str, member: str) -> dict:
    """Most recent value of each vital, from either a typed reading or the live stream."""
    out = {"temp_c": None, "bp_sys": None, "bp_dia": None, "pulse": None, "spo2": None}
    at = {}
    for r in conn.execute("SELECT * FROM vitals WHERE device = ? AND member = ? ORDER BY at DESC LIMIT 40", (device, member)):
        for k in out:
            if out[k] is None and r[k] is not None:
                out[k], at[k] = r[k], r["at"]
    live = conn.execute("SELECT * FROM vitals_live WHERE device = ? AND member = ? ORDER BY id DESC LIMIT 1", (device, member)).fetchone()
    if live:
        for k in ("pulse", "spo2"):
            if live[k] is not None and (k not in at or live["at"] >= at[k]):
                out[k], at[k] = live[k], live["at"]
    return {**out, "at": at}


def live_stats(conn, device: str, member: str, minutes: int = 60 * 24) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    r = conn.execute(
        """SELECT COUNT(*) n, MIN(pulse) pmin, MAX(pulse) pmax, AVG(pulse) pavg, MIN(spo2) smin, AVG(spo2) savg,
                  SUM(spo2 < 92) dips, SUM(pulse > 120) tachy FROM vitals_live WHERE device = ? AND member = ? AND at >= ?""",
        (device, member, since)).fetchone()
    return {k: (round(r[k], 1) if isinstance(r[k], float) else r[k]) for k in r.keys()}


def median(xs: list) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
