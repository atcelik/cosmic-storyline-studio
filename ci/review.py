#!/usr/bin/env python3
"""Build the review pack (always runs, also after a failure). Everything goes to review_out/, which the workflow
pushes to the 'review' branch so Claude can fetch it with git. Kept small: no originals, preview split <= ~40 MB."""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review_out"
OUT.mkdir(exist_ok=True)
req = json.loads((ROOT / "render_request.json").read_text())
ep = req["episode"]
ep_dir = ROOT / "episodes" / ep


def sh(cmd, **kw):
    return subprocess.run(list(map(str, cmd)), capture_output=True, text=True, **kw)


# asset bundle info
b = ep_dir / "bundle"
if b.exists():
    for f in list(b.glob("contact_sheet_*.jpg")) + [b / "report.json", b / "summary.txt"]:
        if f.exists():
            shutil.copy(f, OUT / f"assets_{f.name}")

# voice samples -> small m4a
vt = ROOT / "voice_test"
if vt.exists():
    (OUT / "voice").mkdir(exist_ok=True)
    for w in sorted(vt.glob("*.wav")):
        sh(["ffmpeg", "-v", "error", "-y", "-i", w, "-c:a", "aac", "-b:a", "96k", OUT / "voice" / f"{w.stem}.m4a"])

# episode files
for f in (ep_dir / "episode.json", ep_dir / "build" / "timeline.json", ep_dir / "build" / "captions.srt",
          ep_dir / "build" / "description.txt"):
    if f.exists():
        shutil.copy(f, OUT / f.name)

# final video checks
st = OUT / "status.json"
status = json.loads(st.read_text()) if st.exists() else {}
final = ROOT / status["final_video"] if status.get("final_video") else None
if final and final.exists():
    info = {}
    p = sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate:format=duration,size",
            "-of", "json", final])
    info["ffprobe"] = json.loads(p.stdout or "{}")
    p = sh(["ffmpeg", "-hide_banner", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = [l.strip() for l in p.stderr.splitlines()[-14:] if l.strip()]
    info["loudness_summary"] = tail
    dur = float(info["ffprobe"].get("format", {}).get("duration", 0) or 0)
    (OUT / "video_check.json").write_text(json.dumps(info, indent=2))
    # 16 evenly spaced frames, plus a dense sheet of the first 30 s
    if dur > 0:
        step = max(dur / 16, 0.5)
        sh(["ffmpeg", "-v", "error", "-y", "-i", final, "-vf", f"fps=1/{step:.3f},scale=480:-2,tile=4x4", "-frames:v", "1",
            OUT / "frames_overview.jpg"])
        sh(["ffmpeg", "-v", "error", "-y", "-t", "30", "-i", final, "-vf", "fps=1/2,scale=480:-2,tile=5x3", "-frames:v", "1",
            OUT / "frames_first30s.jpg"])
        # preview, split into ~5 minute parts (~35 MB each at these settings)
        (OUT / "preview").mkdir(exist_ok=True)
        sh(["ffmpeg", "-v", "error", "-y", "-i", final, "-vf", "scale=640:-2", "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "800k", "-maxrate", "1000k", "-bufsize", "2000k", "-c:a", "aac", "-b:a", "64k", "-f", "segment",
            "-segment_time", "300", "-reset_timestamps", "1", OUT / "preview" / "preview_%02d.mp4"])

big = [f for f in OUT.rglob("*") if f.is_file() and f.stat().st_size > 90e6]
for f in big:
    f.unlink()
    print("removed oversized", f)
print("review pack:", sorted(str(f.relative_to(OUT)) for f in OUT.rglob("*") if f.is_file()))
