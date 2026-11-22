#!/usr/bin/env python3
"""Apply a patch: list of FULL shot objects. Existing id -> replaced. New id needs "insert_after": "S045".
Usage: patch_shots.py ep.json patch.json   (writes ep.json.bak)"""
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

ep_path, patch_path = sys.argv[1], sys.argv[2]
shutil.copy(ep_path, ep_path + ".bak")
ep = load_json(ep_path); patch = load_json(patch_path)
patch = patch["shots"] if isinstance(patch, dict) else patch
shots = ep["shots"]
for p in patch:
    after = p.pop("insert_after", None)
    ids = [s["id"] for s in shots]
    if p["id"] in ids:
        shots[ids.index(p["id"])] = p; print("replaced", p["id"])
    elif after in ids:
        shots.insert(ids.index(after) + 1, p); print("inserted", p["id"], "after", after)
    else:
        sys.exit(f"{p['id']}: new shot needs a valid insert_after")
save_json(ep_path, ep)
print(f"{len(shots)} shots now. Re-run: make check EP=...")
