#!/usr/bin/env python3
"""Assemble morning-lineup-tour.mp4: trim each segment, add silent track, concat."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "seg"
OUT.mkdir(exist_ok=True)

segs = json.loads((HERE / "segments.json").read_text())
files = []
for s in segs:
    name, dur = s["name"], s["dur"]
    dst = OUT / f"{name}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(s["trim"]), "-i", s["file"],
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-t", str(dur),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-r", "30", "-vf", "scale=780:1688,setsar=1",
         "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2", str(dst)],
        check=True, capture_output=True)
    files.append(dst)
    print(f"encoded {name}", flush=True)

lst = HERE / "list.txt"
lst.write_text("".join(f"file '{f}'\n" for f in files))
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", "-movflags", "+faststart",
                str(HERE / "morning-lineup-tour.mp4")],
               check=True, capture_output=True)
d = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "csv=p=0", str(HERE / "morning-lineup-tour.mp4")])
print("tour.mp4 done —", float(d), "s", flush=True)
