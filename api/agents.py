"""Alert-source agents.

With TINYFISH_API_KEY set, each source is read by a TinyFish web agent
(live browser, plain-English goal, output_schema for fixed fields).
Without it, the same sources are read by our direct fetchers. Both paths
emit the same events, so the live screen works either way.
"""
import os
from datetime import datetime
from typing import Callable

from ingest import portal

Emit = Callable[[str, dict], None]

# One agent per source: where it starts and what it must return.
SOURCES = [
    {
        "id": "portal_nsq",
        "name": "CDSCO NSQ portal",
        "url": "https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug",
        "tab": "nsq",
        "goal": "Open the Not of Standard Quality drugs list. Select the most recent reporting month. "
                "Return every row with product_name, brand_name, batch_no, manufacturer, nsq_result, reported_by, reporting_month.",
    },
    {
        "id": "portal_spurious",
        "name": "CDSCO spurious list",
        "url": "https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug",
        "tab": "spurious",
        "goal": "Open the Spurious drugs tab. Select the most recent reporting month. "
                "Return every row with product_name, brand_name, batch_no, manufacturer, nsq_result, reported_by, reporting_month.",
    },
    {
        "id": "cdsco_alerts_page",
        "name": "CDSCO alerts page",
        "url": "https://cdsco.gov.in/opencms/opencms/en/Notifications/Alerts/",
        "tab": None,
        "goal": "List the five most recent drug alert documents with title, published date and the PDF link.",
    },
]

ROW_SCHEMA = {
    "type": "object",
    "properties": {"rows": {"type": "array", "items": {"type": "object", "properties": {
        k: {"type": "string"} for k in
        ("product_name", "brand_name", "batch_no", "manufacturer", "nsq_result", "reported_by", "reporting_month", "title", "published", "link")
    }}}},
}


def mode() -> str:
    return "tinyfish" if os.environ.get("TINYFISH_API_KEY") else "direct"


def run_tinyfish(src: dict, emit: Emit) -> list[dict]:
    from tinyfish import RunStatus, TinyFish

    client = TinyFish()
    result: dict = {}
    stream = client.agent.stream(
        url=src["url"],
        goal=src["goal"],
        output_schema=ROW_SCHEMA,
        on_started=lambda e: emit("agent_started", {"source": src["id"], "run_id": getattr(e, "run_id", None)}),
        on_streaming_url=lambda e: emit("agent_stream", {"source": src["id"], "streaming_url": getattr(e, "streaming_url", None)}),
        on_progress=lambda e: emit("agent_progress", {"source": src["id"], "step": getattr(e, "purpose", "")}),
        on_complete=lambda e: result.update(status=getattr(e, "status", None), result=getattr(e, "result_json", None) or getattr(e, "result", None), error=getattr(e, "error", None)),
    )
    for _ in stream:  # drive the stream; callbacks emit the events
        pass
    if result.get("status") != RunStatus.COMPLETED:
        raise RuntimeError(str(result.get("error") or result.get("status")))
    data = result.get("result") or {}
    return data.get("rows", []) if isinstance(data, dict) else []


def run_direct(src: dict, emit: Emit) -> list[dict]:
    emit("agent_started", {"source": src["id"], "run_id": None})
    if src["tab"] is None:
        from ingest.fetch import discover

        emit("agent_progress", {"source": src["id"], "step": "Reading the CDSCO alerts table"})
        docs = sorted(discover(), key=lambda d: datetime.strptime(d["published"], "%Y-%b-%d"), reverse=True)[:5]
        return [{"title": d["title"], "published": d["published"], "link": d["url"]} for d in docs]

    emit("agent_progress", {"source": src["id"], "step": "Listing reporting months"})
    months = portal.months_for(src["tab"], since=2026)
    latest = months[-1]
    emit("agent_progress", {"source": src["id"], "step": f"Reading {latest} list"})
    env = portal.fetch(src["tab"], latest, refresh=True)
    rows = env["payload"].get("aaData") or []
    return [{
        "product_name": r.get("str_product_name") or r.get("product_name_from_dtl"),
        "brand_name": r.get("str_brand_name"),
        "batch_no": r.get("str_batch_no"),
        "manufacturer": r.get("str_manufactured_by"),
        "reporting_month": r.get("dt_reporting_month_year"),
    } for r in rows]


def run_source(src: dict, emit: Emit) -> list[dict]:
    if mode() == "tinyfish":
        try:
            return run_tinyfish(src, emit)
        except Exception as e:  # fall back so a recall is never blocked by one agent
            emit("agent_progress", {"source": src["id"], "step": f"Agent failed ({e}); falling back to direct read"})
    return run_direct(src, emit)
