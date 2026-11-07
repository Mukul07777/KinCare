"""Capture KinCare web app pages for the video: python capture_site.py (web app on :3000, API on :8000).

Scrolls each page top to bottom first so scroll-reveal sections render, hides the Next.js dev badge,
then saves a viewport shot (and a full-page shot of the landing page for the scrolling browser).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT = Path(__file__).resolve().parent / "shots"; OUT.mkdir(exist_ok=True)
PAGES = {"home": "/", "result": "/result?batch=AT25-0938A&brand=Namik-MR", "scan": "/scan", "network": "/network",
         "family": "/family", "dadi": "/dadi", "alerts": "/alerts", "blast": "/blast"}
HIDE = "nextjs-portal, [data-nextjs-toast], #__next-build-watcher{display:none!important}"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    for name, path in PAGES.items():
        try:
            pg.goto("http://localhost:3000" + path, wait_until="load", timeout=90000)
        except Exception as e:
            print(name, "load warning:", str(e)[:60])
        pg.wait_for_timeout(3000)
        pg.add_style_tag(content=HIDE)
        h = pg.evaluate("document.body.scrollHeight")
        for y in range(0, h, 300):                     # trigger scroll-reveal sections
            pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(120)
        pg.wait_for_timeout(800)
        if name == "home":
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(600)
            pg.screenshot(path=str(OUT / "home_full.png"), full_page=True)
        pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        print(name, "ok")
    b.close()
