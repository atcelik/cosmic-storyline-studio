#!/usr/bin/env python3
"""Size-and-distance comparison scenes (the "size comparison" look: bodies side by side on black space, a big
name + type + size label per body, measuring arrows, a light beam with a running clock). OUR visualization:
label it OUR_CGI. Surfaces are real map textures (Solar System Scope, CC BY 4.0, based on NASA data).

Usage: scale2d.py spec.json out.mp4 [--draft]          (whole clip)
       scale2d.py spec.json still.png --still 0.5        (one frame, for previews)

World units are kilometres on one horizontal line (y = 0 through the centres). The view moves at constant speed
(rule 6: still moving at every cut): centre moves linearly, the visible width changes at a constant ratio.

spec = {
 "duration": 8, "fit": true, "fallback": 8, "seed": 3,
 "view": {"center_km": [x0, x1], "width_km": [w0, w1], "y_km": [y0, y1]},
 "light": [-0.8, -0.25],                       # screen direction TO the Sun (x right, y up) for day/night shading
 "bodies": [{"name": "EARTH", "type": "Terrestrial planet", "size": "12,742 km", "diameter_km": 12742,
             "x_km": 0, "texture": "../EARTHSS.jpg", "tint": [70, 120, 200], "spin": [0, 8],
             "emissive": false, "glow": 0, "dim": [[0.3, 0.45]],  # dim: fade to dark between these fractions
             "label_at": 0.05, "repeat": 1, "step_km": 0, "ghost": false}],
 "arrows": [{"from_km": 0, "to_km": 384400, "y_frac": 0.22, "text": "384,400 km", "sub": "about 30 Earth diameters",
             "at": 0.15}],
 "beam": {"from_km": 0, "to_km": 384400, "t": [0.15, 0.85], "text": "LIGHT takes 1.28 s",
          "clock": [0, 1.28], "clock_fmt": "s", "y_frac": 0.0, "stop_at": null},
 "ripples": {"x_km": 0, "t": [0.2, 0.9], "count": 3, "dashed": true},
 "headline": {"text": "1 ASTRONOMICAL UNIT", "sub": "the yardstick of the solar system", "at": 0.1}
}
More keys: "beams": [beam, ...] (several), "flares": [{"x_km","y_km","strength"}], "texts": [{"x_frac","y_frac",
"lines":[[text,size_frac,"yellow|white|cyan"]],"at"}], "clock": {"x_frac","y_frac","t":[a,b],"seconds":[0,500],"fmt":"ms","label"},
"stars": [{"x_frac","y_frac","size","label","sub","at","color":[r,g,b]}], "bubbles": [{"x_frac","y_frac","text","at"}],
"backdrop": {"type":"ocean","depth":[0,0.6]}, "zigzag": {"x_km","y_km","radius_km","t":[a,b],"steps":40,"seed":1},
body keys: "label": false, "label_xy": [fx, fy], "glow_color": [r,g,b]. Every element fades in at its "at" fraction (0.5 s fade) and stays."""
import argparse, json, math, subprocess, sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import load_config

cv2.setNumThreads(0)
YELLOW = (255, 214, 64)
WHITE = (236, 240, 248)
CYAN = (150, 225, 255)
_tex_cache, _font_cache = {}, {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _font_cache:
        cfg = load_config()
        path = cfg.get("font_path", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if not bold:
            path = path.replace("-Bold", "").replace("Bold", "")
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except OSError:
            _font_cache[key] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    return _font_cache[key]


def lin(v, u):
    """[a, b] -> linear value at u; a scalar stays constant."""
    if isinstance(v, (list, tuple)):
        if len(v) == 1:
            return float(v[0])
        return float(v[0]) + (float(v[-1]) - float(v[0])) * u
    return float(v)


def fade(at, t_sec, dur):
    """0..1 opacity: fades in over 0.5 s starting at fraction `at`."""
    if at is None:
        return 1.0
    return float(np.clip((t_sec - at * dur) / 0.5, 0, 1))


def load_texture(base, path, tint, seed, recolor=False):
    key = (str(path), tuple(tint or ()), seed, recolor)
    if key in _tex_cache:
        return _tex_cache[key]
    tex = None
    if path:
        p = (base / path).resolve()
        if p.exists():
            tex = cv2.cvtColor(cv2.imread(str(p), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            if tex.shape[1] > 4096:
                tex = cv2.resize(tex, (4096, 2048), interpolation=cv2.INTER_AREA)
        else:
            print(f"WARN texture missing: {p} (procedural placeholder used; do not publish this render)", file=sys.stderr)
    if tex is None:                      # placeholder: soft noise in the tint colour
        rng = np.random.default_rng(seed)
        n = cv2.resize(rng.random((32, 64)).astype(np.float32), (1024, 512), interpolation=cv2.INTER_CUBIC)
        n = cv2.GaussianBlur(n, (0, 0), 6)
        n = (n - n.min()) / max(np.ptp(n), 1e-6)
        col = np.array(tint or (160, 160, 160), np.float32)
        tex = np.clip(col * (0.6 + 0.6 * n[..., None]), 0, 255).astype(np.uint8)
    elif recolor and tint and len(tint) == 3:   # recolour only when asked (e.g. a red dwarf from the Sun map) (e.g. a red dwarf from the Sun map)
        g = tex.astype(np.float32).mean(axis=2, keepdims=True) / 255.0
        tex = np.clip(g * np.array(tint, np.float32) * 1.6, 0, 255).astype(np.uint8)
    _tex_cache[key] = tex
    return tex


def star_field(W, H, seed, n=1600):
    rng = np.random.default_rng(seed)
    img = np.zeros((H * 2, W * 2, 3), np.float32)
    xs, ys = rng.integers(0, W * 2, n * 4), rng.integers(0, H * 2, n * 4)
    b = rng.power(6, n * 4) * 0.9 + 0.1
    tint = rng.choice([[1, 1, 1], [0.85, 0.9, 1.0], [1.0, 0.92, 0.82]], n * 4)
    img[ys, xs] = (b[:, None] * tint * 255)
    img = cv2.GaussianBlur(img, (0, 0), 0.6) * 1.6
    return np.clip(img, 0, 255)


def draw_sphere(frame, cx, cy, r, tex, spin_deg, light, emissive, alpha_mul):
    H, W = frame.shape[:2]
    if r < 0.8:
        if 0 <= cx < W and 0 <= cy < H:
            c = tex.reshape(-1, 3).mean(axis=0) * alpha_mul
            cv2.circle(frame, (int(cx), int(cy)), 1, tuple(float(x) for x in c), -1, cv2.LINE_AA)
        return
    x0, x1 = int(max(math.floor(cx - r - 2), 0)), int(min(math.ceil(cx + r + 2), W))
    y0, y1 = int(max(math.floor(cy - r - 2), 0)), int(min(math.ceil(cy + r + 2), H))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx, ny = (xx + 0.5 - cx) / r, (yy + 0.5 - cy) / r
    rr = nx * nx + ny * ny
    edge = np.clip((1.0 - np.sqrt(rr)) * r + 0.5, 0, 1)
    inside = edge > 0
    if not inside.any():
        return
    nz = np.sqrt(np.clip(1.0 - rr, 0, 1))
    lon = np.arctan2(nx, nz) + math.radians(spin_deg)
    lat = np.arcsin(np.clip(-ny, -1, 1))
    th, tw = tex.shape[:2]
    u = ((lon / (2 * math.pi) + 0.5) % 1.0) * (tw - 1)
    v = (0.5 - lat / math.pi) * (th - 1)
    col = cv2.remap(tex, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_WRAP).astype(np.float32)
    if emissive:
        shade = (0.55 + 0.45 * nz ** 0.6)[..., None] * 1.25          # limb darkening
    else:
        L = np.array([light[0], -light[1], 0.35], np.float32)
        L /= np.linalg.norm(L)
        d = nx * L[0] + ny * L[1] + nz * L[2]
        shade = (np.clip(d, 0, 1) ** 0.8 * 1.05 + 0.03)[..., None]
    a = (edge * alpha_mul)[..., None]
    region = frame[y0:y1, x0:x1]
    region[:] = region * (1 - a) + np.clip(col * shade, 0, 255) * a


def draw_glow(frame, cx, cy, r, strength, color=(255, 200, 120)):
    if strength <= 0 or r <= 0:
        return
    H, W = frame.shape[:2]
    R = r * 1.6 + 40 + (160 if r < 3 else 0)
    x0, x1 = int(max(cx - R, 0)), int(min(cx + R, W))
    y0, y1 = int(max(cy - R, 0)), int(min(cy + R, H))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    g = np.clip(1 - (d - r) / (R - r), 0, 1) ** 2.2 * (d > r * 0.98)
    frame[y0:y1, x0:x1] += g[..., None] * np.array(color, np.float32) * strength


def text_block(draw, x, y, lines, W, H, align="left", alpha=1.0, anchor="top"):
    """lines = [(text, size, colour, bold)]; keeps the block inside the frame. anchor="bottom": y is the block's bottom edge."""
    if alpha <= 0:
        return
    dims = [draw.textbbox((0, 0), t, font=font(s, b)) for t, s, c, b in lines]
    bw = max(d[2] - d[0] for d in dims)
    adv = [int(s * 1.22) for t, s, c, b in lines]          # line advance from the font size, not the glyph box
    bh = sum(adv)
    if align == "center":
        x -= bw / 2
    if anchor == "bottom":
        y -= bh
    x = min(max(x, 40), W - bw - 40)
    y = min(max(y, 40), H - bh - 40)
    cy = y
    for (t, s, c, b), d, a_ in zip(lines, dims, adv):
        lx = x + (bw - (d[2] - d[0])) / 2 if align == "center" else x
        col = tuple(int(v * alpha) for v in c)
        draw.text((lx + 2, cy + 2 - d[1]), t, font=font(s, b), fill=(0, 0, 0))
        draw.text((lx, cy - d[1]), t, font=font(s, b), fill=col)
        cy += a_
    return


def arrow(img, p0, p1, color, thick, alpha):
    if alpha <= 0:
        return
    c = tuple(float(v * alpha) for v in color)
    p0, p1 = tuple(int(v) for v in p0), tuple(int(v) for v in p1)
    cv2.line(img, p0, p1, c, thick, cv2.LINE_AA)
    for a, b in ((p0, p1), (p1, p0)):
        d = np.array(b, float) - np.array(a, float)
        if np.linalg.norm(d) < 1:
            continue
        d /= np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        tip = np.array(a, float)
        pts = np.array([tip, tip + d * 22 + n * 11, tip + d * 22 - n * 11], np.int32)
        cv2.fillConvexPoly(img, pts, c, cv2.LINE_AA)


def fmt_clock(v, mode):
    if mode == "ms":
        m, s = divmod(max(v, 0), 60)
        return f"{int(m)} min {int(s):02d} s"
    if mode == "years":
        return f"{v:.1f} years"
    return f"{v:.2f} s"


COLORS = {"yellow": YELLOW, "white": WHITE, "cyan": CYAN}


def draw_ocean(frame, u, spec_b, seed):
    H, W = frame.shape[:2]
    d0, d1 = spec_b.get("depth", [0.0, 0.6])
    depth = d0 + (d1 - d0) * u                                   # 0 = sunlit surface, 1 = black
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    d = np.clip(depth + yy * 0.5, 0, 1)                          # deeper toward the bottom of the frame
    top = np.array([40, 130, 200], np.float32); deep = np.array([2, 6, 14], np.float32)
    col = deep + (top - deep) * (np.clip(1 - d * 1.4, 0, 1) ** 1.6)[..., None]
    frame[:] = np.repeat(col, W, axis=1)
    rng = np.random.default_rng(seed)
    for k in range(7):                                           # light rays that fade with depth
        x0 = rng.uniform(0.1, 0.9) * W; w = rng.uniform(40, 120); sw = rng.uniform(-0.25, 0.25) * W
        a = np.clip(1.0 - depth * 1.7, 0, 1) * 0.16
        if a > 0:
            pts = np.array([[x0 - w, 0], [x0 + w, 0], [x0 + sw + w * 3, H], [x0 + sw - w * 3, H]], np.int32)
            ray = np.zeros_like(frame); cv2.fillConvexPoly(ray, pts, (170, 220, 255), cv2.LINE_AA)
            frame += cv2.GaussianBlur(ray, (0, 0), 18) * a
    n = 160                                                      # marine snow rising as we sink
    xs = rng.uniform(0, W, n); ys0 = rng.uniform(0, H, n); sp = rng.uniform(0.5, 1.5, n)
    for x, y0, v in zip(xs, ys0, sp):
        y = (y0 - u * H * 1.6 * v) % H
        cv2.circle(frame, (int(x), int(y)), 1 + int(v > 1.2), (170, 190, 205), -1, cv2.LINE_AA)
    if spec_b.get("vent_glow") and u > spec_b["vent_glow"]:      # warm glow far below: where the vents are
        g = float(np.clip((u - spec_b["vent_glow"]) / 0.4, 0, 1))
        draw_glow(frame, W * 0.5, H * 1.05, 2, 0.9 * g, (255, 120, 40))


def draw_zigzag(frame, cx, cy, R, u, zz):
    t0, t1 = zz.get("t", [0.1, 0.9]); p = float(np.clip((u - t0) / max(t1 - t0, 1e-3), 0, 1))
    rng = np.random.default_rng(zz.get("seed", 1)); n = int(zz.get("steps", 40))
    ang = rng.uniform(0, 2 * math.pi, n); r = np.cumsum(rng.uniform(0.2, 1.0, n))
    pts = [(cx, cy)]; pos = np.zeros(2)
    for i in range(n):
        step = rng.uniform(0.15, 0.4) * R * (0.5 + 0.5 * i / n)
        pos = pos + step * np.array([math.cos(ang[i]), math.sin(ang[i])])
        pos *= min(1.0, 0.98 * R / max(np.linalg.norm(pos), 1e-6)) if np.linalg.norm(pos) > 0.96 * R else 1.0
        pts.append((cx + pos[0], cy + pos[1]))
    pts[-1] = (cx + R * 0.97, cy - R * 0.2)
    k = max(2, int(len(pts) * p))
    arr = np.array(pts[:k], np.int32).reshape(-1, 1, 2)
    glow = np.zeros_like(frame); cv2.polylines(glow, [arr], False, (255, 255, 220), 7, cv2.LINE_AA)
    frame += cv2.GaussianBlur(glow, (0, 0), 6) * 1.2
    cv2.polylines(frame, [arr], False, (255, 255, 245), 3, cv2.LINE_AA)


def round_box(draw, x, y, w, h, fill, outline):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=int(h * 0.3), fill=fill, outline=outline, width=3)


def render_frame(spec, base, t, dur, W, H, stars):
    u = t / dur if dur > 0 else 0
    view = spec["view"]
    cxk = lin(view["center_km"], u)
    w0, w1 = (view["width_km"] if isinstance(view["width_km"], list) else [view["width_km"]] * 2)[0], \
             (view["width_km"] if isinstance(view["width_km"], list) else [view["width_km"]] * 2)[-1]
    wk = w0 * (w1 / w0) ** u                       # constant-ratio zoom
    cyk = lin(view.get("y_km", 0), u)
    sc = W / wk                                     # px per km
    X = lambda xk: W / 2 + (xk - cxk) * sc
    Y = lambda yk: H / 2 - (yk - cyk) * sc

    # stars drift slowly and steadily (never a still frame)
    dx = int((u * 60) % W)
    frame = stars[H // 2:H // 2 + H, W // 2 - dx:W // 2 - dx + W].copy()
    if spec.get("backdrop", {}).get("type") == "ocean":
        draw_ocean(frame, u, spec["backdrop"], spec.get("seed", 3))
    light = spec.get("light", [-0.8, -0.25])

    labels = []
    for b in spec.get("bodies", []):
        a = fade(b.get("at", 0), t, dur)
        for wnd in b.get("dim", []):               # dim = fade to dark (the Sun switching off)
            a *= 1 - float(np.clip((u - wnd[0]) / max(wnd[1] - wnd[0], 1e-3), 0, 1))
        tex = load_texture(base, b.get("texture"), b.get("tint"), spec.get("seed", 3), b.get("recolor", False))
        r = b["diameter_km"] / 2 * sc
        for k in range(int(b.get("repeat", 1))):
            xk = b.get("x_km", 0) + k * b.get("step_km", 0)
            cx, cy = X(xk), Y(b.get("y_km", 0))
            draw_glow(frame, cx, cy, r, b.get("glow", 0) * a, tuple(b.get("glow_color", (255, 200, 120))))
            draw_sphere(frame, cx, cy, r, tex, lin(b.get("spin", 0), u), light, b.get("emissive", False),
                        a * (0.45 if b.get("ghost") else 1.0))
        if b.get("name") and b.get("label", True) is not False:
            la = fade(b.get("label_at", b.get("at", 0)), t, dur) * (a if b.get("dim") else 1)
            if b.get("label_xy"):
                labels.append((b["label_xy"][0] * W, b["label_xy"][1] * H, b, la, -1))
            else:
                labels.append((X(b.get("x_km", 0)), Y(b.get("y_km", 0)) - r, b, la, r))

    # beams (light travelling) before text so labels stay on top
    beams = list(spec.get("beams", [])) + ([spec["beam"]] if spec.get("beam") else [])
    beam_txts = []
    for bm in beams:
        t0, t1 = bm.get("t", [0.1, 0.9])
        p = float(np.clip((u - t0) / max(t1 - t0, 1e-3), 0, 1))
        stop = bm.get("stop_at")
        tail = 0.0 if stop is None else float(np.clip((u - stop) / max(1 - stop, 1e-3), 0, 1))
        xa, xb = X(bm["from_km"]), X(bm["to_km"])
        yb = H / 2 + bm.get("y_frac", 0.0) * H
        head = xa + (xb - xa) * p
        start = xa + (xb - xa) * tail
        if u >= t0 and abs(head - start) > 1 and (tail < 1):
            glow = np.zeros_like(frame)
            cv2.line(glow, (int(start), int(yb)), (int(head), int(yb)), (255, 230, 160), 9, cv2.LINE_AA)
            glow = cv2.GaussianBlur(glow, (0, 0), 7)
            frame += glow * 1.4
            cv2.line(frame, (int(start), int(yb)), (int(head), int(yb)), (255, 248, 225), 3, cv2.LINE_AA)
            if tail == 0:
                cv2.circle(frame, (int(head), int(yb)), 7, (255, 255, 240), -1, cv2.LINE_AA)
        if bm.get("text"):
            clock = bm.get("clock")
            sub = fmt_clock(lin(clock, p), bm.get("clock_fmt", "s")) if clock else None
            beam_txts.append(((xa + xb) / 2, yb + 34, bm["text"], sub, fade(t0, t, dur)))
    for fl in spec.get("flares", []):
        draw_glow(frame, X(fl["x_km"]), Y(fl.get("y_km", 0)), 1, fl.get("strength", 1.0) * 1.6, (255, 225, 170))
    zz = spec.get("zigzag")
    if zz:
        draw_zigzag(frame, X(zz.get("x_km", 0)), Y(zz.get("y_km", 0)), zz["radius_km"] * sc, u, zz)
    for st in spec.get("stars", []):
        a_ = fade(st.get("at", 0), t, dur)
        sx, sy = st["x_frac"] * W, st["y_frac"] * H
        col = tuple(st.get("color", [255, 245, 230]))
        draw_glow(frame, sx, sy, st.get("size", 5), 1.2 * a_, col)
        cv2.circle(frame, (int(sx), int(sy)), int(st.get("size", 5)), tuple(float(c * a_) for c in col), -1, cv2.LINE_AA)

    for rp in [spec["ripples"]] if spec.get("ripples") else []:
        t0, t1 = rp.get("t", [0.2, 0.9])
        cx, cy = X(rp.get("x_km", 0)), H / 2
        for k in range(int(rp.get("count", 3))):
            ph = (u - t0) / max(t1 - t0, 1e-3) - k / rp.get("count", 3)
            if 0 < ph < 1:
                rad = int(40 + ph * W * 0.7)
                col = tuple(float(v * (1 - ph) * 0.7) for v in CYAN)
                if rp.get("dashed", True):
                    for ang in range(0, 360, 8):
                        cv2.ellipse(frame, (int(cx), int(cy)), (rad, rad), 0, ang, ang + 4, col, 2, cv2.LINE_AA)
                else:
                    cv2.circle(frame, (int(cx), int(cy)), rad, col, 2, cv2.LINE_AA)

    arrow_txt = []
    for ar in spec.get("arrows", []):
        a = fade(ar.get("at", 0.1), t, dur)
        ya = H / 2 + ar.get("y_frac", 0.22) * H
        xa, xb = X(ar["from_km"]), X(ar["to_km"])
        arrow(frame, (xa, ya), (xb, ya), WHITE, 3, a)
        arrow_txt.append(((xa + xb) / 2, ya + 16, ar, a))

    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    big = int(H * 0.058)
    for x, ytop, b, a, r in labels:              # big name, type, size (the reference layout)
        lines = [(b["name"], big, YELLOW, True)]
        if b.get("type"):
            lines.append((f"({b['type']})", int(big * 0.42), WHITE, False))
        if b.get("size"):
            lines.append((b["size"], int(big * 0.72), YELLOW, True))
        if r < 0:
            text_block(d, x, ytop, lines, W, H, align="center", alpha=a)
        else:
            text_block(d, x, ytop - 22, lines, W, H, align="center", alpha=a, anchor="bottom")
    for x, y, ar, a in arrow_txt:
        lines = [(ar["text"], int(H * 0.036), WHITE, True)]
        if ar.get("sub"):
            lines.append((ar["sub"], int(H * 0.026), CYAN, False))
        text_block(d, x, y, lines, W, H, align="center", alpha=a)
    for x, y, txt, sub, a in beam_txts:
        lines = [(txt, int(H * 0.038), WHITE, True)] + ([(sub, int(H * 0.05), YELLOW, True)] if sub else [])
        text_block(d, x, y, lines, W, H, align="center", alpha=a)
    for st in spec.get("stars", []):
        if st.get("label"):
            lines = [(st["label"], int(H * 0.034), WHITE, True)] + ([(st["sub"], int(H * 0.028), YELLOW, True)] if st.get("sub") else [])
            text_block(d, st["x_frac"] * W, st["y_frac"] * H + st.get("size", 5) + 18, lines, W, H, align="center", alpha=fade(st.get("at", 0), t, dur))
    for tx in spec.get("texts", []):
        lines = [(l[0], int(H * l[1]), COLORS.get(l[2], WHITE), True) for l in tx["lines"]]
        text_block(d, tx["x_frac"] * W, tx["y_frac"] * H, lines, W, H, align="center", alpha=fade(tx.get("at", 0), t, dur))
    ck = spec.get("clock")
    if ck:
        c0, c1 = ck.get("t", [0.1, 0.9]); p = float(np.clip((u - c0) / max(c1 - c0, 1e-3), 0, 1))
        lines = ([(ck["label"], int(H * 0.03), WHITE, False)] if ck.get("label") else []) + \
                [(fmt_clock(lin(ck.get("seconds", [0, 500]), p), ck.get("fmt", "ms")), int(H * 0.085), YELLOW, True)]
        text_block(d, ck.get("x_frac", 0.5) * W, ck.get("y_frac", 0.1) * H, lines, W, H, align="center", alpha=fade(c0, t, dur))
    for bb in spec.get("bubbles", []):
        a_ = fade(bb.get("at", 0.1), t, dur)
        if a_ <= 0:
            continue
        f = font(int(H * 0.045), True)
        tb = d.textbbox((0, 0), bb["text"], font=f); w_, h_ = tb[2] - tb[0] + 60, tb[3] - tb[1] + 40
        x_, y_ = bb["x_frac"] * W - w_ / 2, bb["y_frac"] * H - h_ / 2
        round_box(d, x_, y_, w_, h_, (int(30 * a_), int(40 * a_), int(60 * a_)), tuple(int(v * a_) for v in CYAN))
        d.text((x_ + 30, y_ + 20 - tb[1]), bb["text"], font=f, fill=tuple(int(v * a_) for v in WHITE))
    hl = spec.get("headline")
    if hl:
        a = fade(hl.get("at", 0.1), t, dur)
        lines = [(hl["text"], int(H * 0.06), YELLOW, True)] + ([(hl["sub"], int(H * 0.03), WHITE, False)] if hl.get("sub") else [])
        text_block(d, W / 2, H * 0.12, lines, W, H, align="center", alpha=a)
    return np.asarray(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--still", type=float, default=None)
    ap.add_argument("--frames", default=None, help="a:b = render only frames a..b-1 (parallel CI chunks)")
    a = ap.parse_args()
    cfg = load_config()
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    base = spec_path.parent
    W, H = (cfg.get("width", 1920), cfg.get("height", 1080))
    if a.draft:
        W, H = W // 2, H // 2
    fps = cfg.get("fps", 30)
    dur = float(spec["duration"] if spec.get("duration") != "auto" else spec.get("fallback", 8))
    stars = star_field(W, H, spec.get("seed", 3))
    if a.still is not None:
        Image.fromarray(render_frame(spec, base, a.still * dur, dur, W, H, stars)).save(a.out)
        print("still ->", a.out); return
    n = max(int(round(dur * fps)), 1)
    f0, f1 = (int(x) for x in a.frames.split(":")) if a.frames else (0, n)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, min(f1, n)):
        proc.stdin.write(render_frame(spec, base, i / fps, dur, W, H, stars).tobytes())
    proc.stdin.close()
    if proc.wait():
        sys.exit("ffmpeg failed")
    print(f"{min(f1, n) - f0} frames -> {a.out}")


if __name__ == "__main__":
    main()
