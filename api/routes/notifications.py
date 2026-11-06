"""Phone notifications (Web Push) and care savings."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import push

from core import _plans, conn, current_account

router = APIRouter()


# ---- phone notifications (Web Push) ----

class PushSubIn(BaseModel):
    endpoint: str
    keys: dict


@router.get("/api/push/key")
def push_key(account: str = Depends(current_account)):
    return {"key": push.public_key(), "subscribed": push.has_subs(conn, account)}


@router.post("/api/push/subscribe")
def push_subscribe(s: PushSubIn, account: str = Depends(current_account)):
    if not push.ready():
        raise HTTPException(503, "Phone notifications are not set up on this server (pip install pywebpush)")
    if not s.endpoint.startswith("https://") or not {"p256dh", "auth"} <= s.keys.keys():
        raise HTTPException(400, "Invalid push subscription")
    push.subscribe(conn, account, s.model_dump())
    return {"ok": True}


@router.delete("/api/push/subscribe")
def push_unsubscribe(endpoint: str | None = None, account: str = Depends(current_account)):
    push.unsubscribe(conn, account, endpoint)
    return {"ok": True}


@router.post("/api/push/test")
def push_test(account: str = Depends(current_account)):
    n = push.send(conn, account, "KinCare notifications are on", "You'll get dose, refill and recall alerts here, even with KinCare closed.", "/care", "test")
    return {"sent": n}


@router.get("/api/care/savings")
def care_savings(member: str | None = None, account: str = Depends(current_account)):
    import prices

    meds = [m for p in _plans(account, member) for m in p["medicines"]]
    return prices.plan_savings(conn, meds)
