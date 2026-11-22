#!/usr/bin/env python3
"""3D space fly-through renderer (CPU, numpy + OpenCV). No generative AI: every surface is a real map texture.

A perspective camera moves at constant speed along a smooth path through a scene of:
  - textured spheres (NASA/Cassini global maps), lit by the Sun, with soft edges
  - planetary rings (radial colour/alpha strip) with the planet's shadow on the rings and the rings' shadow on the planet
  - a 3D star field (stars at real 3D positions, so near/far parallax is true when the camera moves)
  - optional plume particles (jets from the south polar region, bright when backlit)
  - sun glare when the Sun is in view, bloom on bright areas
This is OUR visualization: label it OUR_CGI ("Illustration / simulation").

Usage: space3d.py spec.json out.mp4 [--draft] [--frames a:b]   (a:b = one chunk, for parallel rendering)
       space3d.py spec.json still.png --still 0.5        (one frame at 50 % of the clip, for previews)

spec = {
  "duration": 9, "fov": 45, "motion": "linear", "seed": 3,
  "sun": [-0.4, 0.15, -0.9],                         # world direction pointing TO the Sun
  "stars": {"count": 9000, "near": 3000, "far": 30000},
  "camera": {"pos": [[x,y,z], ...], "target": [[x,y,z], ...], "up": [0,1,0], "roll": [0, 3]},
  "bodies": [{"texture": "../saturn.jpg", "center": [0,0,0], "radius": 58.2, "tilt": 0, "spin": [0, 2],
              "rings": {"texture": "../saturn_ring.png", "inner": 1.24, "outer": 2.27},
              "plumes": {"count": 40000, "height": 1.6, "jets": 60, "seed": 4}}]}
Units are free (we use 1000 km). Keyframe lists are spread evenly over the clip and joined with a Catmull-Rom spline.
Texture paths are relative to the spec file."""
import json, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import load_config

cv2.setNumThreads(0)
F32 = np.float32


def norm(v):
    v = np.asarray(v, np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


def spline(keys, u):
    P = np.asarray(keys, np.float64)
    if P.ndim == 0:
        return float(P)
    if P.ndim == 1 and not isinstance(keys[0], (list, tuple)):
        P = P[:, None]
        return float(spline(P.tolist(), u)[0])
    n = len(P)
    if n == 1:
        return P[0]
    seg = min(max(u, 0.0), 1.0) * (n - 1)
    i = min(int(seg), n - 2)
    t = seg - i
    p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def scalar(v, u):
    if isinstance(v, (list, tuple)):
        return float(spline([[x] for x in v], u)[0])
    return float(v)


def rot_x(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


class Camera:
    def __init__(self, spec, W, H, u):
        c = spec["camera"]
        self.pos = spline(c["pos"], u)
        tgt = spline(c["target"], u)
        f = norm(tgt - self.pos)
        up = norm(c.get("up", [0, 1, 0]))
        r = np.cross(f, up)
        if np.linalg.norm(r) < 1e-6:
            r = np.cross(f, [0, 0, 1])
        r = norm(r)
        up = np.cross(r, f)
        roll = np.radians(scalar(c.get("roll", 0), u))
        r, up = r * np.cos(roll) + up * np.sin(roll), up * np.cos(roll) - r * np.sin(roll)
        self.B = np.stack([r, up, f], axis=1)        # columns: camera axes in world coordinates
        self.W, self.H = W, H
        self.fpx = (W / 2) / np.tan(np.radians(spec.get("fov", 45)) / 2)

    def to_cam(self, p):
        return (np.asarray(p, np.float64) - self.pos) @ self.B

    def dir_to_cam(self, d):
        return np.asarray(d, np.float64) @ self.B


def splat(layer, xs, ys, vals):
    """Additive bilinear splat of points (vals: N x 3) into layer (H x W x 3)."""
    H, W = layer.shape[:2]
    x0 = np.floor(xs).astype(np.int64); y0 = np.floor(ys).astype(np.int64)
    fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + dx, y0 + dy
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        np.add.at(layer, (yi[ok], xi[ok]), (vals[ok] * w[ok]).astype(F32))


class Stars:
    def __init__(self, spec, seed):
        s = spec.get("stars") or {}
        n = int(s.get("count", 0))
        rng = np.random.default_rng(seed)
        d = rng.standard_normal((n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        dist = rng.uniform(s.get("near", 3000), s.get("far", 30000), n)
        self.p = d * dist[:, None]
        mag = rng.random(n) ** 7
        temp = rng.random(n)
        col = np.stack([0.85 + 0.15 * temp, 0.9 + 0.08 * rng.random(n), 1.0 - 0.25 * (1 - temp)], 1)  # BGR, slight tints
        self.v = (col * (0.04 + 1.4 * mag)[:, None] * s.get("brightness", 1.0)).astype(F32)
        self.big = mag > 0.35

    def draw(self, img, cam):
        if len(self.p) == 0:
            return
        q = cam.to_cam(self.p)
        ok = q[:, 2] > 1.0
        q, v, big = q[ok], self.v[ok], self.big[ok]
        xs = cam.W / 2 + cam.fpx * q[:, 0] / q[:, 2] - 0.5
        ys = cam.H / 2 - cam.fpx * q[:, 1] / q[:, 2] - 0.5
        lay = np.zeros_like(img)
        splat(lay, xs, ys, v)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.6)
        if big.any():
            g = np.zeros_like(img)
            splat(g, xs[big], ys[big], v[big] * 0.6)
            lay += cv2.GaussianBlur(g, (0, 0), 2.2)
        img += lay


def load_texture(path):
    if isinstance(path, (list, tuple)):          # candidates: first one that exists
        found = [q for q in path if Path(q).exists()]
        if not found:
            raise SystemExit(f"none of these textures exist: {[str(q) for q in path]}")
        path = found[0]
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise SystemExit(f"cannot read texture {path}")
    return im


class Body:
    def __init__(self, b, base, seed):
        self.b = b
        tex = load_texture(self._paths(base, b["texture"]))
        if tex.ndim == 2:
            tex = cv2.cvtColor(tex, cv2.COLOR_GRAY2BGR)
        self.full = tex[..., :3].astype(F32) / 255.0
        self.cache = {}
        self.R = float(b["radius"])
        self.C = np.asarray(b["center"], np.float64)
        self.ring = None
        if b.get("rings"):
            rg = b["rings"]
            rt = load_texture(self._paths(base, rg["texture"]))
            # one radial profile: average the strip's rows (inner edge on the left)
            if rt.ndim == 2:
                rt = cv2.cvtColor(rt, cv2.COLOR_GRAY2BGRA)
            if rt.shape[2] == 3:
                a = cv2.cvtColor(rt, cv2.COLOR_BGR2GRAY)
                rt = np.dstack([rt, a])
            prof = rt.astype(F32).mean(axis=0) / 255.0                   # (N, 4) BGRA
            if prof.shape[0] < 16:
                prof = rt.astype(F32).mean(axis=1) / 255.0
            self.ring = (prof[:, :3], prof[:, 3] * float(rg.get("opacity", 1.0)), float(rg["inner"]), float(rg["outer"]))
            a = prof[:, 3]; k = len(a)
            print(f"  ring texture {rt.shape[1]}x{rt.shape[0]}, alpha profile (10 bins): "
                  + " ".join(f"{a[int(i * k / 10):int((i + 1) * k / 10)].mean():.2f}" for i in range(10)), flush=True)
        self.plumes = None
        if b.get("plumes"):
            self.plumes = self._make_plumes(b["plumes"], seed)

    @staticmethod
    def _paths(base, t):
        return [base / x for x in t] if isinstance(t, list) else base / t

    def _make_plumes(self, p, seed):
        rng = np.random.default_rng(p.get("seed", seed))
        jets = int(p.get("jets", 60)); n = int(p.get("count", 40000))
        # jet sources along four 'tiger stripe' arcs around the south pole (body frame: +y is north)
        stripe = rng.integers(0, 4, jets)
        lon = np.radians(rng.uniform(-60, 60, jets) + stripe * 8 - 12)
        lat = np.radians(-90 + 8 + stripe * 5 + rng.normal(0, 1.2, jets))
        base = np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)], 1)
        tilt = rng.normal(0, 0.12, (jets, 3))
        dirs = base + tilt; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        j = rng.integers(0, jets, n)
        s0 = rng.random(n)                                   # position along the jet, 0..1 of max height
        side = rng.standard_normal((n, 3))
        strength = rng.uniform(0.4, 1.0, jets)[j]
        return dict(base=base[j], dirs=dirs[j], s0=s0, side=side, strength=strength,
                    hmax=float(p.get("height", 1.6)), speed=float(p.get("speed", 0.05)),
                    gain=float(p.get("brightness", 1.0)))

    def orient(self, u):
        spin = scalar(self.b.get("spin", 0), u)
        return rot_x(self.b.get("tilt", 0)) @ rot_y(spin)    # body -> world

    def tex(self, size_px):
        want = int(min(self.full.shape[1], max(512, 2.2 * np.pi * size_px)))
        key = min(1 << int(np.ceil(np.log2(want))), self.full.shape[1])
        if key not in self.cache:
            self.cache[key] = cv2.resize(self.full, (key, max(2, key // 2)), interpolation=cv2.INTER_AREA)
        return self.cache[key]

    def extent(self):
        e = 1.0
        if self.ring:
            e = max(e, self.ring[3])
        if self.plumes:
            e = max(e, 1 + self.plumes["hmax"])
        return self.R * e * 1.02

    _dirs = None

    def bbox(self, cam):
        """Screen box of the body's bounding sphere, found by projecting points on it (exact under perspective)."""
        if Body._dirs is None:
            k = np.arange(400) + 0.5
            phi = np.arccos(1 - 2 * k / 400); th = np.pi * (1 + 5 ** 0.5) * k
            Body._dirs = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
        Rx = self.extent()
        W, H = cam.W, cam.H
        C = cam.to_cam(self.C)
        if np.linalg.norm(C) <= Rx * 1.05:
            return (0, W, 0, H)
        pts = C + Body._dirs * Rx
        if (pts[:, 2] <= 1e-3).any():
            if C[2] < -Rx:
                return None
            return (0, W, 0, H)
        xs = W / 2 + cam.fpx * pts[:, 0] / pts[:, 2]; ys = H / 2 - cam.fpx * pts[:, 1] / pts[:, 2]
        m = 0.03 * (xs.max() - xs.min()) + 4
        x0, x1 = int(max(0, xs.min() - m)), int(min(W, xs.max() + m + 1))
        y0, y1 = int(max(0, ys.min() - m)), int(min(H, ys.max() + m + 1))
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, x1, y0, y1)

    def draw(self, img, cam, u, t, sun_w):
        bb = self.bbox(cam)
        if bb is None:
            return
        x0, x1, y0, y1 = bb
        Cc = cam.to_cam(self.C).astype(F32)
        R = F32(self.R)
        Mb = self.orient(u)
        K = (Mb.T @ cam.B).astype(F32)                 # camera -> body frame
        sun = cam.dir_to_cam(sun_w).astype(F32)
        axis = cam.dir_to_cam(Mb @ np.array([0, 1, 0])).astype(F32)
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(F32)
        xn = (xs + 0.5 - cam.W / 2) / F32(cam.fpx)
        yn = -(ys + 0.5 - cam.H / 2) / F32(cam.fpx)
        L = np.sqrt(xn * xn + yn * yn + 1)
        dx, dy, dz = xn / L, yn / L, 1 / L
        roi = img[y0:y1, x0:x1]

        # sphere
        b = dx * Cc[0] + dy * Cc[1] + dz * Cc[2]
        h2 = np.maximum(float(Cc @ Cc) - b * b, 0)
        h = np.sqrt(h2)
        bpos = np.maximum(b, 1e-6)
        cov = np.clip((R - h) / (bpos / F32(cam.fpx)) + 0.5, 0, 1) * (b > 0)
        thit = b - np.sqrt(np.maximum(R * R - h2, 0))
        nx = (thit * dx - Cc[0]) / R; ny = (thit * dy - Cc[1]) / R; nz = (thit * dz - Cc[2]) / R
        nn = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        nx, ny, nz = nx / nn, ny / nn, nz / nn
        sphere_any = bool((cov > 0).any())
        if sphere_any:
            bx = K[0, 0] * nx + K[0, 1] * ny + K[0, 2] * nz
            by = K[1, 0] * nx + K[1, 1] * ny + K[1, 2] * nz
            bz = K[2, 0] * nx + K[2, 1] * ny + K[2, 2] * nz
            la = np.arcsin(np.clip(by, -1, 1)); lo = np.arctan2(bx, bz)
            size_px = float(cam.fpx * self.R / max(np.linalg.norm(Cc), 1e-6))
            tex = self.tex(size_px)
            th, tw = tex.shape[:2]
            mapx = ((lo / (2 * np.pi) + 0.5) * tw - 0.5).astype(F32)
            mapy = np.clip((0.5 - la / np.pi) * th - 0.5, 0, th - 1).astype(F32)
            col = cv2.remap(tex, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            lam = nx * sun[0] + ny * sun[1] + nz * sun[2]
            day = np.clip(lam * 1.08 + 0.04, 0, 1) ** 0.85
            if self.ring:
                # shadow of the rings on the planet
                Px, Py, Pz = nx * R, ny * R, nz * R
                pa = Px * axis[0] + Py * axis[1] + Pz * axis[2]
                sa = float(sun @ axis)
                if abs(sa) > 1e-4:
                    tr = -pa / sa
                    qx, qy, qz = Px + tr * sun[0], Py + tr * sun[1], Pz + tr * sun[2]
                    rq = np.sqrt(qx * qx + qy * qy + qz * qz) / R
                    a = self.ring_alpha(rq) * (tr > 0)
                    day = day * (1 - 0.85 * a)
            shade = (0.012 + day)[..., None]
            body = col * shade

        # rings
        ring_front = ring_back = None
        if self.ring:
            rc, ra, inner, outer = self.ring
            den = dx * axis[0] + dy * axis[1] + dz * axis[2]
            den = np.where(np.abs(den) < 1e-6, F32(1e-6), den)
            tr = float(Cc @ axis) / den
            qx, qy, qz = tr * dx - Cc[0], tr * dy - Cc[1], tr * dz - Cc[2]
            rr = np.sqrt(qx * qx + qy * qy + qz * qz) / R
            vis = (tr > 0) & (rr > inner) & (rr < outer)
            if vis.any():
                s = np.clip((rr - inner) / (outer - inner), 0, 1) * (len(ra) - 1)
                i0 = np.floor(s).astype(np.int32); i1 = np.minimum(i0 + 1, len(ra) - 1); f = (s - i0)[..., None]
                rcol = rc[i0] * (1 - f) + rc[i1] * f
                ralpha = (ra[i0] * (1 - f[..., 0]) + ra[i1] * f[..., 0]) * vis
                sa = float(sun @ axis)
                cam_side = np.sign(-float(Cc @ axis)) or 1.0
                lit = 0.22 + 0.78 * abs(sa) ** 0.35
                if np.sign(sa) != cam_side:          # looking at the unlit face: only light that leaks through thin parts
                    lit_map = (0.08 + 0.9 * (1 - ralpha)) * lit
                else:
                    lit_map = np.full_like(ralpha, lit)
                # planet shadow on the rings
                qs = qx * sun[0] + qy * sun[1] + qz * sun[2]
                perp = np.sqrt(np.maximum(qx * qx + qy * qy + qz * qz - qs * qs, 0))
                shadow = np.where(qs < 0, np.clip((perp - R) / (0.02 * R), 0, 1), 1.0)
                rcol = rcol * (lit_map * (0.04 + 0.96 * shadow))[..., None]
                front = vis & ((cov <= 0) | (tr < thit))
                ring_front = (rcol, ralpha * front)
                ring_back = (rcol, ralpha * (vis & ~front))
        if ring_back is not None:
            a = ring_back[1][..., None]
            roi[:] = roi * (1 - a) + ring_back[0] * a
        if sphere_any:
            c = cov[..., None]
            roi[:] = roi * (1 - c) + body * c
        if self.b.get("atmosphere") and b.max() > 0:
            # thin limb glow, much stronger when the Sun is behind the planet (forward scattering)
            atm = np.asarray(self.b["atmosphere"], F32)[::-1]
            fwd = np.clip(dx * sun[0] + dy * sun[1] + dz * sun[2], 0, 1)
            width = F32(self.b.get("atmosphere_width", 0.012)) * R
            outside = np.exp(-np.maximum(h - R, 0) / width) * (h > R)
            # which part of the limb faces the Sun (screen-space)
            lx, ly = (thit * dx - Cc[0]), (thit * dy - Cc[1])
            ln = np.sqrt(lx * lx + ly * ly) + 1e-6
            side = np.clip((lx * sun[0] + ly * sun[1]) / ln * 0.7 + 0.45, 0, 1)
            g = outside * (0.15 * side + 1.6 * fwd ** 6) * (b > 0)
            roi[:] = roi + g[..., None] * atm
        if ring_front is not None:
            a = ring_front[1][..., None]
            roi[:] = roi * (1 - a) + ring_front[0] * a
        if self.plumes:
            self.draw_plumes(img, cam, Mb, sun, t)

    def ring_alpha(self, rq):
        rc, ra, inner, outer = self.ring
        s = np.clip((rq - inner) / (outer - inner), 0, 1) * (len(ra) - 1)
        a = ra[np.round(s).astype(np.int32)]
        return a * ((rq > inner) & (rq < outer))

    def draw_plumes(self, img, cam, Mb, sun, t):
        p = self.plumes
        h = ((p["s0"] + p["speed"] * t) % 1.0) * p["hmax"]                    # height in body radii
        spread = 0.015 + 0.10 * h
        pos_b = p["base"] * self.R + (p["dirs"] * h[:, None] + p["side"] * spread[:, None] * 0.5) * self.R
        pos_w = pos_b @ Mb.T + self.C
        q = cam.to_cam(pos_w)
        ok = q[:, 2] > 0.01
        q = q[ok]
        dist = np.linalg.norm(q, axis=1)
        v = q / dist[:, None]
        # hidden behind the moon?
        Cc = cam.to_cam(self.C)
        b = v @ Cc
        h2 = Cc @ Cc - b * b
        thit = b - np.sqrt(np.maximum(self.R ** 2 - h2, 0))
        hidden = (h2 < self.R ** 2) & (b > 0) & (thit < dist)
        fwd = np.clip(v @ sun, 0, 1)
        bright = (0.06 + 2.4 * fwd ** 4) * np.exp(-h[ok] / (0.45 * p["hmax"])) * p["strength"][ok] * p["gain"]
        bright = bright * ~hidden
        px = cam.fpx / dist
        keep = bright > 1e-4
        xs = cam.W / 2 + cam.fpx * q[keep, 0] / q[keep, 2] - 0.5
        ys = cam.H / 2 - cam.fpx * q[keep, 1] / q[keep, 2] - 0.5
        # scale per-particle energy with on-screen size so density looks the same at any distance
        e = bright[keep] * np.clip(px[keep] * self.R * 0.004, 0.02, 3.0)
        vals = np.stack([e * 1.0, e * 0.95, e * 0.82], 1)                      # BGR: slightly blue-white
        lay = np.zeros_like(img)
        splat(lay, xs, ys, vals)
        # soften with the on-screen size of the moon, so close-ups stay smooth instead of grainy
        size_px = float(cam.fpx * self.R / max(np.linalg.norm(Cc), 1e-6))
        s1 = max(1.2, size_px * 0.012)
        img += cv2.GaussianBlur(lay, (0, 0), s1) * 0.9 + cv2.GaussianBlur(lay, (0, 0), s1 * 5) * 1.6


def sun_glare(img, cam, sun_w, bodies, gain):
    s = cam.dir_to_cam(sun_w)
    if s[2] <= 0.02:
        return
    sx = cam.W / 2 + cam.fpx * s[0] / s[2]; sy = cam.H / 2 - cam.fpx * s[1] / s[2]
    # blocked by a body? (soft: how deep the sun line goes behind the limb, in pixels)
    vis = 1.0
    for bd in bodies:
        Cc = cam.to_cam(bd.C)
        b = float(s @ Cc)
        if b <= 0:
            continue
        h = np.sqrt(max(Cc @ Cc - b * b, 0))
        edge_px = (bd.R - h) * cam.fpx / b
        vis = min(vis, float(np.clip(1 - (edge_px + 3) / 25, 0, 1)))
    if vis <= 0:
        return
    H, W = img.shape[:2]
    ys, xs = np.mgrid[0:H:4, 0:W:4].astype(F32)
    d = np.sqrt((xs - sx) ** 2 + (ys - sy) ** 2) / H
    g = (0.9 * np.exp(-d / 0.015) + 0.25 * np.exp(-d / 0.08) + 0.06 * np.exp(-d / 0.35)) * vis * gain
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    img += np.dstack([g * 0.92, g * 0.97, g * 1.0])


def render_frame(spec, bodies, stars, W, H, u, t):
    cam = Camera(spec, W, H, u)
    img = np.zeros((H, W, 3), F32)
    stars.draw(img, cam)
    sun_w = norm(spec.get("sun", [-0.5, 0.2, 0.8]))
    for bd in sorted(bodies, key=lambda b: -np.linalg.norm(b.C - cam.pos)):
        bd.draw(img, cam, u, t, sun_w)
    if spec.get("sun_glare", 1.0):
        sun_glare(img, cam, sun_w, bodies, float(spec.get("sun_glare", 1.0)))
    bright = np.clip(img - 0.85, 0, None)
    if bright.max() > 0:
        img += cv2.GaussianBlur(bright, (0, 0), 9) * 0.5
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    spec_p, out = Path(sys.argv[1]), sys.argv[2]
    draft = "--draft" in sys.argv
    still = float(sys.argv[sys.argv.index("--still") + 1]) if "--still" in sys.argv else None
    cfg = load_config()
    spec = json.loads(spec_p.read_text())
    base = spec_p.resolve().parent
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    if spec.get("size"):
        W, H = (int(x) for x in spec["size"])
    if draft:
        W, H = W // 2, H // 2
    seed = spec.get("seed", 1)
    stars = Stars(spec, seed)
    bodies = [Body(b, base, seed + i) for i, b in enumerate(spec["bodies"])]
    n = int(round(spec["duration"] * fps))

    def uu(i):
        x = i / max(1, n - 1)
        return x if spec.get("motion", "linear") == "linear" else ease(x)

    if still is not None:
        i = int(round(still * (n - 1)))
        cv2.imwrite(out, render_frame(spec, bodies, stars, W, H, uu(i), i / fps))
        print("wrote", out)
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", out]
    f0, f1 = 0, n
    if "--frames" in sys.argv:
        f0, f1 = (int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(":"))
        f1 = min(f1, n)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(f0, f1):
        enc.stdin.write(render_frame(spec, bodies, stars, W, H, uu(i), i / fps).tobytes())
        if i > f0 and (i - f0) % 60 == 0:
            sp = (i - f0) / (time.time() - t0)
            print(f"  {spec_p.name}: frame {i}/{f1}  {sp:.1f} fps", flush=True)
    enc.stdin.close(); enc.wait()
    if enc.returncode:
        sys.exit("ffmpeg failed")
    print(f"{out}: frames {f0}..{f1 - 1} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
