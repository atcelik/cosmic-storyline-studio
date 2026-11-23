#!/usr/bin/env python3
"""Render every scene spec of an episode on this machine (no CI): fit each spec to its shots' voice-over length
(needs build/timeline.json from `make tts`), then render assets/<id>.mp4 with scale2d.py or space3d.py.
Usage: cgi_local.py episodes/ep02 [--draft]"""
import json, subprocess, sys
from pathlib import Path
ep_dir = Path(sys.argv[1]); draft = "--draft" in sys.argv
ep = json.loads((ep_dir / "episode.json").read_text())
tl_path = ep_dir / "build" / "timeline.json"
T = {t["id"]: t for t in json.loads(tl_path.read_text())["shots"]} if tl_path.exists() else {}
here = Path(__file__).parent
for spec in sorted((ep_dir / "assets" / "space3d").glob("*.json")):
    sp = json.loads(spec.read_text())
    if sp.get("fit"):
        used = [s for s in ep["shots"] if (s["visual"].get("file") or "") == f"assets/{spec.stem}.mp4"]
        secs = sum(T[s["id"]]["dur"] - T[s["id"]]["trans_d"] for s in used if s["id"] in T) or sp.get("fallback", 10)
        sp["duration"] = round(secs + 1.0, 2); spec.write_text(json.dumps(sp, indent=1))
    out = ep_dir / "assets" / f"{spec.stem}.mp4"
    script = "scale2d.py" if sp.get("renderer") == "scale2d" else "space3d.py"
    print(f"{spec.stem}: {sp['duration']} s", flush=True)
    r = subprocess.run([sys.executable, str(here / script), str(spec), str(out)] + (["--draft"] if draft else []))
    if r.returncode: sys.exit(f"render failed: {spec.stem}")
