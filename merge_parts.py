#!/usr/bin/env python3
"""Merge ChatGPT output written in parts into one episode.json.
Folder: episodes/ep02/part_00_header.json (schema_version, episode, voice, music, beats)
        episodes/ep02/part_01.json ...    ({"shots": [...]} or a bare list)
Usage: merge_parts.py episodes/ep02 [--force]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

d = Path(sys.argv[1])
if (d / "episode.json").exists() and "--force" not in sys.argv:
    sys.exit("episode.json already exists. Merging again would ERASE picked assets and verified credits. "
             "Use patch_shots.py to change shots (or add --force to start over).")
hdr = load_json(d / "part_00_header.json")
shots = []
for p in sorted(d.glob("part_*.json")):
    if p.name.startswith("part_00"):
        continue
    data = load_json(p)
    items = data["shots"] if isinstance(data, dict) else data
    print(f"{p.name}: {len(items)} shots")
    shots += items
ep = dict(hdr)
ep["shots"] = shots
save_json(d / "episode.json", ep)
ids = [s.get("id") for s in shots]
dupes = sorted({i for i in ids if ids.count(i) > 1})
print(f"Wrote {d / 'episode.json'}: {len(shots)} shots" + (f"  DUPLICATE IDS: {dupes}" if dupes else ""))
