#!/usr/bin/env python3
"""Which shot is on screen at a time? Usage: where.py episodes/ep02 2:15   (or seconds)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

d = Path(sys.argv[1]); t = sys.argv[2]
sec = int(t.split(":")[0]) * 60 + float(t.split(":")[1]) if ":" in t else float(t)
ep = load_json(d / "episode.json"); tl = load_json(d / "build" / "timeline.json")
for s, x in zip(ep["shots"], tl["shots"]):
    if x["start"] <= sec < x["start"] + x["dur"]:
        print(f"{s['id']} (beat {s['beat']})  {x['start']:.1f}-{x['start']+x['dur']:.1f}s  len {x['dur']:.1f}s")
        print(f"  voice-over: {s.get('voiceover','')}")
        print(f"  visual: {s['visual'].get('file') or s['visual'].get('search_query')}  [{s['visual']['source_class']}]")
        print(f"  camera: {(s.get('camera') or {}).get('move','push_in')}  transition out: {(s.get('transition_out') or {}).get('type','cut')}")
        break
else:
    print("time is outside the video")
