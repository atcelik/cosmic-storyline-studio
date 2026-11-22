#!/usr/bin/env python3
"""Write build/captions.srt and build/description.txt (chapters + credits) from episode.json + timeline.json."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def chunks(text, max_chars=42, max_words=7):
    out, cur = [], []
    for w in text.split():
        cur.append(w)
        line = " ".join(cur)
        if len(line) >= max_chars or len(cur) >= max_words or re.search(r"[.!?;:,]$", w) and len(cur) >= 3:
            out.append(line); cur = []
    if cur: out.append(" ".join(cur))
    return out


def main():
    cfg = load_config()
    base, build = ep_dirs(sys.argv[1])
    ep = load_json(sys.argv[1])
    tl = load_json(build / "timeline.json")
    srt, n = [], 1
    for s, t in zip(ep["shots"], tl["shots"]):
        text = (s.get("voiceover") or "").strip()
        if not text: continue
        cs = chunks(text)
        tot = sum(len(c) for c in cs)
        cur = t["vo_start"]
        for c in cs:
            d = t["vo_dur"] * len(c) / tot
            srt.append(f"{n}\n{ts(cur)} --> {ts(cur + d)}\n{c}\n")
            cur += d; n += 1
    (build / "captions.srt").write_text("\n".join(srt), encoding="utf-8")

    start_of_beat = {}
    for s, t in zip(ep["shots"], tl["shots"]):
        start_of_beat.setdefault(s["beat"], t["start"])
    lines = ["CHAPTERS"]
    for b in ep["beats"]:
        if b.get("chapter") and b["id"] in start_of_beat:
            m = int(start_of_beat[b["id"]] // 60); sec = int(start_of_beat[b["id"]] % 60)
            lines.append(f"{m}:{sec:02} {b['chapter']}")
    lines += ["", "VISUAL CREDITS"]
    seen = set()
    for s in ep["shots"]:
        v = s["visual"]
        if v["source_class"] == "OUR_CGI": continue
        key = (v.get("credit"), v.get("source_url"))
        if key in seen: continue
        seen.add(key)
        lines.append(f"- [{v['source_class']}] {v.get('credit')} — {v.get('source_url')}")
    m = ep.get("music")
    if m: lines.append(f"- Music: {m.get('credit','?')} ({m.get('license','?')})")
    lines += ["", "NOTES",
              "Some visuals are scientific visualizations, artist's concepts or illustrations; they are labelled on screen.",
              f"Narration: synthetic voice ({ep.get('voice', {}).get('engine', cfg['tts']['engine'])}).",
              "Not endorsed by NASA, ESA or any agency."]
    (build / "description.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote build/captions.srt and build/description.txt")


if __name__ == "__main__":
    main()
