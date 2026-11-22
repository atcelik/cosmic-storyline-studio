#!/usr/bin/env python3
"""Validate an episode.json: structure, retention pacing, source labelling, assets.
Usage: validate.py episodes/ep01/episode.json [--assets] [--strict]
--assets  also check files exist + resolution/fps.
--strict  unverified credits/claims become errors (use before publishing)."""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

errors, warns = [], []
E_ = lambda m: errors.append(m)
W_ = lambda m: warns.append(m)


def finish():
    for m in warns: print("WARN ", m)
    for m in errors: print("ERROR", m)
    print(f"Result: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warns)} warnings)")
    sys.exit(1 if errors else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--assets", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    ep = load_json(a.episode)
    base = Path(a.episode).resolve().parent
    R = cfg["retention"]

    if ep.get("schema_version") != 2:
        E_("schema_version must be 2")
    meta = ep.get("episode", {})
    for k in ("id", "title", "central_question"):
        if not meta.get(k):
            E_(f"episode.{k} missing")
    if meta.get("language") != "en":
        E_("episode.language must be 'en'")
    beats = ep.get("beats", [])
    shots = ep.get("shots", [])
    if not beats: E_("beats[] missing")
    if not shots:
        E_("shots[] missing"); finish()
    beat_ids = [b.get("id") for b in beats]
    for i, b in enumerate(beats):
        if not b.get("id") or not b.get("name"):
            E_(f"beats[{i}] needs id and name")
        if i > 0 and not b.get("because"):
            E_(f"beat {b.get('id')}: missing 'because' (the but/therefore link to the previous beat)")

    seen, last_beat_idx = set(), -1
    for s in shots:
        sid = s.get("id", "?")
        if sid in seen: E_(f"duplicate shot id {sid}")
        seen.add(sid)
        if s.get("beat") not in beat_ids:
            E_(f"{sid}: unknown beat {s.get('beat')}")
        else:
            bi = beat_ids.index(s["beat"])
            if bi < last_beat_idx: E_(f"{sid}: beat order goes backwards")
            last_beat_idx = max(last_beat_idx, bi)
        v = s.get("visual", {})
        if v.get("type") not in ("still", "video"): E_(f"{sid}: visual.type must be still|video")
        sc = v.get("source_class")
        if sc not in SOURCE_CLASSES:
            E_(f"{sid}: visual.source_class must be one of {sorted(SOURCE_CLASSES)} (generative AI imagery is not allowed)")
        if not v.get("file") and not v.get("search_query"):
            E_(f"{sid}: visual needs file or search_query")
        if sc and sc != "OUR_CGI":
            if not v.get("credit"): E_(f"{sid}: visual.credit missing")
            if not v.get("source_url"): E_(f"{sid}: visual.source_url missing")
            if v.get("file") and not v.get("credit_verified"):
                (E_ if a.strict else W_)(f"{sid}: credit/licence not marked credit_verified=true")
        cam = s.get("camera") or {}
        if cam.get("move", "push_in") not in CAMERA_MOVES: E_(f"{sid}: bad camera.move")
        if not (0 <= cam.get("strength", 0.06) <= 3.0): E_(f"{sid}: camera.strength must be 0..3.0")
        if not (0 <= cam.get("parallax", 0) <= 1): E_(f"{sid}: camera.parallax must be 0..1")
        if cam.get("layer", "ground") not in ("ground", "body"): E_(f"{sid}: camera.layer must be ground or body")
        if abs(cam.get("drift", 0)) > 0.06: E_(f"{sid}: camera.drift must be within -0.06..0.06")
        if cam.get("parallax") and (s.get("visual") or {}).get("type") != "still": W_(f"{sid}: parallax only works on stills")
        if cam.get("move", "push_in") != "hold" and not cam.get("focus"):
            W_(f"{sid}: no camera.focus: zoom will go to the frame centre, not to the point of interest")
        tr = s.get("transition_out") or {}
        if tr.get("type", "cut") not in TRANSITIONS: E_(f"{sid}: bad transition type")
        if tr.get("type", "cut") != "cut" and not (0.2 <= float(tr.get("duration", 0.5)) <= 1.5):
            E_(f"{sid}: transition duration must be 0.2..1.5")
        vo = (s.get("voiceover") or "").strip()
        if vo and re.search(r"\d", vo) and not s.get("claims"):
            W_(f"{sid}: voice-over has numbers but no claims[] with a source")
        for c in s.get("claims", []):
            if not c.get("source_url"): E_(f"{sid}: claim without source_url")
            if not c.get("verified"):
                (E_ if a.strict else W_)(f"{sid}: claim not verified: {c.get('text','')[:50]}")

    if errors: finish()
    tl = build_timeline(ep, cfg)
    T = {t["id"]: t for t in tl["shots"]}
    for s in shots:
        d = T[s["id"]]["dur"]
        if d > R["max_shot_error"]: E_(f"{s['id']}: {d:.1f}s is too long for one shot (split it)")
        elif d > R["max_shot_warn"]: W_(f"{s['id']}: {d:.1f}s shot (retention rule: <= {R['max_shot_warn']}s)")
    hook = [t for t in tl["shots"] if t["start"] < R["hook_window"]]
    if len(hook) < R["hook_min_shots"]:
        W_(f"hook: only {len(hook)} shots in first {R['hook_window']}s (want >= {R['hook_min_shots']})")
    if not (shots[0].get("voiceover") or "").strip():
        W_("first shot has no voice-over: open with the hook line")
    run_t, last_t, run_h = 0, None, 0
    for s in shots:
        t = (s.get("transition_out") or {}).get("type", "cut")
        run_t = run_t + 1 if t == last_t else 1
        last_t = t
        if t != "cut" and run_t > R["max_same_transition_run"]: W_(f"{s['id']}: same transition '{t}' used {run_t}x in a row")
        hold = (s.get("camera") or {}).get("move", "push_in") == "hold" and (s.get("visual") or {}).get("type") != "video"
        run_h = run_h + 1 if hold else 0
        if run_h > R["max_hold_run"]: W_(f"{s['id']}: {run_h} static 'hold' shots in a row")
    ours = sum(1 for s in shots if s["visual"].get("source_class") == "OUR_CGI")
    share = cfg["retention"].get("max_cgi_share", 0.6)
    if ours > share * len(shots): W_(f"{ours}/{len(shots)} shots are OUR_CGI; keep it <= {share:.0%} (mix with real NASA imagery)")
    ev = sum(1 for s in shots if (s.get("transition_out") or {}).get("type") in EVENT_TRANSITIONS)
    if ev > max(4, len(beats) * 1.5): W_(f"{ev} 'event' transitions: reserve them for beat changes")
    if ep.get("music") is None: W_("no music bed defined")
    tot = tl["total"]
    print(f"Estimated runtime: {tot/60:.1f} min ({len(shots)} shots, avg {tot/len(shots):.1f}s/shot)")
    if not (R["target_min"] <= tot <= R["target_max"]):
        W_(f"runtime {tot:.0f}s outside target {R['target_min']}-{R['target_max']}s")
    if a.assets:
        check_assets(ep, base, cfg, T)
    finish()


def check_assets(ep, base, cfg, T):
    from PIL import Image
    import cv2
    A = cfg["assets"]
    for s in ep["shots"]:
        v = s["visual"]
        f = v.get("file")
        if not f:
            E_(f"{s['id']}: unresolved asset (search_query only)")
            continue
        p = base / f
        if not p.exists():
            E_(f"{s['id']}: file not found {f}")
            continue
        if v["type"] == "still":
            w, h = Image.open(p).size
            if v.get("fit") == "contain":
                if w < 400: E_(f"{s['id']}: image only {w}px wide, too small even framed on black")
                continue
            mv = (s.get("camera") or {}).get("move", "push_in")
            eff = max(cfg["width"] / w, cfg["height"] / h) * (1 + (s.get("camera") or {}).get("strength", 0.06) if mv != "hold" else 1)
            if eff > 1.0: W_(f"{s['id']}: source is upscaled {eff:.2f}x at the closest zoom: will look soft")
            if w < A["still_min_width_error"]: E_(f"{s['id']}: image only {w}px wide")
            elif w < A["still_min_width_warn"] and (s.get("camera") or {}).get("move", "push_in") != "hold":
                W_(f"{s['id']}: image {w}px wide; will look soft with camera motion (want >= {A['still_min_width_warn']})")
        else:
            c = cv2.VideoCapture(str(p))
            h, fps, n = c.get(4), c.get(5), c.get(7)
            c.release()
            if h < 1080: W_(f"{s['id']}: video only {int(h)}p")
            if fps and all(abs(fps - x) > 0.1 for x in (30, 60, 29.97, 59.94)):
                W_(f"{s['id']}: video is {fps:.2f} fps; expect slight judder at 30 fps output")
            if fps and n / fps + 0.05 < T[s["id"]]["dur"] * v.get("speed", 1.0):
                W_(f"{s['id']}: clip ({n/fps:.1f}s) shorter than shot ({T[s['id']]['dur']:.1f}s): last frame will freeze")
    m = ep.get("music")
    if m and not (base / m["file"]).exists(): E_(f"music file not found {m['file']}")


if __name__ == "__main__":
    main()
