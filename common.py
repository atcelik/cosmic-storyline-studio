"""Shared helpers: config, timeline math. No third-party deps."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_CLASSES = {"REAL_PHOTO", "REAL_VIDEO", "PROCESSED_DATA", "SCIENTIFIC_CGI", "ARTIST_CONCEPT", "OUR_CGI"}
CAMERA_MOVES = {"push_in", "pull_out", "pan_left", "pan_right", "hold"}
TRANSITIONS = {"cut", "crossfade", "dip_black", "dip_white", "push_left", "push_right", "zoom_through"}
EVENT_TRANSITIONS = {"dip_black", "dip_white", "push_left", "push_right", "zoom_through"}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save_json(p, data):
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config():
    return load_json(ROOT / "config.json")


def ep_dirs(episode_json):
    base = Path(episode_json).resolve().parent
    build = base / "build"
    build.mkdir(exist_ok=True)
    return base, build


def est_vo_seconds(text, wps=2.6):
    n = len(re.findall(r"[A-Za-z0-9'’-]+", text))
    return n / wps if n else 0.0


def build_timeline(ep, cfg, vo=None):
    """Return {'shots': [...], 'total': seconds}. Shots overlap by their transition duration.
    vo: optional {shot_id: real voice-over seconds}; otherwise estimated from word count."""
    t = cfg["timing"]
    shots = ep["shots"]
    n = len(shots)
    req = []
    for s in shots:
        tr = s.get("transition_out") or {}
        typ = tr.get("type", "cut")
        d = 0.0 if typ == "cut" else float(tr.get("duration", 0.5))
        req.append((typ, d))
    durs = []
    for i, s in enumerate(shots):
        text = (s.get("voiceover") or "").strip()
        vo_d = 0.0
        if text:
            vo_d = (vo or {}).get(s["id"]) or est_vo_seconds(text, t["words_per_sec"])
        prev_d = req[i - 1][1] if i > 0 else 0.0
        lead = t["vo_lead"] + 0.5 * prev_d
        tail = t["vo_tail"] + 0.5 * req[i][1]
        need = lead + vo_d + tail if text else 0.0
        dur = max(float(s.get("min_duration", 0)), need, t["min_shot"])
        durs.append((dur, vo_d, lead))
    out, start = [], 0.0
    for i, s in enumerate(shots):
        dur, vo_d, lead = durs[i]
        typ, d = req[i]
        if i == n - 1:
            typ, d = "cut", 0.0
            dur += t["end_hold"]
        else:
            d = min(d, 0.4 * dur, 0.4 * durs[i + 1][0])
            if d < 0.15:
                typ, d = "cut", 0.0
        out.append(dict(id=s["id"], start=round(start, 4), dur=round(dur, 4),
                        vo_start=round(start + lead, 4), vo_dur=round(vo_d, 4),
                        trans=typ, trans_d=round(d, 4)))
        start += dur - d
    total = out[-1]["start"] + out[-1]["dur"] if out else 0.0
    return {"shots": out, "total": round(total, 4)}
