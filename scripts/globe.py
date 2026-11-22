#!/usr/bin/env python3
"""Render a rotating planet/moon clip from a NASA equirectangular texture (e.g. Blue Marble, LRO CGI Moon Kit).
This is OUR visualization of real map data: label it PROCESSED_DATA or OUR_CGI honestly, never REAL_VIDEO.
Usage: globe.py spec.json out.mp4 [--draft]
spec = {"duration": 6, "seed": 3, "stars": 1200, "sun": [-0.6, 0.25, 0.75],
        "bodies": [{"texture": "assets/earth.jpg", "atmosphere": [0.35, 0.6, 1.0],
                    "center": [[0.5,0.5],[0.45,0.55]], "radius": [0.32, 0.42],   # fractions of frame height
                    "lon": [10, 40], "lat": [15, 18], "roll": 0}]}
Keyframes are [start, end] with smootherstep easing. lon/lat = which surface point faces the camera."""
import json, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import load_config

cv2.setNumThreads(0)


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


def lerp(a, b, e):
    return np.asarray(a, np.float64) + (np.asarray(b, np.float64) - np.asarray(a, np.float64)) * e


def kf(v, e, vec=False):
    """Scalar: 5 (static) or [a, b] (animated). Vector: [x, y] (static) or [[x, y], [x, y]] (animated)."""
    if vec:
        if isinstance(v[0], list):
            return lerp(v[0], v[1], e)
        return np.asarray(v, np.float64)
    if isinstance(v, list):
        if len(v) == 1:
            return float(v[0])
        return float(lerp(v[0], v[1], e))
    return float(v)


def rot(lon, lat, roll):
    lo, la, ro = np.radians([lon, lat, roll])
    Ry = np.array([[np.cos(lo), 0, np.sin(lo)], [0, 1, 0], [-np.sin(lo), 0, np.cos(lo)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(la), -np.sin(la)], [0, np.sin(la), np.cos(la)]])
    Rz = np.array([[np.cos(ro), -np.sin(ro), 0], [np.sin(ro), np.cos(ro), 0], [0, 0, 1]])
    # camera -> body: front of the globe shows (lon, lat); camera 'up' points north
    return Ry @ Rx.T @ Rz.T


class Body:
    def __init__(self, b, base, H):
        self.b = b
        img = cv2.imread(str(base / b["texture"]), cv2.IMREAD_COLOR)
        if img is None:
            raise SystemExit(f"cannot read {b['texture']}")
        self.full = img.astype(np.float32) / 255.0
        self.cache = {}
        self.atm = b.get("atmosphere")

    def tex(self, R):
        # texture width ~ 2.2 x circumference in pixels avoids aliasing without wasting time
        want = int(min(self.full.shape[1], max(512, 2.2 * np.pi * R)))
        key = 1 << int(np.ceil(np.log2(want)))
        key = min(key, self.full.shape[1])
        if key not in self.cache:
            h = max(2, key // 2)
            self.cache[key] = cv2.resize(self.full, (key, h), interpolation=cv2.INTER_AREA)
        return self.cache[key]

    def draw(self, frame, e, W, H, sun):
        b = self.b
        cx, cy = kf(b["center"], e, vec=True)
        R = kf(b["radius"], e) * H
        cx, cy = cx * W, cy * H
        lon = kf(b.get("lon", 0), e); lat = kf(b.get("lat", 0), e); roll = kf(b.get("roll", 0), e)
        pad = R * 0.08 if self.atm else 2
        x0, x1 = int(max(0, cx - R - pad)), int(min(W, cx + R + pad + 1))
        y0, y1 = int(max(0, cy - R - pad)), int(min(H, cy + R + pad + 1))
        if x1 <= x0 or y1 <= y0:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        nx = (xs + 0.5 - cx) / R
        ny = -(ys + 0.5 - cy) / R
        r2 = nx * nx + ny * ny
        inside = r2 <= 1.0
        nz = np.sqrt(np.clip(1 - r2, 0, 1))
        # world normal (camera space) -> body space
        M = rot(lon, lat, roll).astype(np.float32)
        bx = M[0, 0] * nx + M[0, 1] * ny + M[0, 2] * nz
        by = M[1, 0] * nx + M[1, 1] * ny + M[1, 2] * nz
        bz = M[2, 0] * nx + M[2, 1] * ny + M[2, 2] * nz
        la = np.arcsin(np.clip(by, -1, 1))
        lo = np.arctan2(bx, bz)
        tex = self.tex(R)
        th, tw = tex.shape[:2]
        mapx = ((lo / (2 * np.pi) + 0.5) * tw - 0.5).astype(np.float32)
        mapy = ((0.5 - la / np.pi) * th - 0.5).astype(np.float32)
        col = cv2.remap(tex, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        s = np.asarray(sun, np.float32); s /= np.linalg.norm(s)
        lam = nx * s[0] + ny * s[1] + nz * s[2]
        day = np.clip(lam * 1.15 + 0.08, 0, 1) ** 0.9
        shade = (0.025 + 0.975 * day)[..., None]
        out = col * shade
        # anti-aliased edge
        edge = np.clip((1.0 - np.sqrt(r2)) * R + 0.5, 0, 1)[..., None]
        roi = frame[y0:y1, x0:x1]
        roi[:] = roi * (1 - edge) + out * edge
        if self.atm:
            atm = np.asarray(self.atm, np.float32)[::-1]  # RGB -> BGR
            d = np.sqrt(r2)
            lit = np.clip(lam * 0.9 + 0.35, 0, 1)
            inner = np.where(inside, (1 - nz) ** 3 * 0.55, 0)
            outer = np.where(~inside, np.exp(-((d - 1) * R) / (R * 0.025)) * 0.65, 0)
            # light the outer halo by the sun direction in screen space
            ang = (nx * s[0] + ny * s[1]) / np.maximum(d, 1e-6)
            outer = outer * np.clip(ang * 0.8 + 0.35, 0, 1)
            glow = (inner * lit + outer)[..., None] * atm
            roi[:] = roi + glow
        frame[y0:y1, x0:x1] = roi


def stars(W, H, n, seed):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 3), np.float32)
    xs = rng.uniform(0, W, n); ys = rng.uniform(0, H, n)
    mag = rng.random(n) ** 6
    for x, y, m in zip(xs, ys, mag):
        b = 0.15 + 0.85 * m
        tint = np.array([1.0, 0.95 + 0.05 * rng.random(), 0.85 + 0.15 * rng.random()], np.float32)
        r = 1 if m < 0.9 else 2
        cv2.circle(img, (int(x), int(y)), r, (tint * b).tolist(), -1, lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(img, (0, 0), 0.6)


def main():
    spec_p, out = Path(sys.argv[1]), sys.argv[2]
    draft = "--draft" in sys.argv
    cfg = load_config()
    spec = json.loads(spec_p.read_text())
    base = spec_p.resolve().parent
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    if draft:
        W, H = W // 2, H // 2
    n = int(round(spec["duration"] * fps))
    bg = stars(W, H, spec.get("stars", 0), spec.get("seed", 1)) if spec.get("stars") else np.zeros((H, W, 3), np.float32)
    bodies = [Body(b, base, H) for b in spec["bodies"]]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    drift = spec.get("star_drift", [0, 0])
    for i in range(n):
        u = i / max(1, n - 1)
        e = u if spec.get("motion") == "linear" else ease(u)
        dx, dy = drift[0] * W * e, drift[1] * H * e
        f = cv2.warpAffine(bg, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_WRAP) if (dx or dy) else bg.copy()
        for b in bodies:
            b.draw(f, e, W, H, spec.get("sun", [-0.6, 0.25, 0.75]))
        enc.stdin.write((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()
    print(f"{out}: {n} frames in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
