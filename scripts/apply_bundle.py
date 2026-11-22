#!/usr/bin/env python3
"""Import an asset bundle (the zip(s) made by get_assets.py) into an episode and wire files into episode.json.
Usage: apply_bundle.py episodes/ep01 ep01_assets_part01.zip [part02.zip ...] [--pick S014=2 ...]
       apply_bundle.py episodes/ep01 episodes/ep01/bundle      (a bundle folder works too)
- Media go to episodes/ep01/assets/, report.json is merged.
- Manifest items fill visual.file / credit / source_url for every shot listed in their "shots".
- Search candidates: candidate 1 is used unless you choose another with --pick S014=2.
- credit_verified is set true only for manifest items marked "credit_checked": true (checked by a human or Claude
  on the source page); search results always stay false."""
import argparse, json, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

ap = argparse.ArgumentParser()
ap.add_argument("episode_dir")
ap.add_argument("zips", nargs="+")
ap.add_argument("--pick", nargs="*", default=[])
a = ap.parse_args()
ep_dir = Path(a.episode_dir)
assets = ep_dir / "assets"; assets.mkdir(parents=True, exist_ok=True)
items = {}
def handle(name, data):
    if name == "report.json":
        for it in json.loads(data)["items"]:
            if it.get("status") == "ok":
                items[it["id"]] = it
        return
    meta = name.startswith(("contact_sheet", "summary"))
    target = (assets / "bundle_meta" / name) if meta else assets / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


for z in a.zips:
    zp = Path(z)
    if zp.is_dir():  # a bundle/ folder (GitHub Actions run, no zip needed)
        for f in sorted(zp.iterdir()):
            if f.is_file():
                handle(f.name, f.read_bytes())
        continue
    with zipfile.ZipFile(zp) as zf:
        for n in zf.namelist():
            name = Path(n).name
            if name and not n.endswith("/"):
                handle(name, zf.read(n))
save_json(assets / "bundle_report.json", {"items": list(items.values())})
picks = dict(p.split("=") for p in a.pick)
ep_p = ep_dir / "episode.json"
if not ep_p.exists():
    print(f"{len(items)} assets unpacked to {assets}. No episode.json, nothing wired."); sys.exit(0)
ep = load_json(ep_p)
by_shot = {}
for it in items.values():
    for sid in it.get("shots", []):
        by_shot.setdefault(sid, []).append(it)
wired, missing = 0, []
for s in ep["shots"]:
    cands = by_shot.get(s["id"])
    if not cands:
        if not s["visual"].get("file") and s["visual"].get("source_class") != "OUR_CGI":
            missing.append(s["id"])
        continue
    manual = [c for c in cands if not c.get("from_search")]
    if manual:
        it = manual[0]
    else:
        want = int(picks.get(s["id"], 1))
        it = next((c for c in cands if c.get("candidate") == want), cands[0])
    if not (assets / it["bundle_file"]).exists():
        missing.append(s["id"]); continue
    v = s["visual"]
    v["file"] = f"assets/{it['bundle_file']}"
    v["type"] = "video" if it["kind"] == "video" else "still"
    v["source_url"] = it.get("source_url") or v.get("source_url")
    if it.get("credit"):
        v["credit"] = it["credit"]
    if it.get("source_class"):
        v["source_class"] = it["source_class"]
    v["credit_verified"] = bool(it.get("credit_checked")) and not it.get("from_search")
    for k in ("trim_start", "speed"):
        if k in it:
            v[k] = it[k]
    wired += 1
save_json(ep_p, ep)
print(f"{len(items)} assets unpacked, {wired} shots wired.")
if missing:
    print(f"{len(missing)} shots still without a file: {', '.join(missing[:30])}{' ...' if len(missing) > 30 else ''}")
print("Next: make validate EP=" + ep_dir.name)
