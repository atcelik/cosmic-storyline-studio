#!/usr/bin/env python3
"""ONE COMMAND: download every asset an episode needs, check it, and pack it into zip file(s) you can upload to Claude.

Inputs (either or both):
  episodes/epNN/asset_manifest.json   list of direct download URLs (Claude writes this for you)
  --search                            also search the NASA Image and Video Library for every shot in
                                      episode.json that has visual.search_query but no file/manifest entry

Usage:
  python3 scripts/get_assets.py episodes/ep01                 # manifest only
  python3 scripts/get_assets.py episodes/ep01 --search        # manifest + NASA search for the rest
  options: --top 2 (candidates per searched shot)  --max-width 3840  --part-mb 400  --keep-tiff

Output (in episodes/epNN/):
  assets/originals/        full-size downloads (stay on the server)
  bundle/                  transfer copies: images <= --max-width px wide (JPEG q93), videos <= 1080p
  bundle/report.json       every item: status, pixel size, fps, duration, bytes, credit, source page
  bundle/contact_sheet_NN.jpg
  epNN_assets_part01.zip ...   <- upload these to Claude

Re-running is safe: finished downloads are skipped; failed ones are retried.
Manifest format: see docs/ASSET_MANIFEST.md"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) space-docs-pipeline/1.0"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
NASA_API = os.environ.get("NASA_API_BASE", "https://images-api.nasa.gov")


def log(*a):
    print(*a, flush=True)


def http_get(url, dest=None, timeout=90, max_mb=2048):
    """Download url to dest (streaming, resumable via .part). Returns bytes if dest is None."""
    req = urllib.request.Request(url, headers=UA)
    if dest is None:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    if have:
        req.add_header("Range", f"bytes={have}-")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype:
            raise RuntimeError(f"got a web page (text/html), not a file: use the direct file URL")
        mode = "ab" if (have and r.status == 206) else "wb"
        if mode == "wb":
            have = 0
        total = r.headers.get("Content-Length")
        total = int(total) + have if total else None
        if total and total > max_mb * 1024 * 1024:
            raise RuntimeError(f"file is {total / 1e6:.0f} MB, over --max-file-mb {max_mb}")
        with open(part, mode) as f:
            got, t0 = have, time.time()
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if got > max_mb * 1024 * 1024:
                    raise RuntimeError(f"file exceeds {max_mb} MB")
                if time.time() - t0 > 5:
                    log(f"      {got / 1e6:.0f} MB" + (f" / {total / 1e6:.0f} MB" if total else ""))
                    t0 = time.time()
    if total and part.stat().st_size != total:
        raise RuntimeError(f"incomplete download ({part.stat().st_size} of {total} bytes)")
    part.rename(dest)


def download(url, dest, tries=4):
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"
    err = None
    for k in range(tries):
        try:
            http_get(url, dest)
            return "downloaded"
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404, 410):
                break
        except Exception as e:  # network hiccup, timeout, incomplete
            err = str(e)
            if "web page" in err or "over --max-file-mb" in err:
                break
        time.sleep(2 * (k + 1))
    raise RuntimeError(err)


def ext_of(url, kind):
    e = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if e in IMG_EXT | VID_EXT:
        return e
    return ".mp4" if kind == "video" else ".jpg"


# ---------- NASA search (for shots without a manifest entry) ----------
def nasa_search(q, media, top):
    url = f"{NASA_API}/search?" + urllib.parse.urlencode({"q": q, "media_type": media, "page_size": 30})
    items = json.loads(http_get(url))["collection"]["items"]
    log(f"   {len(items)} raw results")
    out = []
    pref = ("~large.mp4", "~orig.mp4", "~orig.mov", "~medium.mp4", "~mobile.mp4") if media == "video" else ("~orig.jpg", "~orig.png", "~orig.tif", "~large.jpg")
    for it in items:
        if len(out) >= top:
            break
        d = it["data"][0]
        try:
            hrefs = [h["href"] for h in json.loads(http_get(f"{NASA_API}/asset/{urllib.parse.quote(d['nasa_id'])}"))["collection"]["items"]]
        except Exception:
            continue
        href = next((u for p in pref for u in hrefs if u.lower().endswith(p)), None)
        if not href:
            continue
        host = urllib.parse.urlparse(href).hostname or ""
        if href.startswith("http://") and host.endswith("nasa.gov"):
            href = "https://" + href[len("http://"):]
        href = urllib.parse.quote(href, safe=":/~%?=&#+,")      # NASA ids may contain spaces
        out.append({"url": href, "title": d.get("title"),
                    "credit": f"NASA ({d.get('center') or 'see page'})" + (f" / {d['photographer']}" if d.get("photographer") else ""),
                    "source_url": f"https://images.nasa.gov/details/{urllib.parse.quote(d['nasa_id'])}",
                    "date": d.get("date_created", "")[:10], "description": (d.get("description") or "")[:300]})
        time.sleep(0.3)
    return out


# ---------- checks and transfer copies ----------
def probe_video(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("not a readable video")
    j = json.loads(r.stdout)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), round(int(num) / max(1, int(den)), 3), round(float(j["format"]["duration"]), 2)


def make_transfer_copy(src, dst_dir, item, a):
    kind = item["kind"]
    if kind == "image":
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(src)
        w, h = im.size
        item.update(orig_width=w, orig_height=h)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if w > a.max_width:
            im = im.resize((a.max_width, round(h * a.max_width / w)), Image.LANCZOS)
        out = dst_dir / f"{item['id']}.jpg"
        if src.suffix.lower() in (".jpg", ".jpeg") and w <= a.max_width:
            shutil.copy(src, out)
        else:
            im.convert("RGB").save(out, quality=93, subsampling=0)
        item.update(width=im.size[0], height=im.size[1])
    else:
        w, h, fps, dur = probe_video(src)
        item.update(orig_width=w, orig_height=h, fps=fps, duration=dur)
        out = dst_dir / f"{item['id']}.mp4"
        if h > 1080 or src.suffix.lower() != ".mp4" or src.stat().st_size > a.video_mb * 1e6:
            vf = "scale=-2:1080:flags=lanczos" if h > 1080 else "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium",
                            "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
        else:
            shutil.copy(src, out)
        w, h, fps, dur = probe_video(out)
        item.update(width=w, height=h)
    item["bundle_file"] = out.name
    item["bytes"] = out.stat().st_size
    # quality flags for 1920x1080 full-frame use
    flags = []
    if kind == "image" and (item["orig_width"] < 1920 or item["orig_height"] < 1080):
        flags.append("SMALL: smaller than 1920x1080, will look soft full-frame")
    elif kind == "image" and item["orig_width"] < 2560:
        flags.append("OK_NO_ZOOM: fine full-frame, little room to zoom")
    if kind == "video":
        if item["orig_height"] < 1080:
            flags.append(f"LOW_RES_VIDEO: {item['orig_height']}p")
        if item["fps"] and abs(item["fps"] - 30) > 0.5 and abs(item["fps"] - 60) > 0.5 and abs(item["fps"] - 29.97) > 0.1:
            flags.append(f"FPS_{item['fps']}: may judder at 30 fps")
    ar = item["orig_width"] / item["orig_height"]
    if ar < 1.2:
        flags.append(f"ASPECT_{ar:.2f}: tall/square, full-frame crop loses {100 * (1 - ar / (16 / 9)):.0f}% of the height")
    item["flags"] = flags
    return out


def contact_sheets(items, bundle, cfg_font):
    from PIL import Image, ImageDraw, ImageFont
    Image.MAX_IMAGE_PIXELS = None
    TW, TH, CAP, COLS, ROWS = 400, 225, 58, 4, 5
    try:
        f = ImageFont.truetype(cfg_font, 14)
    except Exception:
        f = ImageFont.load_default()
    ok = [i for i in items if i.get("status") == "ok"]
    paths = []
    for k in range(0, len(ok), COLS * ROWS):
        chunk = ok[k:k + COLS * ROWS]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * TW, rows * (TH + CAP)), (18, 18, 22))
        d = ImageDraw.Draw(sheet)
        for j, it in enumerate(chunk):
            x, y = (j % COLS) * TW, (j // COLS) * (TH + CAP)
            p = bundle / it["bundle_file"]
            try:
                if it["kind"] == "image":
                    im = Image.open(p); im.draft("RGB", (TW * 2, TH * 2)); im = im.convert("RGB")
                else:
                    tmp = bundle / "_thumb.jpg"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(min(2, it.get("duration", 1) / 2)), "-i", str(p),
                                    "-frames:v", "1", str(tmp)], check=True)
                    im = Image.open(tmp).convert("RGB"); tmp.unlink()
                im.thumbnail((TW, TH))
                sheet.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
            except Exception:
                d.text((x + 10, y + TH // 2), "PREVIEW FAILED", font=f, fill=(255, 90, 90))
            col = (255, 120, 120) if any(fl.startswith(("SMALL", "LOW_RES")) for fl in it["flags"]) else (255, 220, 120)
            d.text((x + 6, y + TH + 3), f"{it['id']} {it['kind']} {it['orig_width']}x{it['orig_height']}", font=f, fill=col)
            d.text((x + 6, y + TH + 21), (it.get("title") or "")[:48], font=f, fill=(230, 230, 230))
            d.text((x + 6, y + TH + 38), ", ".join(it.get("shots", []))[:48], font=f, fill=(150, 200, 255))
        p = bundle / f"contact_sheet_{k // (COLS * ROWS) + 1:02}.jpg"
        sheet.save(p, quality=85)
        paths.append(p)
    return paths


def write_zips(ep_dir, ep_id, bundle, part_mb):
    for old in ep_dir.glob(f"{ep_id}_assets_part*.zip"):
        old.unlink()
    files = sorted(p for p in bundle.iterdir() if p.is_file())
    meta = [p for p in files if p.suffix in (".json", ".txt") or p.name.startswith("contact_sheet")]
    media = [p for p in files if p not in meta]
    parts, cur, size = [], [], 0
    for p in media:
        s = p.stat().st_size
        if cur and size + s > part_mb * 1e6:
            parts.append(cur); cur, size = [], 0
        cur.append(p); size += s
    if cur or not parts:
        parts.append(cur)
    out = []
    for n, group in enumerate(parts, 1):
        z = ep_dir / f"{ep_id}_assets_part{n:02}.zip"
        with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for p in meta + group:  # every part carries report + sheets, so each part is self-describing
                zf.write(p, f"{ep_id}_assets/{p.name}")
        out.append(z)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode_dir")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--top", type=int, default=2)
    ap.add_argument("--max-width", type=int, default=3840)
    ap.add_argument("--video-mb", type=float, default=150)
    ap.add_argument("--part-mb", type=float, default=400)
    ap.add_argument("--no-zip", action="store_true", help="skip the upload zips (used on GitHub Actions)")
    a = ap.parse_args()

    ep_dir = Path(a.episode_dir).resolve()
    here = Path(__file__).resolve().parent
    cfg_p = next((c for c in (here.parent / "config.json", here / "config.json") if c.exists()), None)
    cfg = load_json(cfg_p) if cfg_p else {"font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"}
    man_p = ep_dir / "asset_manifest.json"
    man = load_json(man_p) if man_p.exists() else {"items": []}
    ep_p = ep_dir / "episode.json"
    ep = load_json(ep_p) if ep_p.exists() else None
    ep_id = man.get("episode") or (ep or {}).get("episode", {}).get("id") or ep_dir.name
    items = [dict(i) for i in man.get("items", [])]
    for i in items:
        i.setdefault("kind", "video" if ext_of(i["url"], "") in VID_EXT else "image")
        i.setdefault("shots", [])

    if a.search:
        if not ep:
            sys.exit("--search needs episode.json in the episode folder")
        covered = {s for i in items for s in i["shots"]}
        n = len(items)
        for s in ep["shots"]:
            v = s.get("visual", {})
            if s["id"] in covered or v.get("file") or not v.get("search_query") or v.get("source_class") == "OUR_CGI":
                continue
            media = "video" if v.get("type") == "video" else "image"
            log(f"search {s['id']}: {v['search_query']!r} ({media})")
            try:
                hits = nasa_search(v["search_query"], media, a.top)
            except Exception as e:
                log(f"   search failed: {e}")
                continue
            if not hits:
                log("   no results: change the search_query or ask Claude for a manual URL")
            for k, h in enumerate(hits, 1):
                n += 1
                items.append(dict(h, id=f"{s['id']}_c{k}", kind=media, shots=[s["id"]], candidate=k,
                                  source_class=v.get("source_class"), from_search=True))

    if not items:
        sys.exit("nothing to download: add asset_manifest.json or use --search")

    orig = ep_dir / "assets" / "originals"; orig.mkdir(parents=True, exist_ok=True)
    bundle = ep_dir / "bundle"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir()
    log(f"{len(items)} items -> {orig}")
    for k, it in enumerate(items, 1):
        dest = orig / f"{it['id']}{ext_of(it['url'], it['kind'])}"
        log(f"[{k}/{len(items)}] {it['id']}  {it['url']}")
        try:
            how = download(it["url"], dest)
            make_transfer_copy(dest, bundle, it, a)
            it["status"] = "ok"
            log(f"   {how}: {it['orig_width']}x{it['orig_height']}" + (f" {it['fps']}fps {it['duration']}s" if it["kind"] == "video" else "")
                + (f"  [{'; '.join(it['flags'])}]" if it["flags"] else ""))
        except Exception as e:
            it["status"] = "failed"; it["error"] = str(e)[:300]
            if dest.exists() and it.get("orig_width") is None:
                dest.unlink()  # corrupt/unreadable file: remove so a re-run downloads it again
            log(f"   FAILED: {e}")

    ok = [i for i in items if i["status"] == "ok"]
    bad = [i for i in items if i["status"] != "ok"]
    report = {"episode": ep_id, "created": time.strftime("%Y-%m-%d %H:%M"), "max_width": a.max_width,
              "ok": len(ok), "failed": len(bad), "items": items}
    save_json(bundle / "report.json", report)
    sheets = contact_sheets(items, bundle, cfg.get("font_path", ""))
    lines = [f"{ep_id} asset bundle - {report['created']}", f"OK {len(ok)}  FAILED {len(bad)}", ""]
    for i in items:
        lines.append(f"{i['id']:12} {i['status']:7} {i.get('orig_width', '?')}x{i.get('orig_height', '?')} "
                     f"{' '.join(i.get('flags', []))} {i.get('error', '')}")
    (bundle / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    zips = [] if a.no_zip else write_zips(ep_dir, ep_id, bundle, a.part_mb)

    log("\n" + "=" * 60)
    log(f"OK {len(ok)}   FAILED {len(bad)}   contact sheets: {len(sheets)}")
    for i in bad:
        log(f"  FAILED {i['id']}: {i.get('error')}")
    if zips:
        log("Upload these to Claude:")
    for z in zips:
            log(f"  {z}  ({z.stat().st_size / 1e6:.0f} MB)")
    if bad:
        log("Re-run the same command to retry failed items (finished ones are skipped).")


if __name__ == "__main__":
    main()
