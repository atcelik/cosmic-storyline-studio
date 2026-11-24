"""Vertical Short: how big is the Milky Way (about 50 s). Everything is drawn by scale2d (procedural galaxy), so it needs
no textures or photos: run on the server with Kokoro (am_michael).
Run: python episodes/shorts/build_milkyway.py  ->  episodes/short_milkyway/"""
import json, shutil
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "short_milkyway"
W, H = 1080, 1920
SUN = (0.55, 229)                       # radius (galaxy units) and angle of the Sun's place, on a spiral arm
CREDIT = "Our visualization (procedural galaxy, not a photograph)"
NASA = "https://imagine.gsfc.nasa.gov/science/objects/milkyway1.html"
RMG = "https://www.rmg.co.uk/stories/space-astronomy/guide-milky-way-our-home-galaxy"
SPACE = "https://www.space.com/19915-milky-way"
STARWALK = "https://starwalk.space/news/the-milky-way-galaxy"


def gal(i, **kw):
    g = {"r_frac": 0.44, "y_frac": 0.43, "tilt": 0.62, "rot": [i * 5, i * 5 + 5]}
    g.update(kw)
    return g


def mark(label=None, **kw):
    m = {"r": SUN[0], "ang": SUN[1], "at": 0}
    if label:
        m["label"] = label
    m.update(kw)
    return m


def T(*lines, y=0.1, at=0.05):
    return {"x_frac": 0.5, "y_frac": y, "at": at, "lines": [list(l) for l in lines]}


# (voice-over, scene, claims)
SHOTS = [
    ("Light from the Sun reaches us in eight minutes.",
     {"galaxy": gal(0, marker=mark("SUN")), "texts": [T(("SUN TO EARTH", 0.05, "white"), ("8 MINUTES", 0.09, "yellow"))]}, []),
    ("To cross our galaxy, it needs one hundred thousand years.",
     {"galaxy": gal(1, beam={"t": [0.08, 0.92]}),
      "clock": {"x_frac": 0.5, "y_frac": 0.08, "t": [0.08, 0.92], "seconds": [0, 100000], "fmt": "years", "label": "LIGHT ACROSS THE GALAXY"}},
     [("Milky Way disk about 100,000 light-years across", NASA)]),
    ("This is the Milky Way, a disk of one hundred to four hundred billion stars.",
     {"galaxy": gal(2, tilt=[0.62, 0.9], r_frac=[0.44, 0.48]),
      "texts": [T(("THE MILKY WAY", 0.08, "yellow"), ("100-400 BILLION STARS", 0.045, "white"))]},
     [("100-400 billion stars", RMG)]),
    ("Shrink the whole solar system down to a coin in your hand.",
     {"galaxy": gal(3, tilt=0.9, r_frac=0.48, alpha=[1.0, 0.75], coin={"at": 0.15, "y_frac": 0.84, "label": "THE WHOLE SOLAR SYSTEM"}),
      "texts": [T(("SHRINK IT TO A COIN", 0.06, "yellow"))]}, []),
    ("The galaxy would still be about two and a half thousand kilometres wide.",
     {"galaxy": gal(4, tilt=0.9, r_frac=0.48, alpha=0.75, coin={"at": 0, "y_frac": 0.84, "label": "SOLAR SYSTEM = 2.4 cm"},
                    diam_arrow={"at": 0.15, "y_off": 0.25, "text": "GALAXY = 2,500 km", "sub": "at the same scale"}),
      "texts": [T(("SAME SCALE", 0.06, "yellow"))]}, []),
    ("Voyager 1, our most distant probe, would need nearly two billion years to cross it.",
     {"galaxy": gal(5, tilt=0.9, r_frac=0.48, probe={"at": 0, "icon": "voyager", "frac": 0.0006}),
      "clock": {"x_frac": 0.5, "y_frac": 0.08, "t": [0.05, 0.9], "seconds": [0, 1.76e9], "fmt": "byears", "label": "VOYAGER 1 ACROSS THE GALAXY"}},
     [("Voyager 1 moves at about 17 km/s; 100,000 light-years takes about 1.8 billion years", "https://science.nasa.gov/mission/voyager/voyager-1/")]),
    ("And we are not even near the middle.",
     {"galaxy": gal(6, tilt=0.9, r_frac=0.48, marker=mark("YOU ARE HERE")), "texts": [T(("NOT IN THE MIDDLE", 0.06, "yellow"))]}, []),
    ("We sit about twenty-six thousand light-years out.",
     {"galaxy": gal(7, tilt=0.9, r_frac=0.48, marker=mark("YOU ARE HERE", radius_arrow={"text": "26,000 LIGHT-YEARS", "at": 0.1}))},
     [("Sun about 26,000 light-years from the centre", SPACE)]),
    ("Even so, the Sun is carrying us around the centre.",
     {"galaxy": gal(8, tilt=0.9, r_frac=0.48, marker=mark("SUN", orbit=[SUN[1], SUN[1] + 70], trail=True)),
      "texts": [T(("WE ARE MOVING", 0.06, "yellow"))]}, []),
    ("One lap takes about two hundred and thirty million years.",
     {"galaxy": gal(9, tilt=0.9, r_frac=0.48, marker=mark("SUN", orbit=[SUN[1] + 70, SUN[1] + 360], trail=True)),
      "clock": {"x_frac": 0.5, "y_frac": 0.08, "t": [0.05, 0.92], "seconds": [0, 230], "fmt": "myears", "label": "ONE LAP AROUND THE GALAXY"}},
     [("One orbit takes about 230 million years", RMG)]),
    ("The last time we were here, the first dinosaurs were just appearing.",
     {"galaxy": gal(10, tilt=0.9, r_frac=0.48, marker=mark("230 MILLION YEARS AGO")),
      "texts": [T(("LAST TIME HERE:", 0.05, "white"), ("FIRST DINOSAURS", 0.08, "yellow"))]},
     [("One galactic year ago dinosaurs were just emerging", STARWALK)]),
    ("And the Milky Way is only one of billions of galaxies.",
     {"galaxy": gal(11, tilt=0.9, r_frac=[0.48, 0.07], many={"at": 0.25, "n": 55}),
      "texts": [T(("ONE OF BILLIONS", 0.07, "yellow"), at=0.4)]}, []),
]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets" / "space3d").mkdir(parents=True)
    (OUT / "assets" / "music").mkdir()
    shutil.copy(HERE.parent / "ep02" / "music" / "drone.wav", OUT / "assets" / "music" / "drone.wav")
    shots = []
    for i, (vo, scene, claims) in enumerate(SHOTS):
        sid = f"S{i + 1:03d}"
        spec = {"renderer": "scale2d", "duration": 8, "fit": True, "fallback": 6, "seed": 3, "size": [W, H],
                "view": {"center_km": [0, 0], "width_km": [1000, 1000]}}
        spec.update(scene)
        (OUT / "assets" / "space3d" / f"{sid}.json").write_text(json.dumps(spec, indent=1))
        s = {"id": sid, "beat": "B1", "voiceover": vo,
             "visual": {"type": "video", "file": f"assets/{sid}.mp4", "source_class": "OUR_CGI", "credit": CREDIT,
                        "source_url": NASA, "credit_verified": True, "credit_short": "Illustration"},
             "camera": {"move": "hold"}, "transition_out": {"type": "cut"}, "min_duration": 3.0}
        if claims:
            s["claims"] = [{"text": c, "source_url": u, "verified": True} for c, u in claims]
        shots.append(s)
    shots[-1]["min_duration"] = 4.5
    ep = {"schema_version": 2,
          "episode": {"id": "short_milkyway", "title": "How big is the Milky Way? #shorts", "language": "en",
                      "central_question": "How big is our galaxy, compared with things we know?"},
          "format": {"width": W, "height": H, "caption_y": 0.76},
          "burn_captions": True, "caption_words": 3,
          "voice": {"engine": "kokoro", "voice": "am_michael", "speed": 1.15},
          "music": {"file": "assets/music/drone.wav", "credit": "Procedurally generated by us", "license": "own work", "gain_db": -15},
          "beats": [{"id": "B1", "name": "Short"}], "shots": shots}
    (OUT / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(shots)} shots -> {OUT}")


if __name__ == "__main__":
    main()
