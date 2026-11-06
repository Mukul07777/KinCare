"""Live recall engine: run a recall, stream its progress, notifications log."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import roles

from core import _phone, conn, demo_mode, require, rows

router = APIRouter()


# ---- live recall engine ----

class RecallIn(BaseModel):
    scope: str = "latest"  # "latest" = newest published list, "all" = every alert
    demo_phone: str | None = None
    demo_name: str | None = None
    demo_language: str = "hi"
    demo_city: str | None = None


@router.post("/api/recall/run")
def recall_run(body: RecallIn, who: dict = Depends(require("recall.run"))):
    import recall

    demo = None
    if body.demo_phone:
        # Messaging a typed-in number is a stage-demo tool: admins only (or the laptop demo), never any pharmacist.
        if not (demo_mode() or roles.allowed(who["roles"], "recall.demo_contact")):
            raise HTTPException(403, "Only an admin can add a demo contact.")
        # The demo contact holds a real batch from the newest list.
        latest = rows("SELECT brand, batch_no FROM alerts WHERE alert_month = (SELECT MAX(alert_month) FROM alerts) ORDER BY category DESC, id LIMIT 1")[0]
        demo = {"phone": _phone(body.demo_phone), "name": body.demo_name, "language": body.demo_language,
                "batch": latest["batch_no"], "brand": latest["brand"], "city": body.demo_city}
    run_id = recall.start(body.scope, demo)
    roles.audit(conn, who["actor"], "recall.run", run_id, f"scope={body.scope}" + (" +demo contact" if demo else ""))
    conn.commit()
    return {"run_id": run_id}


@router.get("/api/recall/stream/{run_id}")
async def recall_stream(run_id: str, _: dict = Depends(require("recall.run"))):
    import asyncio

    from fastapi.responses import StreamingResponse

    async def gen():
        last, idle = 0, 0
        while idle < 600:  # stop after ~5 min of silence
            evs = rows("SELECT id, type, payload, at FROM events WHERE run_id = ? AND id > ? ORDER BY id", (run_id, last))
            for e in evs:
                last = e["id"]
                yield f"event: {e['type']}\ndata: {e['payload']}\n\n"
                if e["type"] == "run_complete":
                    return
            idle = 0 if evs else idle + 1
            if not evs:
                yield ": keep-alive\n\n" if idle % 20 == 0 else ""
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/api/recall/config")
def recall_config():
    import agents
    import notify

    return {"agents": agents.mode(), "twilio": notify.twilio_ready(), "whatsapp": notify.whatsapp_ready(),
            "sources": [{"id": s["id"], "name": s["name"], "url": s["url"]} for s in agents.SOURCES]}


@router.get("/api/notifications")
def notifications(run_id: str | None = None, limit: int = Query(50, le=500), who: dict = Depends(require("notifications.view"))):
    """Messages KinCare sent. Regulators see who was reached with the phone masked; only admins see full numbers."""
    out = (rows("SELECT * FROM notifications WHERE run_id = ? ORDER BY id", (run_id,)) if run_id
           else rows("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)))
    if roles.ADMIN not in who["roles"]:
        for n in out:
            n["phone"] = _mask(n.get("phone"))
    return out


def _mask(p: str | None) -> str | None:
    return f"{p[:3]} ••••• {p[-4:]}" if p and len(p) > 7 else p


@router.get("/api/ask")
def ask_endpoint(q: str = Query(..., min_length=2, max_length=300)):
    import ask

    return ask.answer(conn, q)
