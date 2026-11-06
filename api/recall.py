"""The recall engine: new alert list -> affected people -> notified.

One run:
  1. agents read every source in parallel
  2. the alert store is synced
  3. the latest published list is taken as the new list
  4. every watched batch and every pharmacy sale is matched against it
  5. each affected person gets a WhatsApp message and a voice call
Every step is written to `events`, which the live screen streams.
"""
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import agents
import checkin
import notify
from db import connect
from ingest import portal
from matcher import match, normalise_batch

_lock = threading.Lock()


class Run:
    def __init__(self, conn):
        self.conn = conn
        self.id = uuid.uuid4().hex[:12]
        self.t0 = time.time()

    def emit(self, type_: str, payload: dict):
        payload = {**payload, "t": round(time.time() - self.t0, 2)}
        with _lock:
            self.conn.execute("INSERT INTO events (run_id, type, payload) VALUES (?,?,?)", (self.id, type_, json.dumps(payload, default=str)))
            self.conn.commit()


def contacts(conn, demo: dict | None) -> list[dict]:
    people = [
        {"kind": "watchlist", "name": r["name"], "phone": r["phone"], "language": r["language"] or "hi",
         "batch": r["batch"], "brand": r["brand"], "maker": r["maker"], "where": "Personal watchlist", "city": None}
        for r in conn.execute("SELECT * FROM watchlist WHERE phone IS NOT NULL AND phone != ''")
    ]
    people += [
        {"kind": "sale", "name": r["customer"], "phone": r["phone"], "language": r["language"] or "hi",
         "batch": r["batch"], "brand": r["product"], "maker": None, "where": r["pharmacy"], "city": r["city"]}
        for r in conn.execute("SELECT * FROM sales WHERE phone IS NOT NULL AND phone != ''")
    ]
    if demo and demo.get("phone"):
        people.append({"kind": "demo", "name": demo.get("name"), "phone": demo["phone"], "language": demo.get("language", "hi"),
                       "batch": demo["batch"], "brand": demo.get("brand"), "maker": None, "where": "Live demo", "city": demo.get("city")})
    return people


def execute(run: Run, scope: str, demo: dict | None):
    conn = run.conn
    run.emit("run_started", {"mode": agents.mode(), "sources": [{"id": s["id"], "name": s["name"]} for s in agents.SOURCES]})

    # 1. Fan out: one agent per source, all at once.
    def one(src):
        try:
            rows = agents.run_source(src, run.emit)
            run.emit("agent_done", {"source": src["id"], "rows": len(rows)})
        except Exception as e:
            run.emit("agent_failed", {"source": src["id"], "error": str(e)})

    with ThreadPoolExecutor(max_workers=len(agents.SOURCES)) as pool:
        list(pool.map(one, agents.SOURCES))

    # 2. Sync the store (idempotent; adds only months not yet ingested).
    before = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    try:
        with _lock:
            portal.load(since=time.gmtime().tm_year)
    except Exception as e:
        run.emit("sync_failed", {"error": str(e)})
    after = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    # 3. The list being recalled.
    latest = conn.execute("SELECT MAX(alert_month) FROM alerts").fetchone()[0]
    where = "" if scope == "all" else "WHERE alert_month = ?"
    target = [dict(r) for r in conn.execute(f"SELECT * FROM alerts {where}", () if scope == "all" else (latest,))]
    run.emit("list_ready", {"month": latest, "alerts": len(target), "new_in_db": after - before, "scope": scope})

    by_batch: dict[str, list[dict]] = {}
    for a in target:
        by_batch.setdefault(a["batch_norm"], []).append(a)

    # 4. Match people holding those batches.
    hits = []
    people = contacts(conn, demo)
    for p in people:
        cands = by_batch.get(normalise_batch(p["batch"]), [])
        found = match(cands, p["batch"], p["maker"], p["brand"])
        if found:
            hits.append((p, found[0]))
            a = found[0]["alert"]
            run.emit("match", {"who": p["name"], "where": p["where"], "city": p["city"], "batch": p["batch"], "kind": p["kind"],
                               "medicine": a.get("brand") or a["product_name"], "category": a["category"], "level": found[0]["score"]["level"]})
    run.emit("matching_done", {"checked": len(people), "affected": len(hits)})

    # 5. Notify.
    for p, m in hits:
        a = m["alert"]
        lang = p["language"] if p["language"] in ("hi", "en") else "hi"
        with _lock:
            token = checkin.create(conn, name=p["name"], phone=p["phone"], language=lang, batch=p["batch"], alert_id=a["id"])
            conn.commit()
        text = notify.whatsapp_text(a, p["batch"], p["name"], lang, checkin.link(token))
        script = notify.voice_script(a, p["batch"], p["name"], lang)
        for channel, sender, body in (("whatsapp", lambda: notify.send_whatsapp(p["phone"], text), text),
                                      ("voice", lambda: notify.place_call(p["phone"], script, lang), script)):
            try:
                status, pid = sender()
            except Exception as e:
                status, pid = "failed", str(e)[:200]
            with _lock:
                conn.execute(
                    "INSERT INTO notifications (run_id, channel, name, phone, language, batch, alert_id, message, status, provider_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (run.id, channel, p["name"], p["phone"], lang, p["batch"], a["id"], body, status, pid),
                )
                conn.commit()
            run.emit("notified", {"channel": channel, "who": p["name"], "phone": _mask(p["phone"]), "language": lang,
                                  "status": status, "message": body, "checkin": checkin.link(token)})

    run.emit("run_complete", {"seconds": round(time.time() - run.t0, 1), "affected": len(hits),
                              "notifications": len(hits) * 2, "twilio": notify.twilio_ready()})


def _mask(phone: str) -> str:
    return phone[:-6] + "••••" + phone[-2:] if len(phone) > 6 else phone


def start(scope: str = "latest", demo: dict | None = None) -> str:
    conn = connect()
    run = Run(conn)
    threading.Thread(target=execute, args=(run, scope, demo), daemon=True).start()
    return run.id
