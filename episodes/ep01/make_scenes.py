"""Writes the EP01 3D scene specs (assets/space3d/*.json).
Units: 1 = 1,000 km. Saturn at the origin, Enceladus at (238, 0, 0), +y is north.
Every spec has "fit": true, so ci/run.py stretches it to the voice-over length of the shots that use it.
Run: python episodes/ep01/make_scenes.py [out_dir]"""
import json, sys
from pathlib import Path
import numpy as np

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "assets" / "space3d"
E = np.array([238.0, 0.0, 0.0])
SUN = np.array([-0.85, -0.3, 0.45]); SUN /= np.linalg.norm(SUN)

SATURN = {"texture": ["../SAT8.jpg", "../SAT2.jpg"], "center": [0, 0, 0], "radius": 58.2, "tilt": 0, "spin": [0, 2],
          "rings": {"texture": ["../originals/RING8.png", "../originals/RING2.png"], "inner": 1.22, "outer": 2.41},
          "atmosphere": [1.0, 0.85, 0.6]}


def enc(brightness=0.3, spin=(180, 186), count=120000):
    return {"texture": "../T003.jpg", "center": E.tolist(), "radius": 0.252, "spin": list(spin),
            "plumes": {"count": count, "height": 1.6, "jets": 60, "seed": 4, "brightness": brightness}}


def r3(v):
    return [round(float(x), 3) for x in v]


def spec(pos, target, dur, roll=(0, 0), bodies=None, seed=3, fov=40, extra=None):
    s = {"duration": dur, "fit": True, "fallback": dur, "fov": fov, "seed": seed, "motion": "linear",
         "sun": SUN.round(4).tolist(), "stars": {"count": 12000, "near": 3000, "far": 30000},
         "camera": {"pos": [r3(p) for p in pos], "target": [r3(t) for t in target], "roll": list(roll)},
         "bodies": bodies or [SATURN, enc()]}
    if extra:
        s.update(extra)
    return s


def around(center, d, az, el):
    """point at distance d from center; az around +y (0 = toward -x i.e. toward Saturn), el above the equator"""
    az, el = np.radians(az), np.radians(el)
    return center + d * np.array([-np.cos(el) * np.cos(az), np.sin(el), np.cos(el) * np.sin(az)])


S = {}
# 1-2  approach to Saturn (as trial s1)
S["a_saturn_approach"] = spec([[265, -118, 513], [212, -90, 420], [160, -60, 330]], [[0, 0, 0], [8, 0, 0], [15, 0, 0]], 14, (0, -4))
# 3  approach to Enceladus (trial s2), plumes faint
S["b_enc_approach"] = spec([[244.0, -0.9, -2.2], [242.2, -0.85, -1.6], [240.6, -0.75, -1.1]],
                           [[238, -0.05, 0], [238, -0.12, 0], [238, -0.2, 0]], 8, (2, -2), [SATURN, enc(0.12)])
# 4  south pole, jets backlit: camera on the night side, Sun behind the moon
night = -SUN
S["c_jets_backlit"] = spec([E + 2.8 * night + [0, -0.3, 0], E + 2.4 * night + [0, -0.33, 0], E + 2.0 * night + [0, -0.36, 0]],
                           [E + [0, -0.3, 0], E + [0, -0.33, 0], E + [0, -0.36, 0]], 8, (-2, 2), [SATURN, enc(0.06)])
# Saturn hides the Sun: camera in Saturn's shadow, rings lit from behind (three variants)
for k, (d0, d1, up, rl) in {"d_saturn_eclipse": (330, 300, 40, (0, 3)), "d_saturn_eclipse2": (420, 390, -30, (2, -2)),
                            "d_saturn_eclipse3": (360, 335, 70, (-3, 0))}.items():
    side = np.cross(night, [0, 1, 0]); side /= np.linalg.norm(side)
    p0 = night * d0 + side * 40 + [0, up, 0]
    p1 = night * d1 + side * 10 + [0, up * 0.8, 0]
    S[k] = spec([p0, (p0 + p1) / 2, p1], [[0, 0, 0], [0, 0, 0], [0, 0, 0]], 8, rl, [SATURN])
# Enceladus turning in sunlight (several angles)
for k, (az0, az1, el, d, spin) in {"e_enc_turn": (-35, -20, 8, 1.5, (150, 175)), "e_enc_turn2": (-15, -5, -20, 1.3, (170, 200)),
                                   "e_enc_turn3": (-45, -30, 25, 1.7, (120, 140)), "e_enc_turn4": (-25, -10, -5, 1.15, (200, 220))}.items():
    pos = [around(E, d, a, el) for a in np.linspace(az0, az1, 3)]
    S[k] = spec(pos, [E, E, E], 9, (0, 0), [SATURN, enc(0.2, spin)])
# low flight over the sunlit south polar terrain (three variants); 152 deg = toward the Sun
def low(a0, a1, lat_c, rad, lat_t, lead):
    pos, tgt = [], []
    for a in np.linspace(a0, a1, 4):
        ar, la = np.radians(a), np.radians(lat_c)
        pos.append(E + rad * np.array([np.cos(la) * np.cos(ar), np.sin(la), np.cos(la) * np.sin(ar)]))
        ar2, lt = np.radians(a + lead), np.radians(lat_t)
        tgt.append(E + 0.252 * np.array([np.cos(lt) * np.cos(ar2), np.sin(lt), np.cos(lt) * np.sin(ar2)]))
    return pos, tgt
for k, args in {"f_south_low": (120, 175, -40, 0.42, -70, 25), "f_south_low2": (185, 135, -48, 0.40, -75, -25),
                "f_south_low3": (140, 190, -35, 0.46, -65, 20)}.items():
    pos, tgt = low(*args)
    S[k] = spec(pos, tgt, 8, (0, 0), [SATURN, enc(0.3)], fov=50)
# 14  wide view of Saturn
S["g_saturn_wide"] = spec([[420, 140, 620], [395, 128, 585]], [[0, 0, 0], [0, 0, 0]], 6, (-2, 0), [SATURN])
# 15  second approach to Enceladus, from the north-west
S["h_enc_approach2"] = spec([around(E, 3.2, -40, 15), around(E, 2.4, -32, 8), around(E, 1.7, -25, 0)],
                            [E, E + [0, -0.05, 0], E + [0, -0.1, 0]], 9, (0, 2), [SATURN, enc(0.15)])
# 18  flight along the stripes, looking down on the south pole
pos = [E + [-0.32, -0.5, 0.05], E + [-0.15, -0.55, 0.2], E + [0.0, -0.52, 0.32]]
S["i_stripes_flight"] = spec(pos, [E + [-0.06, -0.21, 0.04], E + [-0.03, -0.21, 0.07], E + [0.0, -0.21, 0.1]], 7,
                             (0, 0), [SATURN, enc(0.25)], fov=45)
# jets close-up (trial s3 and variants)
S["j_jets_close"] = spec([[238.9, -0.78, -0.75], [238.6, -0.7, -0.52], [238.35, -0.62, -0.35]],
                         [[238, -0.25, 0], [238, -0.29, 0], [238, -0.33, 0]], 7, (-3, 2), [SATURN, enc(0.3)])
S["j_jets_close2"] = spec([E + [-0.9, -0.7, 0.5], E + [-0.7, -0.65, 0.35], E + [-0.5, -0.6, 0.25]],
                          [E + [0, -0.3, 0], E + [0, -0.33, 0], E + [0, -0.36, 0]], 7, (2, -1), [SATURN, enc(0.3)])
S["j_jets_close3"] = spec([E + [0.3, -0.95, 0.9], E + [0.2, -0.85, 0.65], E + [0.12, -0.75, 0.45]],
                          [E + [0, -0.28, 0], E + [0, -0.32, 0], E + [0, -0.35, 0]], 7, (0, 3), [SATURN, enc(0.3)])
S["j_jets_close4"] = spec([E + 1.9 * night + [0, -0.7, 0], E + 1.6 * night + [0, -0.7, 0]],
                          [E + [0, -0.4, 0], E + [0, -0.45, 0]], 7, (1, -2), [SATURN, enc(0.06)])
# flight through the plume (Cassini's dives)
S["k_plume_flythrough"] = spec([E + [-0.75, -0.7, 0.4], E + [-0.25, -0.72, 0.13], E + [0.25, -0.72, -0.13], E + [0.75, -0.7, -0.4]],
                               [E + [0, -0.22, 0]] * 4, 10, (0, 8), [SATURN, enc(0.3)], fov=60)
# 57  wide: Enceladus with its plume, Saturn behind
S["l_wide_enc_saturn"] = spec([E + [3.5, -1.4, 3.2], E + [3.1, -1.25, 2.8]], [E + [-1.2, -0.3, 0], E + [-1.3, -0.3, 0]], 7,
                              (-4, -2), [SATURN, enc(0.4)], fov=45)
# 60-63  pull back from Enceladus as Saturn hides the Sun (trial s10, longer)
S["m_pullback"] = spec([[238.5, -0.5, -0.9], [252, 8, -25], [285, 60, -120]], [[238, -0.1, 0], [190, 0, 0], [0, 0, 0]], 22,
                       (0, 3), [SATURN, enc(0.3)])

# variants used once more, so no flight is shown twice
S["b_enc_approach2"] = spec([around(E, 4.0, -60, -10), around(E, 3.0, -55, -12), around(E, 2.2, -50, -14)],
                            [E, E + [0, -0.05, 0], E + [0, -0.1, 0]], 8, (0, -2), [SATURN, enc(0.15, (100, 110))])
S["k_plume_dive2"] = spec([E + [0.7, -0.75, -0.2], E + [0.2, -0.78, -0.05], E + [-0.3, -0.76, 0.12], E + [-0.8, -0.72, 0.3]],
                          [E + [0, -0.22, 0]] * 4, 10, (0, -8), [SATURN, enc(0.3)], fov=60)
S["j_jets_close5"] = spec([E + [-0.5, -0.95, -0.6], E + [-0.4, -0.85, -0.45], E + [-0.3, -0.75, -0.33]],
                          [E + [0, -0.28, 0], E + [0, -0.31, 0], E + [0, -0.34, 0]], 7, (3, 0), [SATURN, enc(0.3)])
S["h_enc_approach3"] = spec([around(E, 3.5, 10, 20), around(E, 2.6, 0, 12), around(E, 1.9, -10, 5)],
                            [E, E + [0, -0.05, 0], E + [0, -0.1, 0]], 8, (0, 2), [SATURN, enc(0.15, (230, 240))])
# Earth: the ocean from orbit, then a dip to black (trial v3 s7 geometry)
S["s7_earth_ocean"] = {"duration": 8, "fit": True, "fallback": 8, "fov": 40, "seed": 8, "motion": "linear",
    "sun": [-0.0845, 0.22, 0.9663], "stars": {"count": 12000, "near": 3000, "far": 30000},
    "camera": {"pos": [[-9.407, 14.653, 25.682], [-8.026, 10.194, 16.531], [-6.858, 6.53, 9.045]],
               "target": [[0, 0, 0], [-1.292, 1.115, 1.435], [-2.769, 2.389, 3.075]], "roll": [-4, 0]},
    "bodies": [{"texture": ["../EARTHSS.jpg"], "center": [0, 0, 0], "radius": 6.371, "spin": [0, 3],
                "atmosphere": [0.35, 0.6, 1.0], "atmosphere_width": 0.02}]}

OUT.mkdir(parents=True, exist_ok=True)
for k, v in S.items():
    (OUT / f"{k}.json").write_text(json.dumps(v, indent=1))
print(len(S), "specs ->", OUT)
