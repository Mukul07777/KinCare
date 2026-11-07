"""Build the KinCare demo video: narration (edge-tts) -> timeline -> frames (Edge, frame by frame) -> MP4.

    .venv\\Scripts\\python build.py            # everything
    .venv\\Scripts\\python build.py --audio    # narration + timeline only
    .venv\\Scripts\\python build.py --frames 30-40   # render only seconds 30-40 (preview)

Output: video/out/KinCare_demo.mp4 (1920x1080, 30 fps).
"""
import argparse
import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

from script import RATE, SCENES, VOICE

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
AUDIO = BUILD / "audio"
FRAMES = BUILD / "frames"
OUT = HERE / "out"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
LEAD, GAP, SCENE_PAD, TAIL = 0.5, 0.22, 0.6, 1.8   # seconds of silence around lines


def duration(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def tts_all() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    for si, (_, cues) in enumerate(SCENES):
        for ci, text in enumerate(cues):
            f = AUDIO / f"s{si}_c{ci}.mp3"
            meta = AUDIO / f"s{si}_c{ci}.txt"
            if f.exists() and meta.exists() and meta.read_text(encoding="utf-8") == text:
                continue   # unchanged line: keep the cached audio
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(f))
            meta.write_text(text, encoding="utf-8")


def timeline() -> dict:
    t, scenes = LEAD, []
    for si, (name, cues) in enumerate(SCENES):
        start, cue_list = t, []
        for ci, text in enumerate(cues):
            d = duration(AUDIO / f"s{si}_c{ci}.mp3")
            cue_list.append({"start": round(t, 3), "dur": round(d, 3), "text": text, "file": f"s{si}_c{ci}.mp3"})
            t += d + GAP
        t += SCENE_PAD
        scenes.append({"name": name, "start": round(start - (LEAD if si == 0 else SCENE_PAD / 2), 3),
                       "end": round(t - SCENE_PAD / 2, 3), "cues": cue_list})
    total = round(t + TAIL, 3)
    scenes[-1]["end"] = total
    return {"total": total, "scenes": scenes}


def mix(tl: dict) -> Path:
    """Place every line at its start time on one narration track."""
    inputs, filters = [], []
    cues = [c for s in tl["scenes"] for c in s["cues"]]
    for i, c in enumerate(cues):
        inputs += ["-i", str(AUDIO / c["file"])]
        ms = int(c["start"] * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms},aresample=48000[a{i}]")
    filters.append("".join(f"[a{i}]" for i in range(len(cues))) +
                   f"amix=inputs={len(cues)}:normalize=0,apad=whole_dur={tl['total']}[out]")
    out = BUILD / "narration.wav"
    subprocess.run([FF, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]",
                    "-t", str(tl["total"]), str(out)], check=True, capture_output=True)
    return out


def render(tl: dict, rng: tuple[float, float] | None) -> None:
    from playwright.sync_api import sync_playwright

    if rng is None and FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True, exist_ok=True)
    first = 0 if rng is None else int(rng[0] * FPS)
    last = int(tl["total"] * FPS) if rng is None else int(rng[1] * FPS)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((HERE / "index.html").as_uri())
        page.wait_for_function("window.READY === true", timeout=30000)
        for f in range(first, last):
            page.evaluate(f"window.seek({f / FPS})")
            page.screenshot(path=str(FRAMES / f"f{f:05d}.jpg"), type="jpeg", quality=92)
            if f % 300 == 0:
                print(f"  frame {f}/{last}", flush=True)
        browser.close()


def encode(tl: dict, narration: Path) -> Path:
    OUT.mkdir(exist_ok=True)
    out = OUT / "KinCare_demo.mp4"
    subprocess.run([FF, "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f%05d.jpg"), "-i", str(narration),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                   check=True, capture_output=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", action="store_true", help="narration and timeline only")
    ap.add_argument("--frames", help="render only this range of seconds, e.g. 30-40")
    a = ap.parse_args()

    asyncio.run(tts_all())
    tl = timeline()
    (BUILD / "timeline.js").write_text("window.TL = " + json.dumps(tl, ensure_ascii=False) + ";", encoding="utf-8")
    print(f"timeline: {tl['total']:.1f} s, {len(tl['scenes'])} scenes")
    if a.audio:
        return
    narration = mix(tl)
    if a.frames:
        lo, hi = (float(x) for x in a.frames.split("-"))
        render(tl, (lo, hi))
        print("preview frames in", FRAMES)
        return
    render(tl, None)
    print("video:", encode(tl, narration))


if __name__ == "__main__":
    main()
