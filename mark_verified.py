#!/usr/bin/env python3
"""Mark credits (and optionally claims) verified AFTER you opened each source page and checked credit + licence.
Without --yes it only lists. Usage: mark_verified.py ep.json [--shots S001,S002 | --all] [--claims] [--yes]"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

ap = argparse.ArgumentParser()
ap.add_argument("episode"); ap.add_argument("--shots"); ap.add_argument("--all", action="store_true")
ap.add_argument("--claims", action="store_true"); ap.add_argument("--yes", action="store_true")
a = ap.parse_args()
ep = load_json(a.episode)
want = set((a.shots or "").split(",")) if a.shots else set()
if not (want or a.all):
    sys.exit("give --shots S001,S002 or --all")
n = 0
for s in ep["shots"]:
    if not a.all and s["id"] not in want:
        continue
    v = s["visual"]
    if v.get("source_class") != "OUR_CGI" and v.get("file") and not v.get("credit_verified"):
        print(f"{s['id']}  credit: {v.get('credit')}\n      page:   {v.get('source_url')}")
        if a.yes: v["credit_verified"] = True
        n += 1
    if a.claims:
        for c in s.get("claims", []):
            if not c.get("verified"):
                print(f"{s['id']}  claim:  {c.get('text','')[:80]}\n      source: {c.get('source_url')}")
                if a.yes: c["verified"] = True
                n += 1
if a.yes:
    save_json(a.episode, ep); print(f"Marked {n} items verified.")
else:
    print(f"\n{n} items listed. Check each page, then re-run with --yes.")
