"""KinCare API: the FastAPI app, its middleware, and one router per area (routes/).

Shared state and helpers (database connection, alert matching, device ids) live in core.py.
Background work (nightly ingest, dose reminders, caregiver alerts, cache warm-up, Telegram polling)
registers with core.on_startup and runs from the lifespan below.
"""
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import caregiver as caregiver_mod  # noqa: F401  (re-exported for tests)
import core
import sessions
import telegram  # noqa: F401  (re-exported for tests)
from core import (  # noqa: F401  (re-exported: tests and tools import these from main)
    NIGHTLY_HOUR_IST, _next_nightly, _refresh, _timings, alert_device, candidates, conn, now,
)
from routes import (
    account, alerts, blast_radius, care_plan, checkins, dadi, doctor_connect, emergency, family, live_vitals, medicines,
    notifications, pack_radar, pharmacy, pharmacy_desk, recall_live, reference, regulator, reports, switch_room, telegram_bot, watchlist,
    whatsapp_bot,
)
from routes.care_plan import send_due_reminders  # noqa: F401
from routes.dadi import _mark_taken_device, default_member  # noqa: F401
from routes.family import send_caregiver_alerts  # noqa: F401
from routes.telegram_bot import TG_BUTTONS, _tg_photo_task, telegram_handle  # noqa: F401
from routes.whatsapp_bot import _expired  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for start in core.STARTUP:  # in import order, as the old @app.on_event("startup") hooks ran
        start()
    yield


app = FastAPI(title="KinCare API", lifespan=lifespan)

# The web app calls the API through its own origin (Next.js rewrites /api), so browsers need no CORS at all.
# KINCARE_ORIGINS lists any other site allowed to call it with credentials (comma separated).
ORIGINS = [o.strip() for o in os.environ.get("KINCARE_ORIGINS", os.environ.get("PUBLIC_WEB_URL", "http://localhost:3000")).split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization", "X-KinCare"])

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",          # doctor / check-in links carry their token in the URL
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",  # JSON only; /docs gets the default below
}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def _guard(request: Request, call_next):
    """CSRF: a request authenticated by the session cookie that changes data must carry X-KinCare (a custom header another
    site can't add without a CORS preflight we refuse) and, when the browser says where it came from, an allowed Origin.
    Bearer-token clients and webhooks carry no cookie, so they are unaffected."""
    if request.method in UNSAFE and request.url.path.startswith("/api/") and sessions.COOKIE in request.cookies             and not request.headers.get("authorization", "").lower().startswith("bearer "):
        origin = request.headers.get("origin")
        own = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if request.headers.get("x-kincare") != "1" or (origin and origin not in ORIGINS and origin != own):
            return JSONResponse({"detail": "Blocked: request did not come from the KinCare app."}, status_code=403)
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        if k == "Content-Security-Policy" and request.url.path in ("/docs", "/redoc", "/openapi.json"):
            continue
        response.headers.setdefault(k, v)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")  # medical data never sits in a shared or browser cache
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    return response


@app.middleware("http")
async def _time_requests(request: Request, call_next):
    t = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    if path.startswith("/api") and "/stream" not in path and path != "/api/status":
        _timings.append((path, (time.perf_counter() - t) * 1000, response.status_code))
    return response


# Same order as the sections of the old single-file main.py, so route matching is unchanged.
for area in (alerts, recall_live, checkins, care_plan, pharmacy, watchlist, pharmacy_desk, reports, account, emergency, blast_radius,
             live_vitals, medicines, whatsapp_bot, regulator, pack_radar, notifications, reference, doctor_connect, family, dadi, telegram_bot,
             switch_room):
    app.include_router(area.router)
