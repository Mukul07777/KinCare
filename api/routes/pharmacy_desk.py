"""Pharmacy recall desk: per-device desk state."""
import json

from fastapi import APIRouter, Depends

from core import conn, require

router = APIRouter()


# ---- per-device pharmacy recall desk state ----

@router.get("/api/pharmacy/state")
def pharmacy_get(who: dict = Depends(require("sales.manage"))):
    r = conn.execute("SELECT state FROM pharmacy_state WHERE device = ?", (who["account"],)).fetchone()
    return json.loads(r["state"]) if r else None


@router.put("/api/pharmacy/state")
def pharmacy_put(state: dict, who: dict = Depends(require("sales.manage"))):
    account = who["account"]
    conn.execute(
        """INSERT INTO pharmacy_state (device, state, updated_at) VALUES (?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(device) DO UPDATE SET state = excluded.state, updated_at = CURRENT_TIMESTAMP""",
        (account, json.dumps(state)),
    )
    conn.commit()
    return {"ok": True}
