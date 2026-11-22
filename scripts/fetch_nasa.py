#!/usr/bin/env python3
"""Find candidate images/videos in the NASA Image and Video Library for every shot that has
visual.search_query but no visual.file. Downloads the best original of the top N hits into
episodes/epXX/assets/candidates/<shot>/ and writes candidates.json (metadata + page URL).
Usage: fetch_nasa.py episodes/ep01/episode.json [--top 3] [--shot S003] [--no-download]
NOT TESTED against the live API from the build sandbox (no network there): run once and read the output.
Pick a candidate with pick.py, then verify credit/licence on the item page and set credit_verified=true."""
import argparse, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

API = "https://images-api.nasa.gov"
UA = {"User-Agent": "space-mysteries-pipeline/1.0"}
PREF_IMG = ("~orig.jpg", "~orig.png", "~large.jpg", "~medium.jpg")
PREF_VID = ("~orig.mp4", "~large.mp4", "~medium.mp4", "~mobile.mp4")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def search(q, media):
    url = f"{API}/search?" + urllib.parse.urlencode({"q": q, "media_type": media, "page_size": 12})
    return json.loads(get(url))["collection"]["items"]


def best_href(nasa_id, media):
    hrefs = json.loads(get(f"{API}/asset/{urllib.parse.quote(nasa_id)}"))["collection"]["items"]
    urls = [h["href"] for h in hrefs]
    for pref in (PREF_VID if media == "video" else PREF_IMG):
        for u in urls:
            if u.lower().endswith(pref):
                return u.replace("http://", "https://")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--shot")
    ap.add_argument("--no-download", action="store_true")
    a = ap.parse_args()
    base, _ = ep_dirs(a.episode)
    ep = load_json(a.episode)
    out_all = {}
    for s in ep["shots"]:
        v = s["visual"]
        if v.get("file") or not v.get("search_query"):
            continue
        if a.shot and s["id"] != a.shot:
            continue
        media = "video" if v["type"] == "video" else "image"
        print(f"{s['id']}: {v['search_query']!r} ({media})")
        try:
            items = search(v["search_query"], media)
        except Exception as e:
            print("   search failed:", e)
            continue
        cands = []
        for it in items:
            d = it["data"][0]
            if len(cands) >= a.top:
                break
            try:
                href = best_href(d["nasa_id"], media)
            except Exception:
                href = None
            if not href:
                continue
            cands.append({"nasa_id": d["nasa_id"], "title": d.get("title"), "center": d.get("center"),
                          "date": d.get("date_created"), "photographer": d.get("photographer"),
                          "description": (d.get("description") or "")[:300], "download": href,
                          "source_url": f"https://images.nasa.gov/details/{d['nasa_id']}"})
            time.sleep(0.3)
        dest = base / "assets" / "candidates" / s["id"]
        dest.mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(cands, 1):
            ext = Path(urllib.parse.urlparse(c["download"]).path).suffix
            c["file"] = f"assets/candidates/{s['id']}/{i}{ext}"
            print(f"   {i}. {c['title']} [{c['center']}] {c['source_url']}")
            if not a.no_download:
                try:
                    (base / c["file"]).write_bytes(get(c["download"]))
                except Exception as e:
                    print("      download failed:", e)
        out_all[s["id"]] = cands
        (dest / "candidates.json").write_text(json.dumps(cands, indent=2), encoding="utf-8")
    print(f"Done. Candidates for {len(out_all)} shots. Next: pick.py <episode.json> <shot> <n>")


if __name__ == "__main__":
    main()
