"""Ingest the BIDMC PPG and Respiration Dataset (PhysioNet): 53 real ICU patients, 8 minutes each.

Per patient: 1 Hz monitor numerics (heart rate, pulse, SpO2, respiration) and the 125 Hz
fingertip pleth waveform. KinCare uses them two ways:
- the "Recorded ICU patient" live stream replays a real patient instead of made-up numbers
- the phone-camera pulse algorithm (ppg.py) is scored against the monitor's own pulse

Raw files are cached under data/raw/bidmc/ so the database can be rebuilt offline. The 1 Hz numerics are
small and always fetched; the waveform comes from the compact WFDB .dat (600 KB, not the 4 MB CSV) and is
optional per record (--waves), because physionet.org can be slow. Re-running resumes where it stopped.
Source: https://physionet.org/content/bidmc/1.0.0/ (Pimentel et al., IEEE TBME 2016), ODC-By 1.0.

Usage: python -m ingest.bidmc [--records 53] [--waves 53]
"""
import argparse
import csv
import io
import json
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

import ppg
from db import connect

BASE = "https://physionet.org/files/bidmc/1.0.0/"
RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "bidmc"
SRC_HZ, KEEP_HZ = 125, 25  # the wave is replayed at 25 Hz: plenty for display, 5x smaller

SCHEMA = """
CREATE TABLE IF NOT EXISTS reference_records (
    id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    age INTEGER, gender TEXT, location TEXT,
    seconds INTEGER NOT NULL,
    numerics TEXT NOT NULL,
    pleth TEXT NOT NULL,
    hz INTEGER NOT NULL,
    summary TEXT NOT NULL,
    validation TEXT
);
"""


def fetch_bytes(name: str) -> bytes:
    path = RAW / name.split("/")[-1]
    part = path.with_suffix(path.suffix + ".part")
    for attempt in range(5):
        if path.exists():
            break
        try:
            # Resume a half-finished download rather than starting over.
            have = part.stat().st_size if part.exists() else 0
            with requests.get(BASE + name, timeout=(30, 120), stream=True, headers={"Range": f"bytes={have}-"} if have else {}) as r:
                if r.status_code != 416:  # 416 = the part file is already complete
                    r.raise_for_status()
                    with open(part, "ab" if r.status_code == 206 else "wb") as f:
                        for chunk in r.iter_content(16384):
                            f.write(chunk)
            part.replace(path)
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
    return path.read_bytes()


def fetch(name: str) -> str:
    return fetch_bytes(name).decode("utf-8")


def read_pleth(n: int) -> list[float]:
    """PLETH channel from the WFDB record (format 16: little-endian int16, channels interleaved)."""
    hea = fetch(f"bidmc{n:02d}.hea").splitlines()
    nsig = int(hea[0].split()[1])
    names = [line.split()[-1] for line in hea[1:1 + nsig]]
    gain = [line.split()[2] for line in hea[1:1 + nsig]]
    ch = names.index("PLETH,") if "PLETH," in names else names.index("PLETH")
    g = float(gain[ch].split("(")[0].split("/")[0]) or 1.0
    raw = fetch_bytes(f"bidmc{n:02d}.dat")
    vals = struct.unpack(f"<{len(raw) // 2}h", raw[: len(raw) // 2 * 2])
    return [v / g for v in vals[ch::nsig]]


def num(x: str):
    x = x.strip()
    if not x or x.lower() == "nan":
        return None
    v = float(x)
    return round(v) if v == v else None


def load_record(n: int, wave: bool = True) -> dict:
    rid = f"bidmc_{n:02d}"
    fix = dict(line.split(":", 1) for line in fetch(f"bidmc_csv/{rid}_Fix.txt").splitlines() if ":" in line)
    rows = list(csv.reader(io.StringIO(fetch(f"bidmc_csv/{rid}_Numerics.csv"))))
    head = [h.strip() for h in rows[0]]
    col = {h: head.index(h) for h in head}
    numerics = [{"hr": num(r[col["HR"]]), "pulse": num(r[col["PULSE"]]), "resp": num(r[col["RESP"]]), "spo2": num(r[col["SpO2"]])}
                for r in rows[1:] if len(r) == len(head)]
    pleth: list[float] = []
    if wave or (RAW / f"bidmc{n:02d}.dat").exists():
        try:
            full = read_pleth(n)
            step = SRC_HZ // KEEP_HZ
            pleth = [round(sum(full[i:i + step]) / step, 4) for i in range(0, len(full) - step + 1, step)]
        except requests.RequestException as e:
            print(f"{rid}: waveform not fetched ({type(e).__name__}); numerics only, re-run to resume")

    v = ppg.validate(pleth, KEEP_HZ, [x["pulse"] for x in numerics]) if pleth else {"windows": 0, "errors": []}
    pulses = [x["pulse"] for x in numerics if x["pulse"]]
    spo2 = [x["spo2"] for x in numerics if x["spo2"]]
    resp = [x["resp"] for x in numerics if x["resp"]]
    age = fix.get("Age", "").strip()
    summary = {
        "pulse_avg": round(sum(pulses) / len(pulses)) if pulses else None, "pulse_min": min(pulses, default=None), "pulse_max": max(pulses, default=None),
        "spo2_min": min(spo2, default=None), "spo2_avg": round(sum(spo2) / len(spo2), 1) if spo2 else None,
        "resp_avg": round(sum(resp) / len(resp)) if resp else None,
        "seconds_spo2_below_92": sum(1 for s in spo2 if s < 92), "seconds_pulse_above_100": sum(1 for p in pulses if p > 100),
    }
    return {
        "id": rid, "age": int(age) if age.isdigit() else None, "gender": fix.get("Gender", "").strip() or None,
        "location": fix.get("Location", "").strip() or None, "seconds": len(numerics),
        "numerics": numerics, "pleth": pleth, "summary": summary, "validation": v,
    }


def safe_load(n: int, wave: bool) -> dict | None:
    try:
        return load_record(n, wave)
    except requests.RequestException as e:
        print(f"bidmc_{n:02d}: skipped ({type(e).__name__}); re-run to fetch it")
        return None


def score(v: dict) -> dict:
    e = v["errors"]
    return {"windows": v["windows"], "estimated": len(e), "abs_error_sum": sum(e), "within5": sum(x <= 5 for x in e),
            "mae": round(sum(e) / len(e), 2) if e else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=int, default=53)
    ap.add_argument("--waves", type=int, default=53, help="fetch the pleth waveform for the first N records")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    conn = connect()
    conn.executescript(SCHEMA)
    with ThreadPoolExecutor(4) as pool:
        records = [r for r in pool.map(lambda n: safe_load(n, n <= a.waves), range(1, a.records + 1)) if r]
    errs = []
    for r in records:
        conn.execute(
            """INSERT OR REPLACE INTO reference_records (id, dataset, age, gender, location, seconds, numerics, pleth, hz, summary, validation)
               VALUES (?, 'bidmc', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r["id"], r["age"], r["gender"], r["location"], r["seconds"], json.dumps(r["numerics"]), json.dumps(r["pleth"]),
             KEEP_HZ, json.dumps(r["summary"]), json.dumps(score(r["validation"]))),
        )
        errs += r["validation"]["errors"]
    conn.commit()
    tried = sum(r["validation"]["windows"] for r in records)
    print(f"loaded {len(records)} BIDMC records ({sum(bool(r['pleth']) for r in records)} with waveform)")
    if errs:
        print(f"camera-pulse algorithm on real ICU pleth: MAE {sum(errs) / len(errs):.2f} bpm, {sum(e <= 5 for e in errs) / len(errs):.0%} within 5 bpm, "
              f"answered {len(errs)}/{tried} windows")


if __name__ == "__main__":
    main()
