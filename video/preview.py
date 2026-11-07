"""Render stills at given seconds: python preview.py 12 40 95 ..."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
out = HERE / "build" / "preview"; out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge"); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    errs = []; pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto((HERE / "index.html").as_uri()); pg.wait_for_function("window.READY === true", timeout=30000)
    for t in sys.argv[1:]:
        pg.evaluate(f"window.seek({float(t)})"); pg.screenshot(path=str(out / f"t{float(t):06.1f}.png"))
    print("errors:", errs or "none"); b.close()
