"""Writes the EP02 size/distance scene specs (assets/space3d/S0xx.json, "renderer": "scale2d").
One spec per OUR_CGI shot, named after the shot id; every spec has "fit": true, so ci/run.py stretches it to the
voice-over length of its shot. Bodies are enlarged and distances shortened where noted; labels carry the real numbers.
Textures (server): EARTH2.jpg, MOON2.jpg, SUN2.jpg = Solar System Scope 2k maps (CC BY 4.0, based on NASA data).
Run: python episodes/ep02/make_scenes.py [out_dir]"""
import json, sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "assets" / "space3d"
S = {}


def view(c0, c1=None, w0=1000, w1=None, y0=0, y1=None):
    return {"center_km": [c0, c0 if c1 is None else c1], "width_km": [w0, w0 if w1 is None else w1],
            "y_km": [y0, y0 if y1 is None else y1]}


def earth(x=0, d=40774, **k):
    b = {"name": "EARTH", "type": "Terrestrial planet", "size": "12,742 km", "diameter_km": d, "x_km": x,
         "texture": "../EARTH2.jpg", "tint": [70, 120, 200], "spin": [0, 10], "at": 0}
    b.update(k); return b


def moon(x, d=11120, **k):
    b = {"name": "MOON", "type": "Natural satellite", "size": "3,475 km", "diameter_km": d, "x_km": x,
         "texture": "../MOON2.jpg", "tint": [170, 170, 170], "spin": [0, 4], "at": 0.05}
    b.update(k); return b


def sun(x=0, d=260000, **k):
    b = {"name": "THE SUN", "type": "Star", "size": "1,391,400 km", "diameter_km": d, "x_km": x,
         "texture": "../SUN2.jpg", "tint": [255, 190, 60], "spin": [0, 6], "emissive": True, "glow": 0.9, "at": 0}
    b.update(k); return b


def spec(v, bodies=None, light=(-0.9, 0.05), **extra):
    s = {"renderer": "scale2d", "duration": 8, "fit": True, "fallback": 8, "seed": 3, "view": v,
         "light": list(light), "bodies": bodies or []}
    s.update(extra); return s


# ---- layouts ---------------------------------------------------------------------------------------------------
EM_X = 172980                                   # Moon drawn at 45 % of its real distance, sizes enlarged
EM_V = view(EM_X / 2, EM_X / 2, 280000, 270000)
EM_A, EM_B = 20387 * 1.06, EM_X - 5560 * 1.06   # arrow / beam ends: body edges
SE_V = view(500000, 500000, 1300000, 1250000)   # Sun at 0, Earth at 1,000,000 (drawn)
SE_A, SE_B = 130000 * 1.06, 1000000 - 25000 * 1.06


def em(beams=None, arrows=None, labels=True, **extra):
    bs = [earth(label=labels), moon(EM_X, label=labels)]
    return spec(EM_V, bs, beams=beams or [], arrows=arrows or [], **extra)


def se(beams=None, arrows=None, labels=False, sun_kw=None, earth_kw=None, **extra):
    bs = [sun(**(sun_kw or {}), label=labels), earth(1000000, 50000, **(earth_kw or {}), label=labels)]
    return spec(SE_V, bs, beams=beams or [], arrows=arrows or [], **extra)


def beam(a, b, text=None, clock=None, fmt="s", t=(0.15, 0.9), y=0.0, stop=None):
    d = {"from_km": a, "to_km": b, "t": list(t), "y_frac": y}
    if text: d["text"] = text
    if clock: d.update(clock=list(clock), clock_fmt=fmt)
    if stop is not None: d["stop_at"] = stop
    return d


def arrow(a, b, text, sub=None, y=0.22, at=0.15):
    d = {"from_km": a, "to_km": b, "y_frac": y, "text": text, "at": at}
    if sub: d["sub"] = sub
    return d


# ---- chapter 1 ------------------------------------------------------------------------------------------------
S["S001"] = spec(view(0, 520000, 700000, 700000), [earth(0, 90000, label=False), sun(1000000, 600000, label=False)],
                 beams=[beam(60000, 1000000, t=(0.05, 0.95))])
S["S002"] = se(beams=[beam(SE_A, SE_B, "LIGHT takes 8 min 20 s", (0, 500), "ms", (0.2, 0.9))],
               arrows=[arrow(SE_A, SE_B, "about 150 million km", None, 0.28, 0.1)], labels=True)
S["S004"] = spec(view(-120000, -60000, 760000, 700000), [earth(-450000, 900000, label=False, spin=[0, 4])],
                 light=(0.95, 0.2), flares=[{"x_km": 0, "y_km": 90000, "strength": 1.4}])
S["S006"] = se(sun_kw={"glow": 1.6}, beams=[beam(SE_A, SE_B, t=(0.05, 0.6)), beam(SE_A, SE_B, t=(0.4, 0.95), y=0.06)])
S["S007"] = se(beams=[beam(SE_A, SE_B, "LIGHT", t=(0.1, 0.9))])
S["S008"] = spec(view(0, 0, 150000, 300000), [earth(0, 60000, label=False)], light=(-0.85, 0.15))

# ---- chapter 2 ------------------------------------------------------------------------------------------------
S["S011"] = spec(view(0, 0, 600000, 580000), [earth(0, 400000, label=False)],
                 arrows=[arrow(-200000, 200000, "12,742 km", "Earth's diameter", 0.3, 0.2)], light=(-0.8, 0.2))
S["S014"] = em(arrows=[arrow(EM_A, EM_B, "384,400 km", "about 30 Earth diameters", 0.2, 0.2)])
# 30 Earth-widths, true scale: real distances here (Earth 12,742 km, Moon at 384,400 km)
S["S015"] = spec(view(192200, 192200, 440000, 430000),
                 [earth(0, 12742, label=False, glow=0.0), moon(384400, 3475, label=False),
                  {"diameter_km": 12742, "x_km": 12742, "texture": "../EARTH2.jpg", "tint": [70, 120, 200], "repeat": 29,
                   "step_km": 12742, "ghost": True, "spin": [0, 0], "at": 0.1}],
                 arrows=[arrow(6371, 384400 - 1737, "30 Earth-widths", "laid end to end", 0.2, 0.3)])
S["S016"] = em(beams=[beam(EM_A, EM_B, "LIGHT", t=(0.1, 0.9))], labels=False)
S["S017"] = spec(view(EM_X / 2, EM_X / 2, 220000, 360000), [earth(label=False), moon(EM_X, label=False)])

# ---- chapter 3 ------------------------------------------------------------------------------------------------
S["S019"] = spec(view(0, 0, 1000, 1000), [], beams=[beam(-480, 480, t=(0.1, 0.8))],
                 texts=[{"x_frac": 0.5, "y_frac": 0.66, "lines": [["THE FASTEST THING WE KNOW OF", 0.05, "yellow"]], "at": 0.3}])
S["S020"] = em(beams=[beam(EM_A, EM_B, None, (0, 1.28), "s", (0.1, 0.95))], labels=False)
S["S021"] = em(beams=[beam(EM_A, EM_B, "LIGHT takes 1.28 s", (0, 1.28), "s", (0.1, 0.9))],
               arrows=[arrow(EM_A, EM_B, "384,400 km", "to the Moon", 0.25, 0.05)])
S["S023"] = em(arrows=[arrow(EM_A, EM_B, "384,400 km", None, 0.2, 0.05), arrow(EM_A, EM_B, "= 1.28 seconds of light", None, 0.34, 0.5)],
               labels=False)
S["S024"] = em(beams=[beam(EM_A, EM_B, None, t=(0.1, 0.45), y=-0.06), beam(EM_B, EM_A, None, t=(0.5, 0.85), y=0.06)],
               texts=[{"x_frac": 0.5, "y_frac": 0.2, "lines": [["ROUND TRIP: A FEW SECONDS", 0.05, "yellow"]], "at": 0.5}], labels=False)
S["S025"] = em(bubbles=[{"x_frac": 0.2, "y_frac": 0.3, "text": "Hello?", "at": 0.1},
                        {"x_frac": 0.8, "y_frac": 0.3, "text": "Hello!", "at": 0.65}],
               texts=[{"x_frac": 0.5, "y_frac": 0.12, "lines": [["...then a few seconds of silence", 0.04, "cyan"]], "at": 0.4}],
               beams=[beam(EM_A, EM_B, None, t=(0.1, 0.4), y=-0.1), beam(EM_B, EM_A, None, t=(0.65, 0.95), y=0.1)], labels=False)
S["S027"] = spec(view(0, 0, 1000, 1000), [], texts=[
    {"x_frac": 0.5, "y_frac": 0.16, "lines": [["THE FARTHER, THE OLDER THE LIGHT", 0.052, "yellow"]], "at": 0.0},
    {"x_frac": 0.5, "y_frac": 0.36, "lines": [["The Moon", 0.045, "white"], ["1.28 seconds old", 0.06, "yellow"]], "at": 0.2},
    {"x_frac": 0.5, "y_frac": 0.54, "lines": [["The Sun", 0.045, "white"], ["8 min 20 s old", 0.06, "yellow"]], "at": 0.45},
    {"x_frac": 0.5, "y_frac": 0.72, "lines": [["Proxima Centauri", 0.045, "white"], ["4.24 years old", 0.06, "yellow"]], "at": 0.7}])

# ---- chapter 4 ------------------------------------------------------------------------------------------------
S["S029"] = spec(view(600000, 640000, 3200000, 3100000, 250000, 250000),
                 [sun(0, 1391400, label_xy=[0.2, 0.02]), earth(1000000, 12742, y_km=0, glow=0.9, glow_color=[90, 150, 255])],
                 arrows=[arrow(1000000 - 695700, 1000000, "109 Earth diameters", None, 0.3, 0.45)])
S["S030"] = se(arrows=[arrow(SE_A, SE_B, "149,600,000 km", "Sun to Earth", 0.28, 0.1)], labels=True)
S["S031"] = se(arrows=[arrow(SE_A, SE_B, "149,600,000 km", None, 0.28, 0.0)],
               headline={"text": "1 ASTRONOMICAL UNIT", "sub": "the standard yardstick of the solar system", "at": 0.15})
S["S035"] = se(arrows=[arrow(SE_A, SE_B, "149,600,000 km", None, 0.3, 0.1)], labels=True)
S["S036"] = se(beams=[beam(SE_A, SE_B, "LIGHT takes", (0, 500), "ms", (0.15, 0.92))], labels=True)
S["S039"] = spec(view(0, 0, 1700000, 1650000), [sun(0, 1391400, label=False, glow=0.0)],
                 zigzag={"x_km": 0, "y_km": 0, "radius_km": 695700, "t": [0.05, 0.95], "steps": 46, "seed": 4},
                 texts=[{"x_frac": 0.5, "y_frac": 0.86, "lines": [["ENERGY ESCAPING THE SUN AS LIGHT", 0.05, "white"]], "at": 0.1}])

# ---- chapter 5 ------------------------------------------------------------------------------------------------
S["S040"] = spec(view(100000, 300000, 1500000, 1500000), [sun(-600000, 1200000, label=False, glow=0.5),
                 earth(1000000, 60000, label=False)], beams=[beam(0, 960000, None, t=(0.1, 0.95))])
S["S041"] = spec(view(0, 80000, 1000000, 900000), [earth(700000, 800000, label=False, glow=0.5, glow_color=[90, 150, 255], spin=[0, 3])],
                 beams=[beam(-480000, 330000, "LIGHT arrives", None, t=(0.05, 0.85))])
S["S042"] = se(beams=[beam(SE_A, SE_B, "about 300,000 km every second", None, t=(0.1, 0.9))])
S["S043"] = se(sun_kw={"dim": [[0.25, 0.5]], "glow": 0.9}, beams=[beam(SE_A, SE_B, None, t=(0.05, 0.9))],
               clock={"x_frac": 0.5, "y_frac": 0.16, "t": [0.25, 0.95], "seconds": [0, 500], "fmt": "ms",
                      "label": "TIME SINCE THE SUN SWITCHED OFF"})
S["S044"] = spec(view(0, 0, 1300000, 1250000), [earth(0, 700000, label=False, spin=[0, 4])], light=(-0.9, 0.1),
                 clock={"x_frac": 0.5, "y_frac": 0.1, "t": [0.1, 0.95], "seconds": [0, 500], "fmt": "ms", "label": "SINCE THE SUN SWITCHED OFF"})
S["S045"] = spec(view(-150000, 150000, 1300000, 1300000), [earth(0, 700000, label=False, spin=[0, 6])], light=(-0.9, 0.1))
S["S046"] = spec(view(100000, 100000, 1500000, 1450000), [earth(900000, 500000, label=False, spin=[0, 3])],
                 beams=[beam(-700000, 640000, None, t=(0.05 + 0.12 * i, 0.8 + 0.05 * i), y=-0.13 + 0.13 * i) for i in range(3)])
S["S047"] = spec(view(100000, 100000, 1500000, 1450000), [earth(900000, 500000, label=False, spin=[0, 3])],
                 beams=[beam(-700000, 640000, None, t=(0.0, 0.45), y=-0.13 + 0.13 * i, stop=0.5) for i in range(3)],
                 texts=[{"x_frac": 0.5, "y_frac": 0.16, "lines": [["THEN IT STOPS", 0.07, "yellow"]], "at": 0.6}])
S["S048"] = se(ripples={"x_km": 0, "t": [0.15, 0.95], "count": 3, "dashed": True},
               headline={"text": "A PREDICTION", "sub": "gravity's change would also take about 8 min 20 s", "at": 0.15})
S["S049"] = se(ripples={"x_km": 0, "t": [0.0, 1.0], "count": 3, "dashed": True},
               headline={"text": "A PREDICTION WE CANNOT TEST DIRECTLY", "sub": None, "at": 0.0})
S["S050"] = se(beams=[beam(SE_A, SE_B, "LIGHT", (0, 500), "ms", (0.1, 0.9))],
               texts=[{"x_frac": 0.5, "y_frac": 0.16, "lines": [["LIGHT ALWAYS SHOWS THE PAST", 0.055, "yellow"]], "at": 0.3}])

# ---- chapter 6 ------------------------------------------------------------------------------------------------
S["S053"] = se(beams=[beam(SE_A, SE_B, "LIGHT takes", (0, 500), "ms", (0.1, 0.92))], labels=True)
S["S058"] = spec(view(0, 0, 1000000, 950000), [earth(0, 800000, label=False, spin=[0, 12])], light=(-0.9, 0.15),
                 texts=[{"x_frac": 0.5, "y_frac": 0.9, "lines": [["SEASONS · WEATHER · THE WATER CYCLE", 0.045, "white"]], "at": 0.2}])
S["S061"] = spec(view(0), backdrop={"type": "ocean", "depth": [0.0, 0.55]})
S["S062"] = spec(view(0), backdrop={"type": "ocean", "depth": [0.55, 1.0], "vent_glow": 0.45},
                 texts=[{"x_frac": 0.5, "y_frac": 0.2, "lines": [["NO SUNLIGHT HERE", 0.06, "cyan"]], "at": 0.25}])

# ---- chapter 7 ------------------------------------------------------------------------------------------------
PX = 1000000                                    # Proxima drawn at 1,000,000 (distance not to scale)
def sun_vs_proxima(**extra):
    return spec(view(PX / 2, PX / 2, 1500000, 1450000),
                [sun(0, 420000, label=True, glow=0.7), {"name": "PROXIMA CENTAURI", "type": "Red dwarf star", "size": None,
                 "diameter_km": 65000, "x_km": PX, "texture": "../SUN2.jpg", "tint": [255, 60, 30], "recolor": True, "emissive": True,
                 "glow": 1.0, "glow_color": [255, 80, 40], "spin": [0, 4], "at": 0.0}], **extra)
S["S067"] = sun_vs_proxima(arrows=[arrow(210000 * 1.06, PX - 32500 * 1.06, "4.24 light-years", None, 0.3, 0.2)])
S["S068"] = sun_vs_proxima(beams=[beam(PX - 32500 * 1.06, 210000 * 1.06, "LIGHT takes", (0, 4.24), "years", (0.15, 0.92))])
S["S070"] = sun_vs_proxima(beams=[beam(PX - 32500 * 1.06, 210000 * 1.06, "set out long before we could see it", None, t=(0.1, 0.95))])
S["S071"] = spec(view(PX / 2, PX / 2, 1500000, 1450000),
                 [sun(0, 420000, label=True, glow=0.7, size="8 min 20 s away"),
                  {"name": "PROXIMA CENTAURI", "type": "Red dwarf star", "size": "4.24 years away", "diameter_km": 65000, "x_km": PX,
                   "texture": "../SUN2.jpg", "tint": [255, 60, 30], "recolor": True, "emissive": True, "glow": 1.0, "glow_color": [255, 80, 40],
                   "spin": [0, 4], "at": 0.0}])
S["S074"] = spec(view(0), stars=[{"x_frac": 0.1, "y_frac": 0.5, "size": 9, "color": [255, 220, 200], "at": 0.0}],
                 beams=[{"from_km": -450, "to_km": 520, "t": [0.1, 0.9], "y_frac": 0.0}],
                 texts=[{"x_frac": 0.5, "y_frac": 0.66, "lines": [["THE SAME RULE", 0.06, "yellow"]], "at": 0.4}])
S["S075"] = spec(view(0), stars=[
    {"x_frac": 0.2, "y_frac": 0.5, "size": 7, "label": "THE SUN", "sub": "8 min 20 s", "color": [255, 225, 150], "at": 0.05},
    {"x_frac": 0.5, "y_frac": 0.32, "size": 7, "label": "PROXIMA CENTAURI", "sub": "4.24 years", "color": [255, 120, 90], "at": 0.3},
    {"x_frac": 0.8, "y_frac": 0.55, "size": 9, "label": "SIRIUS", "sub": "8.6 years", "color": [200, 220, 255], "at": 0.55}])
S["S076"] = spec(view(0), stars=[
    {"x_frac": 0.12 + 0.15 * i, "y_frac": 0.5 + (0.08 if i % 2 else -0.08), "size": 9 - i, "at": 0.05 * i,
     "color": [255 - 12 * i, 235 - 10 * i, 220]} for i in range(6)],
    texts=[{"x_frac": 0.5, "y_frac": 0.2, "lines": [["THE FARTHER THE STAR", 0.05, "white"], ["THE OLDER THE MESSAGE", 0.06, "yellow"]], "at": 0.3}])

# ---- chapter 8 ------------------------------------------------------------------------------------------------
S["S077"] = spec(view(0, 0, 130000, 330000), [earth(0, 50000, label=False)], light=(-0.85, 0.15))
S["S080"] = spec(view(0), beams=[beam(-480, 480, t=(0.05, 0.9))],
                 texts=[{"x_frac": 0.5, "y_frac": 0.66, "lines": [["A LITTLE OF THE PAST", 0.06, "yellow"]], "at": 0.35}])
S["S083"] = se(beams=[beam(SE_A, SE_B, "LIGHT left the Sun", (0, 500), "ms", (0.1, 0.9))], labels=True)
S["S084"] = spec(view(0, 0, 1000, 1000), [], beams=[beam(-520, 520, t=(0.05, 0.85))],
                 flares=[{"x_km": 470, "y_km": 0, "strength": 1.6}],
                 texts=[{"x_frac": 0.5, "y_frac": 0.7, "lines": [["...and arrived in time for you to feel it", 0.045, "white"]], "at": 0.5}])

sys.path.insert(0, str(Path(__file__).parent))
from build_episode import DROP
OUT.mkdir(parents=True, exist_ok=True)
for k in DROP:
    S.pop(k, None); (OUT / f"{k}.json").unlink(missing_ok=True)
for k, v in S.items():
    (OUT / f"{k}.json").write_text(json.dumps(v, indent=1))
print(len(S), "specs ->", OUT)
