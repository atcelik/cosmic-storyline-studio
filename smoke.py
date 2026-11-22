#!/usr/bin/env python3
"""End-to-end smoke test with synthetic assets and the dummy voice. Proves the pipeline runs; says nothing about
Kokoro quality or real-asset look. Usage: python3 tests/smoke.py [--full-res]"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, cv2
ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "episodes" / "_smoke"
(EP / "assets").mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(1)


def make_img(name, w, h, hue):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32)
    img[..., 0] = 40 + 120 * (x / w) * (hue % 2)
    img[..., 1] = 30 + 100 * (y / h)
    img[..., 2] = 60 + 100 * ((x + y) / (w + h)) * ((hue + 1) % 2 + 0.5)
    for _ in range(400):
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))), int(rng.integers(1, 5)), (255, 255, 255), -1)
    cv2.circle(img, (w // 2, h // 2), h // 5, (80, 180, 255), 6)
    cv2.imwrite(str(EP / "assets" / name), np.clip(img, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])


for i in range(5):
    make_img(f"img{i}.jpg", 3840, 2160, i)
make_img("wide.jpg", 6000, 2160, 3)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=4",
                "-pix_fmt", "yuv420p", str(EP / "assets" / "clip.mp4")], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                "sine=frequency=110:duration=30,volume=0.3", "-ac", "2", str(EP / "assets" / "music.wav")], check=True)


def shot(i, beat, img, vo, move, trans, cls="REAL_PHOTO", typ="still", dur=0, text=None):
    s = {"id": f"S{i:03}", "beat": beat, "voiceover": vo,
         "visual": {"type": typ, "file": f"assets/{img}", "source_class": cls, "credit": "Test/Synthetic",
                    "source_url": "https://example.org/test", "credit_verified": True},
         "camera": {"move": move, "strength": 0.08}, "transition_out": trans}
    if dur: s["min_duration"] = dur
    if text: s["on_screen_text"] = text
    return s


ep = {"schema_version": 2,
      "episode": {"id": "_smoke", "title": "Smoke test", "language": "en", "central_question": "Does the pipeline run?"},
      "voice": {"engine": "dummy"},
      "music": {"file": "assets/music.wav", "credit": "synthetic sine", "license": "CC0", "gain_db": -22},
      "beats": [{"id": "B1", "name": "Hook", "chapter": "Intro"},
                {"id": "B2", "name": "Twist", "because": "But the data said otherwise.", "chapter": "The twist"}],
      "shots": [
          shot(1, "B1", "img0.jpg", "What if the sky above you was lying?", "push_in", {"type": "crossfade", "duration": 0.5}, text="THE SKY"),
          shot(2, "B1", "img1.jpg", "Four hundred years of data say it was.", "pull_out", {"type": "cut"}),
          shot(3, "B1", "clip.mp4", "Look closer.", "push_in", {"type": "zoom_through", "duration": 0.8}, "REAL_VIDEO", "video", dur=3),
          shot(4, "B2", "wide.jpg", "But the pattern did not hold at the edges of the map.", "pan_right", {"type": "push_left", "duration": 0.7}, "SCIENTIFIC_CGI"),
          shot(5, "B2", "img2.jpg", "Therefore something else was pulling.", "push_in", {"type": "dip_black", "duration": 0.9}, "PROCESSED_DATA"),
          shot(6, "B2", "img3.jpg", "And that something is still out there.", "pull_out", {"type": "cut"}, text="STILL OUT THERE"),
      ]}
(EP / "episode.json").write_text(json.dumps(ep, indent=2))
draft = [] if "--full-res" in sys.argv else ["--draft"]


def run(*a):
    print("\n$", " ".join(map(str, a)))
    subprocess.run([sys.executable, *map(str, a)], check=True, cwd=ROOT)


E_ = "episodes/_smoke/episode.json"
run("scripts/validate.py", E_, "--assets")
run("scripts/tts.py", E_, "--engine", "dummy")
run("scripts/render.py", E_, *draft)
run("scripts/audio.py", E_, *draft)
run("scripts/meta.py", E_)
out = EP / "build" / ("final_draft.mp4" if draft else "final.mp4")
p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                               "-of", "json", str(out)], capture_output=True, text=True, check=True).stdout)
tl = json.loads((EP / "build" / "timeline.json").read_text())
kinds = [s["codec_type"] for s in p["streams"]]
dur = float(p["format"]["duration"])
ok = "video" in kinds and "audio" in kinds and abs(dur - tl["total"]) < 0.3
print("\nstreams:", p["streams"], "\nduration", dur, "expected", tl["total"])
print("SMOKE TEST:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
