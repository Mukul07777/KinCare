"""Drug-controller dashboard."""
from fastapi import APIRouter, Depends

from core import conn, require

router = APIRouter()


# ---- drug-controller dashboard ----

@router.get("/api/controller")
def controller_overview(state: str | None = None, _: dict = Depends(require("controller.view"))):
    import controller

    return controller.overview(conn, state or None)
