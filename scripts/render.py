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


class Source:
    """Holds a 'working' image already scaled to cover the frame at the largest zoom (K)."""
    def __init__(self, shot, base_dir, W, H):
        v = shot["visual"]
        cam = shot.get("camera") or {}
        self.move = cam.get("move", "push_in")
        self.strength = float(cam.get("strength", 0.06))
        self.focus = cam.get("focus", [0.5, 0.5])
        self.focus_from = cam.get("focus_from")
        self.W, self.H = W, H
        self.K = 1.0 if self.move == "hold" else 1.0 + (max(self.strength, 0.06) if self.move.startswith("pan") else self.strength)
        self.kind = v["type"]
        path = base_dir / v["file"]
        if self.kind == "still":
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                raise RuntimeError(f"cannot read image {path}")
            self.work = self._fit(img)
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
            i0 = int(round(self.trim * self.fps))
            if i0 > 0:
                self.vid.set(cv2.CAP_PROP_POS_FRAMES, i0)
                self.pos = i0 - 1
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
        if self.last is None:
            raise RuntimeError("video has no frames")
        return self._fit(self.last)

    def frame(self, lt, dur):
        u = min(max(lt / dur, 0.0), 1.0)
        e = ease(u)
        work = self.work_at(lt)
        hh, ww = work.shape[:2]
        mv = self.move
        if mv == "push_in": z = 1 + self.strength * e
        elif mv == "pull_out": z = 1 + self.strength * (1 - e)
        elif mv.startswith("pan"): z = self.K
        else: z = 1.0
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
        M = np.float32([[a, 0, self.W / 2 - a * cx], [0, a, self.H / 2 - a * cy]])
        return cv2.warpAffine(work, M, (self.W, self.H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

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

    out = build / ("video_draft.mp4" if a.draft else "video_silent.mp4")
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

    cache = {}

    def get(i):
        if i not in cache:
            for k in [k for k in cache if k < i - 1]:
                cache.pop(k).close()
            cache[i] = Source(shots[i], base, W, H)
        return cache[i]

    def shot_frame(i, t):
        lt = t - T[i]["start"]
        f = get(i).frame(lt, T[i]["dur"])
        sid = shots[i]["id"]
        if sid in labels:
            blend_overlay(f, labels[sid], env(lt, 0.4, 3.6))
        if sid in texts:
            blend_overlay(f, texts[sid], env(lt, shots[i].get("text_start", 0.5), T[i]["dur"] - 0.6, 0.5))
        return f

    t0 = time.time()
    try:
        for n in range(nframes):
            t = n / fps
            i = max(0, bisect.bisect_right(starts, t + 1e-9) - 1)
            fr = shot_frame(i, t)
            if i > 0 and T[i - 1]["trans"] != "cut" and t < starts[i] + T[i - 1]["trans_d"]:
                p = (t - starts[i]) / T[i - 1]["trans_d"]
                fr = transition(shot_frame(i - 1, t), fr, p, T[i - 1]["trans"], W, H)
            if vig is not None:
                fr = (fr.astype(np.float32) * vig).astype(np.uint8)
            if tl["total"] - t < fade_out:
                k = ease((t - (tl["total"] - fade_out)) / fade_out)
                fr = (fr.astype(np.float32) * (1 - k)).astype(np.uint8)
            enc.stdin.write(np.ascontiguousarray(fr).tobytes())
            if n and n % 150 == 0:
                sp = n / (time.time() - t0)
                print(f"  frame {n}/{nframes}  {sp:.1f} fps  ETA {(nframes - n) / sp / 60:.1f} min", flush=True)
    finally:
        enc.stdin.close()
        enc.wait()
        for s in cache.values():
            s.close()
    if enc.returncode != 0:
        sys.exit("ffmpeg failed")
    print(f"Rendered {nframes} frames in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
