#!/usr/bin/env python3
"""Contact sheets (20 shots per JPG): picked asset + shot id + voice-over. Output: build/sheets/sheet_NN.jpg"""
import sys
from pathlib import Path
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from common import *

TW, TH, CAP, COLS, ROWS = 400, 225, 62, 4, 5
cfg = load_config()
base, build = ep_dirs(sys.argv[1])
ep = load_json(sys.argv[1])
out = build / "sheets"; out.mkdir(exist_ok=True)
try: f = ImageFont.truetype(cfg["font_path"], 15)
except Exception: f = ImageFont.load_default()


def thumb(s):
    v = s["visual"]; p = base / v["file"] if v.get("file") else None
    if not p or not p.exists(): return None
    if v["type"] == "still":
        im = Image.open(p); im.draft("RGB", (TW * 2, TH * 2)); im = im.convert("RGB")
    else:
        c = cv2.VideoCapture(str(p)); c.set(cv2.CAP_PROP_POS_MSEC, float(v.get("trim_start", 0)) * 1000)
        ok, fr = c.read(); c.release()
        if not ok: return None
        im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    im.thumbnail((TW, TH)); return im


def wrap(t, n=46):
    out, cur = [], ""
    for w in t.split():
        if len(cur) + len(w) + 1 > n and cur: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return (out + [cur])[:2]


per = COLS * ROWS
shots = ep["shots"]
for k in range(0, len(shots), per):
    chunk = shots[k:k + per]
    rows = (len(chunk) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TW, rows * (TH + CAP)), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for j, s in enumerate(chunk):
        x, y = (j % COLS) * TW, (j // COLS) * (TH + CAP)
        t = thumb(s)
        if t: sheet.paste(t, (x + (TW - t.width) // 2, y + (TH - t.height) // 2))
        else: d.text((x + 10, y + TH // 2), "MISSING", font=f, fill=(255, 90, 90))
        d.text((x + 6, y + TH + 3), f"{s['id']}  {s['visual']['source_class']}", font=f, fill=(255, 220, 120))
        for i, ln in enumerate(wrap(s.get("voiceover", ""))):
            d.text((x + 6, y + TH + 21 + i * 17), ln, font=f, fill=(235, 235, 235))
    p = out / f"sheet_{k // per + 1:02}.jpg"; sheet.save(p, quality=85); print("wrote", p)
