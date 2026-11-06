"""SOS: one tap tells family where you are and what you take, so a doctor gets the facts fast.

KinCare does not call an ambulance itself; the page offers 112 / 108 as plain phone links.
"""
from urllib.parse import quote

import notify


def card(conn, device: str, member: str) -> dict:
    """What a doctor needs at a glance: current medicines and latest vitals."""
    meds = [dict(r) for r in conn.execute(
        """SELECT m.name, m.strength, m.morning, m.noon, m.night, m.batch, p.doctor FROM plan_meds m
           JOIN plans p ON p.id = m.plan_id WHERE p.device = ? AND p.member = ? ORDER BY p.created_at DESC""",
        (device, member))]
    v = conn.execute(
        "SELECT at, temp_c, bp_sys, bp_dia, pulse, spo2, level FROM vitals WHERE device = ? AND member = ? ORDER BY at DESC LIMIT 1",
        (device, member)).fetchone()
    return {"member": member, "medicines": meds, "last_vitals": dict(v) if v else None}


def message(c: dict, lat: float | None, lng: float | None) -> str:
    lines = [f"EMERGENCY (KinCare SOS): {c['member']} needs help now."]
    if lat is not None and lng is not None:
        lines.append(f"Location: https://maps.google.com/?q={lat:.5f},{lng:.5f}")
    v = c["last_vitals"]
    if v:
        parts = [v["temp_c"] and f"temp {v['temp_c']}C", v["bp_sys"] and f"BP {v['bp_sys']}/{v['bp_dia'] or '?'}",
                 v["pulse"] and f"pulse {v['pulse']}", v["spo2"] and f"SpO2 {v['spo2']}%"]
        lines.append("Last vitals: " + ", ".join(p for p in parts if p) + f" ({v['at'][:16].replace('T', ' ')} UTC)")
    if c["medicines"]:
        lines.append("Medicines: " + "; ".join(f"{m['name']} {m['strength'] or ''}".strip() for m in c["medicines"][:8]))
    lines.append("Call 112 or 108 if they cannot. Show this message to the doctor.")
    return "\n".join(lines)


def deliver(contacts: list[dict], text: str) -> list[dict]:
    out = []
    for p in contacts:
        link = f"https://wa.me/{p['phone'].lstrip('+')}?text={quote(text)}"
        status = "link"
        if notify.whatsapp_ready():
            try:
                status, _ = notify.send_whatsapp(p["phone"], text)
            except Exception:  # fall back to a tap-to-send link
                status = "failed"
        out.append({"name": p["name"], "phone": p["phone"], "status": status, "link": link})
    return out
