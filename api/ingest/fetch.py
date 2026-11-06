"""Discover and download CDSCO alert PDFs.

Usage: python -m ingest.fetch [--limit N]
Writes PDFs to data/raw_pdfs/ and an index to data/raw_pdfs/index.json.
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://cdsco.gov.in"
PAGES = [
    f"{BASE}/opencms/opencms/en/Notifications/nsq-drugs/",
    f"{BASE}/opencms/opencms/en/Notifications/Alerts/",
]
OUT = Path(__file__).resolve().parents[2] / "data" / "raw_pdfs"
HEADERS = {"User-Agent": "Mozilla/5.0 (KinCare research; Flip the Switch 2026)"}

MONTHS = "january february march april may june july august september october november december".split()


def classify(title: str) -> str | None:
    t = title.lower()
    if "spurious" in t:
        return "spurious"
    if "nsq" in t or "standard quality" in t or "drug alert" in t:
        return "nsq"
    return None


def alert_month(title: str, published: str) -> str:
    """Month the alert covers, from the title (e.g. 'June 2025'), else the publish date."""
    m = re.search(r"(" + "|".join(MONTHS) + r")\w*[\s\-,]*(20\d\d)", title.lower())
    if m:
        return f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}"
    return datetime.strptime(published, "%Y-%b-%d").strftime("%Y-%m")


def discover() -> list[dict]:
    seen, docs = set(), []
    for page in PAGES:
        soup = BeautifulSoup(requests.get(page, headers=HEADERS, timeout=60).text, "html.parser")
        for tr in soup.select("tr"):
            tds = tr.find_all("td")
            a = tr.find("a", href=True)
            if len(tds) < 4 or not a or "download_file" not in a["href"]:
                continue
            title = " ".join(tds[1].get_text(" ").split())
            published = tds[2].get_text(strip=True)
            cat = classify(title)
            if not cat or not re.fullmatch(r"\d{4}-\w{3}-\d{2}", published):
                continue
            url = BASE + a["href"] if a["href"].startswith("/") else a["href"]
            if url in seen:
                continue
            seen.add(url)
            docs.append({
                "title": title,
                "published": published,
                "category_hint": cat,
                "alert_month": alert_month(title, published),
                "url": url,
                "source_page": page,
                "issuer": "state" if title.lower().startswith("state") else "cdsco",
            })
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=24)
    main_for(ap.parse_args().limit)


def main_for(limit: int):
    OUT.mkdir(parents=True, exist_ok=True)
    pub = lambda d: datetime.strptime(d["published"], "%Y-%b-%d")
    docs = sorted(discover(), key=pub, reverse=True)[:limit]
    for d in docs:
        num = re.search(r"num_id=([^&]+)", d["url"]).group(1).rstrip("=")
        path = OUT / f"{d['alert_month']}_{d['issuer']}_{d['category_hint']}_{num}.pdf"
        d["file"] = path.name
        if not path.exists():
            r = requests.get(d["url"], headers=HEADERS, timeout=120)
            # The download link returns an iframe wrapper around the real PDF.
            frame = re.search(r"<iframe src='([^']+)'", r.text) if not r.content.startswith(b"%PDF") else None
            if frame:
                d["pdf_url"] = BASE + requests.utils.requote_uri(frame.group(1))
                r = requests.get(d["pdf_url"], headers=HEADERS, timeout=120)
            if not r.content.startswith(b"%PDF"):
                print("  skip (not a PDF):", d["title"].encode("ascii", "replace").decode())
                d["file"] = None
                continue
            path.write_bytes(r.content)
        print(f"  {d['alert_month']}  {d['title'][:70]}".encode("ascii", "replace").decode())
    # Keep previously indexed documents so re-runs only add.
    index = OUT / "index.json"
    old = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    merged = {d["url"]: d for d in old} | {d["url"]: d for d in docs if d["file"]}
    index.write_text(json.dumps(list(merged.values()), indent=2), encoding="utf-8")
    print(f"{sum(1 for d in docs if d['file'])} PDFs in {OUT}")


if __name__ == "__main__":
    main()
