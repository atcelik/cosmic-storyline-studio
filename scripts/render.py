#!/usr/bin/env python3
"""Render the silent video from episode.json + build/timeline.json.
Sub-pixel eased camera (cv2.warpAffine), transitions, labels, text. Output: build/video_silent.mp4
Usage: render.py episodes/ep01/episode.json [--draft] [--limit SECONDS]"""
import argparse, bisect, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from common import *


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


# ---------- sources ----------
def cover_scale(w, h, W, H):
    return max(W / w, H / h)


def parallax_mask(img, layer):
    """Soft foreground mask for 2.5D parallax.
    layer 'ground': bright regions touching the bottom edge (a limb or surface in front of sky/plumes/planets).
    layer 'body': the largest bright object (a moon or planet in front of space).
    Returns (mask float32 0..1 at img size, inpainted background) or (None, None) when no clear layer exists."""
    h, w = img.shape[:2]
    sw = 960
    sh_ = max(2, round(h * sw / w))
    small = cv2.resize(img, (sw, sh_), interpolation=cv2.INTER_AREA)
    g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (0, 0), 3)
    thr = max(22, int(np.percentile(g, 99.5) * 0.22))
    m = (g > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    if layer == "ground":
        for i in range(1, n):
            x, y, ww, hh, area = stats[i]
            if y + hh >= sh_ - 2 and area > 0.01 * m.size:
                keep[lab == i] = 1
    elif n > 1:
        i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        if stats[i, cv2.CC_STAT_AREA] > 0.01 * m.size:
            keep[lab == i] = 1
    frac = keep.mean()
    if frac < 0.02 or frac > 0.8:
        return None, None
    # fill holes inside the layer
    ff = keep.copy(); pad = np.zeros((sh_ + 2, sw + 2), np.uint8)
    cv2.floodFill(ff, pad, (0, 0), 1)
    keep = keep | (1 - ff)
    hard = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    bg_small = cv2.inpaint(small, hard, 9, cv2.INPAINT_TELEA)
    soft = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 2.5)
    mask = cv2.resize(soft, (w, h), interpolation=cv2.INTER_LINEAR)
    hole = cv2.resize(cv2.GaussianBlur(hard.astype(np.float32), (0, 0), 4), (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
    bg_up = cv2.resize(bg_small, (w, h), interpolation=cv2.INTER_CUBIC)
    bg = (img.astype(np.float32) * (1 - hole) + bg_up.astype(np.float32) * hole).astype(np.uint8)
    return mask, bg


class Source:
    """Holds a 'working' image already scaled to cover the frame at the largest zoom (K)."""
    def __init__(self, shot, base_dir, W, H, look=None):
        v = shot["visual"]
        cam = shot.get("camera") or {}
        look = look or {}
        self.move = cam.get("move", "push_in")
        self.strength = float(cam.get("strength", 0.06))
        self.focus = cam.get("focus", [0.5, 0.5])
        self.focus_from = cam.get("focus_from")
        # documentary motion: constant speed, so the camera is still moving at every cut (ease=true restores in/out easing)
        self.linear = not cam.get("ease", look.get("motion", "linear") != "linear")
        self.drift = float(cam.get("drift", 0.0))           # lateral slide, fraction of frame width over the shot
        self.par = float(cam.get("parallax", 0.0))          # 0..1, foreground moves more than background
        self.layer = cam.get("layer", "ground")
        fl = float(look.get("float", 0.0))
        self.margin = 1.0 + (3.5 * fl + 0.004 if fl else 0.0) + abs(self.drift) * (1 + self.par)
        self.W, self.H = W, H
        base = 1.0 if self.move == "hold" else 1.0 + (max(self.strength, 0.06) if self.move.startswith("pan") else self.strength)
        self.K = (base + self.strength * 0.4 * self.par) * self.margin
        self.kind = v["type"]
        path = base_dir / v["file"]
        self.mask = self.bg = None
        if self.kind == "still":
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                raise RuntimeError(f"cannot read image {path}")
            self.work = self._fit(img)
            if self.par > 0:
                self.mask, self.bg = parallax_mask(self.work, self.layer)
                if self.mask is None:
                    print(f"  {shot['id']}: no clear {self.layer} layer, parallax off", flush=True)
                    self.par = 0.0
            self.vid = None
        else:
            self.vid = cv2.VideoCapture(str(path))
            if not self.vid.isOpened():
                raise RuntimeError(f"cannot open video {path}")
            self.fps = self.vid.get(cv2.CAP_PROP_FPS) or 30.0
            self.n = int(self.vid.get(cv2.CAP_PROP_FRAME_COUNT))
            self.trim = float(v.get("trim_start", 0.0))
            self.speed = float(v.get("speed", 1.0))
            self.pos, self.last = -1, None
            # skip to the trim point by decoding (seeking with CAP_PROP_POS_FRAMES is unreliable on H.264)
            i0 = int(round(self.trim * self.fps))
            if self.n > 0:
                i0 = min(i0, self.n - 1)
            while self.pos < i0 - 1 and self.vid.grab():
                self.pos += 1
            self.work = None

    def _fit(self, img):
        h, w = img.shape[:2]
        s = cover_scale(w, h, self.W, self.H) * self.K
        size = (max(self.W, round(w * s)), max(self.H, round(h * s)))
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
        return cv2.resize(img, size, interpolation=interp)

    def work_at(self, lt):
        if self.kind == "still":
            return self.work
        target = int(self.trim * self.fps + lt * self.speed * self.fps)
        if self.n > 0:
            target = min(target, self.n - 1)
        while self.pos < target:
            ok, f = self.vid.read()
            if not ok:
                break
            self.pos += 1
            self.last = f
        if self.last is None and self.pos >= 0:
            ok, f = self.vid.retrieve()          # the frame at the trim point was grabbed but not decoded
            if ok:
                self.last = f
        if self.last is None:
            raise RuntimeError(f"video has no frames at {target} (has {self.n})")
        return self._fit(self.last)

    def frame(self, lt, dur, fl=(0.0, 0.0, 0.0)):
        """fl = camera float (dx, dy in output px, rotation in degrees), shared by the whole film."""
        u = min(max(lt / dur, 0.0), 1.0)
        e = u if self.linear else ease(u)
        work = self.work_at(lt)
        hh, ww = work.shape[:2]
        mv = self.move
        if mv == "push_in": zp = e
        elif mv == "pull_out": zp = 1 - e
        else: zp = 0.0
        if mv.startswith("pan"):
            z = self.K / self.margin
        else:
            z = 1 + self.strength * zp
        z *= self.margin
        a = z / self.K
        hw, hh_ = self.W / (2 * a), self.H / (2 * a)
        fx, fy = self.focus
        if self.focus_from:
            fx = self.focus_from[0] + (fx - self.focus_from[0]) * e
            fy = self.focus_from[1] + (fy - self.focus_from[1]) * e
        cx, cy = fx * ww, fy * hh
        if mv.startswith("pan"):
            lo, hi = hw, ww - hw
            f = 0.2 + 0.6 * e
            if mv == "pan_left": f = 1 - f
            cx = lo + (hi - lo) * f if hi > lo else ww / 2
        cx = min(max(cx, hw), ww - hw) if ww > 2 * hw else ww / 2
        cy = min(max(cy, hh_), hh - hh_) if hh > 2 * hh_ else hh / 2
        slide = self.drift * self.W * (e - 0.5)
        if self.par <= 0 or self.mask is None:
            return self._warp(work, a, cx, cy, fl[0] + slide, fl[1], fl[2])
        # 2.5D: background zooms/slides less, foreground more
        p = self.par
        zb = (1 + self.strength * zp * (1 - 0.7 * p)) * self.margin / self.K
        zf = (1 + self.strength * zp * (1 + 0.4 * p)) * self.margin / self.K
        bgf = self._warp(self.bg, zb, cx, cy, fl[0] * (1 - 0.5 * p) + slide * (1 - 0.6 * p), fl[1] * (1 - 0.5 * p), fl[2])
        fgf = self._warp(work, zf, cx, cy, fl[0] + slide * (1 + 0.6 * p), fl[1], fl[2])
        m = self._warp(self.mask, zf, cx, cy, fl[0] + slide * (1 + 0.6 * p), fl[1], fl[2], interp=cv2.INTER_LINEAR)[..., None]
        return (bgf.astype(np.float32) * (1 - m) + fgf.astype(np.float32) * m).astype(np.uint8)

    def _warp(self, img, a, cx, cy, dx, dy, rot, interp=cv2.INTER_CUBIC):
        c, s_ = np.cos(np.radians(rot)), np.sin(np.radians(rot))
        A = np.float32([[a * c, -a * s_], [a * s_, a * c]])
        t = np.float32([self.W / 2 + dx, self.H / 2 + dy]) - A @ np.float32([cx, cy])
        M = np.hstack([A, t[:, None]]).astype(np.float32)
        return cv2.warpAffine(img, M, (self.W, self.H), flags=interp, borderMode=cv2.BORDER_REPLICATE)

    def close(self):
        if self.vid is not None:
            self.vid.release()


# ---------- transitions ----------
def transition(A, B, p, kind, W, H):
    e = ease(p)
    if kind == "crossfade":
        return cv2.addWeighted(A, 1 - e, B, e, 0)
    if kind in ("dip_black", "dip_white"):
        c = 0 if kind == "dip_black" else 255
        solid = np.full_like(A, c)
        if e < 0.5:
            return cv2.addWeighted(A, 1 - e * 2, solid, e * 2, 0)
        return cv2.addWeighted(solid, 1 - (e - 0.5) * 2, B, (e - 0.5) * 2, 0)
    if kind in ("push_left", "push_right"):
        sg = -1 if kind == "push_left" else 1
        MA = np.float32([[1, 0, sg * e * W], [0, 1, 0]])
        MB = np.float32([[1, 0, sg * (e - 1) * W], [0, 1, 0]])
        a = cv2.warpAffine(A, MA, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        b = cv2.warpAffine(B, MB, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return cv2.add(a, b)
    if kind == "zoom_through":
        sa, sb = 1 + 0.35 * e, 1.35 - 0.35 * e
        def zm(img, s):
            return cv2.warpAffine(img, np.float32([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]]), (W, H),
                                  flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return cv2.addWeighted(zm(A, sa), 1 - e, zm(B, sb), e, 0)
    return B


# ---------- overlays ----------
def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def to_overlay(canvas):
    arr = np.array(canvas)
    bbox = canvas.getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    sub = arr[y0:y1, x0:x1]
    rgb = sub[..., :3][..., ::-1].astype(np.float32)
    alpha = sub[..., 3].astype(np.float32) / 255.0
    return (x0, y0, rgb, alpha)


def label_overlay(text, W, H, fpath):
    f = font(fpath, max(12, round(H * 0.026)))
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    pad = round(H * 0.012)
    tw = d.textlength(text, font=f)
    th = f.size
    x, y = round(W * 0.03), H - round(H * 0.05) - th - 2 * pad
    d.rounded_rectangle([x, y, x + tw + 2 * pad, y + th + 2 * pad], radius=pad, fill=(0, 0, 0, 165))
    d.text((x + pad, y + pad - 1), text, font=f, fill=(255, 255, 255, 255))
    return to_overlay(c)


def text_overlay(text, W, H, fpath):
    f = font(fpath, max(16, round(H * 0.06)))
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) > W * 0.8 and cur:
            lines.append(cur); cur = w_
        else:
            cur = t
    lines.append(cur)
    lh = round(f.size * 1.25)
    y = round(H * 0.70)
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=(255, 255, 255, 255), stroke_width=max(2, round(H * 0.004)),
               stroke_fill=(0, 0, 0, 255))
        y += lh
    return to_overlay(c)


SOURCE_WORD = {"REAL_PHOTO": "Photo", "REAL_VIDEO": "Footage", "PROCESSED_DATA": "Processed data",
               "SCIENTIFIC_CGI": "Scientific visualization", "ARTIST_CONCEPT": "Artist's concept", "OUR_CGI": "Illustration"}


def card_overlay(card, shot, W, H, cfg):
    """Top-left chapter card: brand, title, accent rule, subtitle, one small source line."""
    k = H / 1080
    fonts = cfg.get("card_fonts", {})
    def F(role, default, size):
        return font(fonts.get(role, default), round(size * k))
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    gh, gw = round(300 * k), round(1000 * k)
    for i in range(gh):
        a = int(120 * (1 - i / gh) ** 2)
        d.rectangle([0, i, gw, i + 1], fill=(0, 0, 0, a))
    x, y = round(64 * k), round(54 * k)
    accent = tuple(cfg.get("card_accent", [159, 212, 255]))
    d.text((x, y), cfg.get("brand", "COSMIC STORYLINE"), font=F("brand", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19), fill=accent + (235,))
    d.text((x, y + round(30 * k)), card["title"], font=F("title", cfg["font_path"], 46), fill=(255, 255, 255, 250))
    d.line([x, y + round(94 * k), x + round(56 * k), y + round(94 * k)], fill=accent + (230,), width=max(2, round(3 * k)))
    yy = y + round(106 * k)
    if card.get("sub"):
        d.text((x, yy), card["sub"], font=F("sub", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24), fill=(225, 232, 242, 235))
        yy += round(34 * k)
    v = shot["visual"]
    src = card.get("source") or f"{SOURCE_WORD.get(v['source_class'], '')} · {v.get('credit_short') or v.get('credit', '')}"
    d.text((x, yy), src[:90], font=F("source", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17), fill=(175, 185, 200, 210))
    return to_overlay(c)


def blend_overlay(frame, ov, g):
    if ov is None or g <= 0:
        return
    x, y, rgb, alpha = ov
    h, w = alpha.shape
    roi = frame[y:y + h, x:x + w].astype(np.float32)
    a = (alpha * g)[..., None]
    frame[y:y + h, x:x + w] = (roi * (1 - a) + rgb * a).astype(np.uint8)


def env(lt, start, end, fade=0.3):
    if lt < start or lt > end:
        return 0.0
    return min(1.0, (lt - start) / fade, (end - lt) / fade)


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--limit", type=float, default=0, help="render only first N seconds (testing)")
    ap.add_argument("--frames", default="", help="a:b = render only frames a..b-1 (parallel chunks; join with ffmpeg concat)")
    ap.add_argument("--out", default="", help="output file (default build/video_silent.mp4 or video_draft.mp4)")
    a = ap.parse_args()
    cfg = load_config()
    base, build = ep_dirs(a.episode)
    ep = load_json(a.episode)
    tl = load_json(build / "timeline.json")
    sc = cfg["draft"]["scale"] if a.draft else 1.0
    W, H, fps = int(cfg["width"] * sc) // 2 * 2, int(cfg["height"] * sc) // 2 * 2, cfg["fps"]
    q = cfg["draft"] if a.draft else cfg["video"]
    shots, T = ep["shots"], tl["shots"]
    starts = [t["start"] for t in T]
    total = tl["total"] if not a.limit else min(a.limit, tl["total"])
    nframes = int(round(total * fps))
    fade_out = cfg["timing"]["end_fade"]

    # labels / overlays prepared once per shot
    labels = {}
    prev_key = None
    for s in shots:
        if not cfg.get("corner_labels", False):
            break                                  # owner rule 2026-11-22: never a corner label
        v = s["visual"]
        key = (v["source_class"], v.get("credit", ""))
        default = v["source_class"] in cfg.get("label_classes", list(cfg["labels"]))
        show = s.get("label", default) and key != prev_key
        prev_key = key
        if show:
            lab = cfg["labels"][v["source_class"]]
            cr = v.get("credit", "")
            txt = f"{lab} · {cr}"[:70] if (cr and cfg.get("label_credit", True)) else lab
            txt = s.get("label_text", txt)
            labels[s["id"]] = label_overlay(txt, W, H, cfg["font_path"])
    texts = {s["id"]: text_overlay(s["on_screen_text"], W, H, cfg["font_path"]) for s in shots if s.get("on_screen_text")}
    # chapter cards: a shot with "card", or the first shot of a beat that has a "chapter" title
    beats = {b["id"]: b for b in ep.get("beats", [])}
    cards, seen = [], set()
    for i, s in enumerate(shots):
        cd = s.get("card")
        if cd is None and s.get("beat") not in seen and beats.get(s.get("beat"), {}).get("chapter"):
            b = beats[s["beat"]]
            cd = {"title": b["chapter"], "sub": b.get("chapter_sub", "")}
        seen.add(s.get("beat"))
        if cd:
            cards.append((T[i]["start"] + 0.35, card_overlay(cd, s, W, H, cfg)))
    CARD_IN, CARD_HOLD, CARD_OUT = 0.6, cfg.get("card_seconds", 4.5), 0.9

    def card_alpha(t):
        for t0, ov in reversed(cards):
            if t >= t0:
                u = t - t0
                if u < CARD_IN: return ov, u / CARD_IN
                if u < CARD_IN + CARD_HOLD: return ov, 1.0
                if u < CARD_IN + CARD_HOLD + CARD_OUT: return ov, 1 - (u - CARD_IN - CARD_HOLD) / CARD_OUT
                return None, 0.0
        return None, 0.0

    out = Path(a.out) if a.out else build / ("video_draft.mp4" if a.draft else "video_silent.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    f0, f1 = 0, nframes
    if a.frames:
        f0, f1 = (int(x) for x in a.frames.split(":"))
        f1 = min(f1, nframes)
    vf = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-an", "-vf", vf, "-c:v", "libx264", "-preset", q["preset"],
           "-crf", str(q["crf"]), "-profile:v", "high", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-movflags", "+faststart", str(out)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    vig = None
    vs = cfg.get("look", {}).get("vignette", 0)
    if vs:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        vig = (1 - vs * np.clip(r2 / 2, 0, 1) ** 1.2)[..., None].astype(np.float32)

    look = cfg.get("look", {})
    fl_amp = float(look.get("float", 0.0))
    rng = np.random.default_rng(11)
    ph = rng.uniform(0, 2 * np.pi, 6)

    def cam_float(t):
        if not fl_amp:
            return (0.0, 0.0, 0.0)
        dx = fl_amp * W * (0.6 * np.sin(2 * np.pi * 0.061 * t + ph[0]) + 0.4 * np.sin(2 * np.pi * 0.137 * t + ph[1]))
        dy = fl_amp * W * 0.6 * (0.6 * np.sin(2 * np.pi * 0.053 * t + ph[2]) + 0.4 * np.sin(2 * np.pi * 0.119 * t + ph[3]))
        r = fl_amp * 25 * (0.6 * np.sin(2 * np.pi * 0.041 * t + ph[4]) + 0.4 * np.sin(2 * np.pi * 0.097 * t + ph[5]))
        return (dx, dy, r)

    grain = float(look.get("grain", 0.0))
    noise = None
    if grain:
        noise = (rng.standard_normal((H, W)).astype(np.float32) * grain * 255)

    # "continue": true on a video shot = same flight as the shot before, picking up where it stopped
    acc = {}
    for i, s in enumerate(shots):
        v = s["visual"]
        if v.get("type") == "video" and v.get("continue") and i > 0:
            pv = shots[i - 1]["visual"]
            if pv.get("file") == v.get("file"):
                v["trim_start"] = acc.get(i - 1, float(pv.get("trim_start", 0.0))) + T[i - 1]["dur"] - T[i - 1]["trans_d"]
        acc[i] = float(v.get("trim_start", 0.0))

    cache = {}

    def get(i):
        if i not in cache:
            for k in [k for k in cache if k < i - 1]:
                cache.pop(k).close()
            cache[i] = Source(shots[i], base, W, H, look)
        return cache[i]

    def shot_frame(i, t):
        lt = t - T[i]["start"]
        f = get(i).frame(lt, T[i]["dur"], cam_float(t))
        sid = shots[i]["id"]
        if sid in labels:
            blend_overlay(f, labels[sid], env(lt, 0.4, 3.6))
        if sid in texts:
            blend_overlay(f, texts[sid], env(lt, shots[i].get("text_start", 0.5), T[i]["dur"] - 0.6, 0.5))
        return f

    t0 = time.time()
    try:
        for n in range(f0, f1):
            t = n / fps
            i = max(0, bisect.bisect_right(starts, t + 1e-9) - 1)
            fr = shot_frame(i, t)
            if i > 0 and T[i - 1]["trans"] != "cut" and t < starts[i] + T[i - 1]["trans_d"]:
                p = (t - starts[i]) / T[i - 1]["trans_d"]
                fr = transition(shot_frame(i - 1, t), fr, p, T[i - 1]["trans"], W, H)
            cov, ca = card_alpha(t)
            if cov is not None and ca > 0:
                blend_overlay(fr, cov, ease(ca))
            if vig is not None or noise is not None:
                ff = fr.astype(np.float32)
                if vig is not None:
                    ff *= vig
                if noise is not None:
                    nz = np.roll(noise, (int(rng.integers(0, H)), int(rng.integers(0, W))), axis=(0, 1))
                    ff += nz[..., None]
                fr = np.clip(ff, 0, 255).astype(np.uint8)
            if tl["total"] - t < fade_out:
                k = ease((t - (tl["total"] - fade_out)) / fade_out)
                fr = (fr.astype(np.float32) * (1 - k)).astype(np.uint8)
            enc.stdin.write(np.ascontiguousarray(fr).tobytes())
            if n > f0 and (n - f0) % 150 == 0:
                sp = (n - f0) / (time.time() - t0)
                print(f"  frame {n}/{f1}  {sp:.1f} fps  ETA {(f1 - n) / sp / 60:.1f} min", flush=True)
    finally:
        enc.stdin.close()
        enc.wait()
        for s in cache.values():
            s.close()
    if enc.returncode != 0:
        sys.exit("ffmpeg failed")
    print(f"Rendered frames {f0}..{f1 - 1} in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
