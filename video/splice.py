"""Swap the screenshot "REAL RUN" scene for a real screen recording of the Telegram chat.

    .venv\\Scripts\\python splice.py path\\to\\real_chat.mp4 [--max 35]

The real clip keeps its own sound (talk over it while recording, or leave it silent). It is scaled to 1920x1080,
letterboxed, and cut to --max seconds. Keep it short (10-15 s) so the final video stays under 3 minutes.
Output: video/out/KinCare_demo_final.mp4
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
FF = imageio_ffmpeg.get_ffmpeg_exe()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--max", type=float, default=15.0, help="longest the real clip may run, in seconds")
    a = ap.parse_args()

    tl = json.loads((HERE / "build" / "timeline.js").read_text(encoding="utf-8")[len("window.TL = "):-1])
    proof = next(s for s in tl["scenes"] if s["name"] == "proof")
    cut, resume = proof["start"], proof["end"]   # the screenshot scene is replaced by the real clip
    total = tl["total"]
    src = HERE / "out" / "KinCare_demo.mp4"
    info = subprocess.run([FF, "-i", a.clip], capture_output=True, text=True).stderr
    has_audio = "Audio:" in info
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    length = min(a.max, int(h) * 3600 + int(m) * 60 + float(sec))
    extra = [] if has_audio else ["-f", "lavfi", "-t", str(length), "-i", "anullsrc=r=48000:cl=stereo"]
    clip_a = "1:a" if has_audio else "2:a"
    out = HERE / "out" / "KinCare_demo_final.mp4"
    fit = ("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0a0e14,"
           "fps=30,format=yuv420p,setsar=1")
    graph = (f"[0:v]trim=0:{cut},setpts=PTS-STARTPTS[v0];[0:a]atrim=0:{cut},asetpts=PTS-STARTPTS[a0];"
             f"[1:v]trim=0:{length},setpts=PTS-STARTPTS,{fit}[v1];"
             f"[{clip_a}]atrim=0:{length},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[a1];"
             f"[0:v]trim={resume}:{total},setpts=PTS-STARTPTS[v2];[0:a]atrim={resume}:{total},asetpts=PTS-STARTPTS[a2];"
             "[a0]aformat=channel_layouts=stereo[a0s];[a2]aformat=channel_layouts=stereo[a2s];"
             "[v0][a0s][v1][a1][v2][a2s]concat=n=3:v=1:a=1[v][a]")
    subprocess.run([FF, "-y", "-i", str(src), "-i", a.clip, *extra, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out)], check=True)
    print("video:", out)


if __name__ == "__main__":
    main()
