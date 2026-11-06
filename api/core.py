"""Shared by every route module: the database connection, request timings, alert matching, startup hooks."""
import json
import re
import threading
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

import auth
import blast
import doctor as doctor_mod
import entitlements
import notify as notify_mod
import packs as packs_mod
import push
import roles
import sessions
import telegram
import vault
import whatsapp
from db import ThreadConnection
from ingest import bidmc, medicines as medicines_ingest
from matcher import match, normalise_batch

SOURCES = [
    {"id": "cdsco_nsq", "name": "CDSCO NSQ alerts"},
    {"id": "cdsco_spurious", "name": "CDSCO spurious-drug lists"},
    {"id": "state_nsq", "name": "State regulator NSQ alerts"},
]

conn = ThreadConnection()  # one sqlite connection per worker thread
doctor_mod.setup(conn)
conn.executescript(bidmc.SCHEMA)
conn.executescript(medicines_ingest.SCHEMA)
conn.executescript(packs_mod.SCHEMA)
conn.executescript(push.SCHEMA)
conn.executescript(whatsapp.SCHEMA)
conn.executescript(entitlements.SCHEMA)
conn.executescript(blast.SCHEMA)
conn.executescript(auth.SCHEMA)
conn.executescript(sessions.SCHEMA)
conn.executescript(roles.SCHEMA)
notify_mod.conn = conn

# Last 5,000 request timings, for the /status page's live p50/p95 (no external APM needed at this scale).
_STARTED = datetime.now(timezone.utc)
_timings: "deque[tuple[str, float, int]]" = deque(maxlen=5000)


_last_now = datetime.min.replace(tzinfo=timezone.utc)
_now_lock = threading.Lock()


def now() -> str:
    """UTC timestamp, strictly increasing. Windows' clock moves in ~15 ms steps, so two events in one step (a purchase,
    then a dose ticked) got the same time and "taken after the purchase" became a coin flip."""
    global _last_now
    with _now_lock:
        t = datetime.now(timezone.utc)
        _last_now = t if t > _last_now else _last_now + timedelta(microseconds=1)
        return _last_now.isoformat()


def rows(sql: str, args=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def candidates(batch: str) -> list[dict]:
    from matcher.core import LOOKALIKE_SQL, lookalike

    return rows(f"SELECT * FROM alerts WHERE batch_norm = ? OR {LOOKALIKE_SQL} = ?", (normalise_batch(batch), lookalike(batch)))


def run_check(batch: str, maker: str | None, brand: str | None) -> dict:
    import insights

    matches = match(candidates(batch), batch, maker, brand)
    for m in matches:
        m["explain"] = insights.failures_of(m["alert"]["reason"], m["alert"]["category"])
    hit_sources = {m["alert"]["source"] for m in matches}
    return {
        "verdict": "alert_found" if matches else "no_alert_found",
        "checked_at": now(),
        "sources": [{**s, "status": "match" if s["id"] in hit_sources else "no_match"} for s in SOURCES],
        "matches": matches,
    }


def _stats_now(one) -> dict:
    return ({
        "total": one("SELECT COUNT(*) FROM alerts"),
        "spurious": one("SELECT COUNT(*) FROM alerts WHERE category = 'spurious'"),
        "manufacturers": one("SELECT COUNT(DISTINCT manufacturer) FROM alerts WHERE manufacturer NOT LIKE '%investigation%'"),
        "documents": one("SELECT COUNT(*) FROM documents"),
        "coverage": rows("SELECT MIN(alert_month) AS start, MAX(alert_month) AS end FROM alerts")[0],
        "by_month": rows("SELECT alert_month AS month, COUNT(*) AS n FROM alerts GROUP BY alert_month ORDER BY alert_month"),
        "by_source": rows("SELECT source, COUNT(*) AS n FROM alerts GROUP BY source"),
        "top_manufacturers": rows(
            """SELECT manufacturer, COUNT(*) AS n FROM alerts
               WHERE manufacturer != '' AND manufacturer NOT LIKE '%investigation%'
               GROUP BY manufacturer ORDER BY n DESC LIMIT 8"""
        ),
        "last_ingest": one("SELECT MAX(ingested_at) FROM documents"),
    })


_stats_cache: dict = {}
_fill = threading.Lock()  # serialises cache fills (stats, datasets, insights) so a cold burst computes each once


_GENERIC = re.compile(r"\b(pharma\w*|labs?|laborator\w*|healthcare|life\s?sciences?|remedies|formulations?|drugs?|biotech\w*|medi\w*|industries|india|international)\b")


def _core(normalised: str) -> str:
    return " ".join(_GENERIC.sub(" ", normalised).split()) or normalised


_insights_cache: dict = {}


conn.execute("""CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY, trigger TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running', alerts_before INTEGER, alerts_after INTEGER, error TEXT)""")


def _refresh(trigger: str = "manual"):
    """Fetch newly published CDSCO PDFs + portal months and load them; every run is logged in ingest_runs."""
    from ingest import fetch, load, portal

    count = lambda: conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]  # noqa: E731
    run = conn.execute("INSERT INTO ingest_runs (trigger, started_at, alerts_before) VALUES (?,?,?)", (trigger, now(), count())).lastrowid
    try:
        fetch.main_for(limit=60)
        load.load()
        portal.load(since=datetime.now().year - 1)
        conn.execute("UPDATE ingest_runs SET status='ok', finished_at=?, alerts_after=? WHERE id=?", (now(), count(), run))
    except Exception as e:  # logged, not raised: a portal outage must not take the API down
        conn.execute("UPDATE ingest_runs SET status='failed', finished_at=?, alerts_after=?, error=? WHERE id=?", (now(), count(), str(e)[:300], run))


NIGHTLY_HOUR_IST = 2  # CDSCO posts lists during the day; 02:00 IST picks them up before anyone wakes


def _next_nightly() -> datetime:
    ist = timezone(timedelta(hours=5, minutes=30))
    t = datetime.now(ist).replace(hour=NIGHTLY_HOUR_IST, minute=0, second=0, microsecond=0)
    return t if t > datetime.now(ist) else t + timedelta(days=1)


def _phone(p: str | None) -> str | None:
    if not p:
        return None
    digits = re.sub(r"[^\d+]", "", p)
    if not digits.startswith("+"):
        digits = "+91" + digits[-10:]
    if not re.fullmatch(r"\+\d{10,15}", digits):
        raise HTTPException(400, "Phone number looks invalid")
    return digits


def _plans(dev: str, member: str | None = None) -> list[dict]:
    plans = rows("SELECT * FROM plans WHERE device = ?" + (" AND member = ?" if member else "") + " ORDER BY id DESC",
                 (dev, member) if member else (dev,))
    for p in plans:
        vault.open_row("plans", p)
        p["advice"] = json.loads(p["advice"] or "[]")
        p["medicines"] = rows("SELECT * FROM plan_meds WHERE plan_id = ?", (p["id"],))
    return plans


def alert_device(dev: str, title: str, body: str, url: str = "/care", tag: str | None = None, buttons: list[str] | None = None) -> int:
    """Phone notification + the person's own Telegram chat (both free). Returns how many deliveries went out."""
    return push.send(conn, dev, title, body, url, tag) + telegram.send_device(conn, dev, f"{title}\n{body}", role="self", buttons=buttons)


def _log_note(channel: str, name: str, phone: str | None, lang: str, batch: str | None, text: str, alert_id=None, urgent: bool = True) -> str:
    import notify

    status, pid = notify.send_whatsapp(phone, text, urgent) if phone else ("outbox", None)
    conn.execute("INSERT INTO notifications (channel, name, phone, language, batch, alert_id, message, status, provider_id) VALUES (?,?,?,?,?,?,?,?,?)",
                 (channel if phone else "in_app", name, phone or "", lang, batch, alert_id, text, status, pid))
    return status


# ---- who is calling: server-issued sessions (sessions.py), never an id the browser chooses ----

def session_token(request: Request) -> str | None:
    """HttpOnly cookie (the web app) or `Authorization: Bearer` (API clients, tests)."""
    auth_h = request.headers.get("authorization", "")
    if auth_h.lower().startswith("bearer "):
        return auth_h[7:].strip()
    return request.cookies.get(sessions.COOKIE)


def current_session(request: Request) -> dict:
    s = sessions.resolve(conn, session_token(request))
    if not s:
        raise HTTPException(401, "Session expired. Reload the page.")
    return s


def current_account(request: Request) -> str:
    """FastAPI dependency: the caller's account id. 401 without a live session."""
    account = current_session(request)["account"]
    entitlements.seen(conn, account)  # starts the 14-day trial on first use
    return account


def optional_account(request: Request) -> str | None:
    s = sessions.resolve(conn, session_token(request))
    return s["account"] if s else None


def signed_in_account(request: Request) -> str:
    """Sharing medical data (caregivers, doctor links) needs a verified phone on the sharing side."""
    s = current_session(request)
    if s["kind"] != "user":
        raise HTTPException(403, "Sign in with your phone number first: sharing health data needs a verified account.")
    return s["account"]


def _admin_token_ok(token: str | None) -> bool:
    import hmac
    import os

    want = os.environ.get("ADMIN_TOKEN")
    return bool(want and token and hmac.compare_digest(token, want))


def principal(request: Request) -> dict:
    """Who is calling and which roles they hold. Elevated roles only count on a signed-in (phone-verified) session."""
    if _admin_token_ok(request.headers.get("x-admin-token")):
        return {"account": None, "actor": "admin-token", "roles": {roles.ADMIN}}
    s = sessions.resolve(conn, session_token(request))
    if not s:
        raise HTTPException(401, "Session expired. Reload the page.")
    held = roles.of(conn, s["account"]) if s["kind"] == "user" else {roles.PATIENT}
    return {"account": s["account"], "actor": s["account"], "roles": held}


def require(permission: str):
    """FastAPI dependency factory: the caller must hold a role that carries `permission` (roles.PERMISSIONS)."""
    need = roles.PERMISSIONS[permission]

    def dep(request: Request) -> dict:
        p = principal(request)
        if not roles.allowed(p["roles"], permission):
            names = " or ".join(roles.LABEL[r] for r in need)
            raise HTTPException(403, f"This needs the {names} role. Request it on your Account page.")
        return p

    dep.permission = permission  # read by the security tests
    return dep


def _device(account: str) -> str:
    """Kept for call sites that pass an account id they already hold (Telegram, WhatsApp, doctor links)."""
    return account


# ---- demo mode and rate limits ----

def demo_mode() -> bool:
    """KINCARE_DEMO=1 (run.bat on a laptop): login codes shown on screen, simulators open. Never set it on a public server."""
    import os

    return os.environ.get("KINCARE_DEMO") == "1"


_hits: dict[str, deque] = {}
_hits_lock = threading.Lock()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else "") or (request.client.host if request.client else "?")


def rate_limit(request: Request, bucket: str, limit: int, per_seconds: int) -> None:
    """At most `limit` calls per `per_seconds` per client IP for this bucket; 429 past that."""
    import time

    key, now = f"{bucket}:{client_ip(request)}", time.monotonic()
    with _hits_lock:
        q = _hits.setdefault(key, deque())
        while q and now - q[0] > per_seconds:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
        q.append(now)



# Startup work registered by route modules (nightly ingest, reminder loops, cache warm-up, Telegram polling).
# main.py's lifespan runs them in import order, replacing FastAPI's deprecated @app.on_event("startup").
STARTUP: list = []


def on_startup(fn):
    STARTUP.append(fn)
    return fn
