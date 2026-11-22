#!/usr/bin/env python3
"""Choose a downloaded candidate: copies it to assets/ and fills file/source_url/credit (credit_verified stays false).
Usage: pick.py ep.json S003 2     |     pick.py ep.json --auto   (candidate 1 for every shot without a file)"""
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

ep_path = sys.argv[1]
base, _ = ep_dirs(ep_path)
ep = load_json(ep_path)
jobs = [(s["id"], 1) for s in ep["shots"] if not s["visual"].get("file")] if (len(sys.argv) > 2 and sys.argv[2] == "--auto") \
    else [(sys.argv[2], int(sys.argv[3]))]
done = 0
for sid, n in jobs:
    cf = base / "assets" / "candidates" / sid / "candidates.json"
    if not cf.exists():
        print(f"{sid}: no candidates (run fetch first, or the search found nothing)"); continue
    cands = load_json(cf)
    if n > len(cands):
        print(f"{sid}: only {len(cands)} candidates"); continue
    c = cands[n - 1]; src = base / c["file"]
    if not src.exists():
        print(f"{sid}: candidate file missing ({c['file']})"); continue
    dst = base / "assets" / f"{sid}{src.suffix}"
    shutil.copy(src, dst)
    for s in ep["shots"]:
        if s["id"] == sid:
            v = s["visual"]
            v["file"] = f"assets/{dst.name}"; v["source_url"] = c["source_url"]
            v["credit"] = f"NASA ({c.get('center') or 'see source page'}) - {c.get('title')}"
            v["credit_verified"] = False
    done += 1; print(f"{sid}: {c['title']}  <- {c['source_url']}")
save_json(ep_path, ep)
print(f"{done} shots updated. Next: make sheets, review, then verify credits on each source page.")
