"""Per-device watchlist of batches KinCare keeps re-checking."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core import _phone, alert_device, conn, current_account, now, rows, run_check

router = APIRouter()


# ---- per-device watchlist (no accounts yet) ----

class WatchIn(BaseModel):
    batch: str
    brand: str | None = None
    maker: str | None = None
    phone: str | None = None
    name: str | None = None
    language: str = "hi"
    member: str | None = None  # who in the family takes it
    expiry: str | None = None  # as printed, e.g. "01/2027"


@router.get("/api/watchlist")
def watchlist(account: str = Depends(current_account)):
    return rows("SELECT * FROM watchlist WHERE device = ? ORDER BY added_at DESC", (account,))


@router.post("/api/watchlist")
def watch_add(w: WatchIn, account: str = Depends(current_account)):
    dev = account
    r = run_check(w.batch, w.maker, w.brand)
    conn.execute(
        """INSERT INTO watchlist (device, batch, brand, maker, added_at, last_verdict, last_checked_at, phone, name, language, member, expiry)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(device, batch) DO UPDATE SET brand=excluded.brand, maker=excluded.maker,
           last_verdict=excluded.last_verdict, last_checked_at=excluded.last_checked_at,
           phone=COALESCE(excluded.phone, watchlist.phone), name=COALESCE(excluded.name, watchlist.name), language=excluded.language,
           member=COALESCE(excluded.member, watchlist.member), expiry=COALESCE(excluded.expiry, watchlist.expiry)""",
        (dev, w.batch, w.brand, w.maker, now(), r["verdict"], r["checked_at"], _phone(w.phone), w.name, w.language, w.member, w.expiry),
    )
    conn.commit()
    return {"ok": True, "verdict": r["verdict"]}


@router.post("/api/watchlist/recheck")
def watch_recheck(account: str = Depends(current_account)):
    dev = account
    changed = []
    for w in rows("SELECT * FROM watchlist WHERE device = ?", (dev,)):
        r = run_check(w["batch"], w["maker"], w["brand"])
        if r["verdict"] != w["last_verdict"]:
            changed.append(w["batch"])
            if r["verdict"] == "alert_found":
                a = r["matches"][0]["alert"]
                alert_device(dev, f"⛔ Batch {w['batch']} is now flagged", f"{a['product_name']} ({a['alert_month']}). Stop using it and speak to your pharmacist.",
                          "/watchlist", f"watch-{w['batch']}")
        conn.execute(
            "UPDATE watchlist SET last_verdict = ?, last_checked_at = ? WHERE device = ? AND batch = ?",
            (r["verdict"], r["checked_at"], dev, w["batch"]),
        )
    conn.commit()
    return {"changed": changed, "items": watchlist(account)}


@router.delete("/api/watchlist/{batch}")
def watch_remove(batch: str, account: str = Depends(current_account)):
    conn.execute("DELETE FROM watchlist WHERE device = ? AND batch = ?", (account, batch))
    conn.commit()
    return {"ok": True}
