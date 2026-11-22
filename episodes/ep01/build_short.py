"""Builds the first vertical Short from EP01 (episodes/ep01_short1): 1080x1920, native vertical 3D renders,
real photos cropped from high-resolution originals (or framed whole on black), burned-in captions.
Narration reuses lines of the approved EP01 script only.
Run: python episodes/ep01/build_short.py"""
import json, math, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "ep01_short1"
sys.path.insert(0, str(HERE))
from build_episode import ASSETS, CGI_CREDIT  # noqa: E402

W, H = 1080, 1920

# (narration from the approved script, visual, focus)
SHOTS = [
    ("Water, spraying out of a frozen moon, into space.", "3d:c_jets_backlit", None),
    ("This is the real image.", "A007", None),
    ("A moon barely five hundred kilometres across, leaking an ocean.", "3d:e_enc_turn", None),
    ("In 2015 came the verdict: a global ocean, wrapped around the entire moon.", "A009", (0.5, 0.5)),
    ("Cassini flew straight through the plume and tasted it.", "3d:k_plume_flythrough", None),
    ("It found hydrogen. And for microbes, it is food: chemical energy.", "A011", (0.5, 0.6)),
    ("Water. Energy. Chemistry. Every box we know how to tick.", "A001", (0.5, 0.5)),
    ("So, is something alive in the ocean of Enceladus?", "3d:m_pullback", None),
    ("Nobody knows. Not yet.", "3d+:m_pullback", None),
]
CONTAIN = {"A007"}          # 1580 px wide: shown whole on black instead of a soft vertical crop
SRC = "https://science.nasa.gov/missions/cassini/cassini-at-enceladus-a-decade-plus-of-discovery"
H2 = "https://www.jpl.nasa.gov/news/nasa-missions-provide-new-insights-into-ocean-worlds-in-our-solar-system/"
OCEAN = "https://www.jpl.nasa.gov/news/cassini-finds-global-ocean-in-saturns-moon-enceladus/"
CLAIM = {2: SRC, 3: OCEAN, 4: SRC, 5: H2}


ZOOM = {"c_jets_backlit": 0.5}     # move the camera closer: the subject is narrow in a 9:16 frame


def vertical(spec, scene=""):
    """Same flight, 9:16 frame. fov is horizontal in space3d, so keep the landscape's vertical field of view."""
    f = spec.get("fov", 40)
    spec["fov"] = round(math.degrees(2 * math.atan(math.tan(math.radians(f) / 2) * 9 / 16)), 2)
    spec["size"] = [W, H]
    z = ZOOM.get(scene)
    if z:
        cam = spec["camera"]
        cam["pos"] = [[t + (p - t) * z for p, t in zip(P, T)] for P, T in zip(cam["pos"], cam["target"])]
    return spec


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets" / "space3d").mkdir(parents=True)
    (OUT / "assets" / "music").mkdir()
    shutil.copy(HERE / "assets" / "music" / "drone.wav", OUT / "assets" / "music" / "drone.wav")
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([sys.executable, str(HERE / "make_scenes.py"), str(tmp)], check=True, capture_output=True)
    shots, used = [], {}
    for i, (vo, vis, focus) in enumerate(SHOTS):
        s = {"id": f"S{i + 1:03d}", "beat": "B1", "voiceover": vo, "transition_out": {"type": "cut"}}
        if vis.startswith("3d"):
            scene = vis.split(":", 1)[1]
            dst = OUT / "assets" / "space3d" / f"{scene}.json"
            if not dst.exists():
                dst.write_text(json.dumps(vertical(json.loads((tmp / f"{scene}.json").read_text()), scene), indent=1))
            s["visual"] = {"type": "video", "file": f"assets/{scene}.mp4", "source_class": "OUR_CGI", "credit": CGI_CREDIT,
                           "source_url": "https://images.nasa.gov/details/PIA18435", "credit_short": "Visualization, NASA/JPL Cassini map"}
            if vis.startswith("3d+"):
                s["visual"]["continue"] = True
            s["camera"] = {"move": "hold"}
            s["min_duration"] = 4.0
        else:
            url, title, cls, credit, page = ASSETS[vis]
            s["visual"] = {"type": "still", "source_class": cls, "credit": credit, "source_url": page,
                           "search_query": "manifest", "credit_short": credit.split(";")[0][:60]}
            if vis in CONTAIN:
                s["visual"].update({"fit": "contain", "contain_margin": 0.02})
                s["camera"] = {"move": "push_in", "strength": 0.06, "focus": [0.5, 0.5]}
            else:
                s["camera"] = {"move": "push_in", "strength": 0.07, "focus": list(focus)}
            s["min_duration"] = 3.5
            used.setdefault(vis, []).append(s["id"])
        if i in CLAIM:
            s["claims"] = [{"text": vo, "source_url": CLAIM[i], "verified": True}]
        shots.append(s)
    shots[0]["vo_lead"] = 0.3
    shots[0]["card"] = {"title": "Enceladus", "sub": "A moon of Saturn"}
    shots[-1]["min_duration"] = 5.0
    shots[-1]["on_screen_text"] = "Full episode on the channel"
    shots[-1]["text_start"] = 1.6
    ep = {"schema_version": 2,
          "episode": {"id": "ep01_short1", "title": "This moon is leaking an ocean #shorts", "language": "en",
                      "central_question": "Is something alive in the ocean under the ice of Enceladus?"},
          "format": {"width": W, "height": H},
          "burn_captions": True, "caption_words": 3,
          "voice": {"engine": "kokoro", "voice": "am_michael", "speed": 1.0},
          "music": {"file": "assets/music/drone.wav", "credit": "Procedurally generated by us", "license": "own work", "gain_db": -15},
          "beats": [{"id": "B1", "name": "Short"}],
          "shots": shots}
    (OUT / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    need = set(used) | {"T003", "SAT8", "SAT2", "RING8", "RING2"}
    items = [{"id": k, "url": u, "kind": "image", "title": t, "source_class": c, "credit": cr, "source_url": pg,
              "credit_checked": True, "note": "credit line read from the source page on 2026-11-22", "shots": used.get(k, [])}
             for k, (u, t, c, cr, pg) in ASSETS.items() if k in need]
    (OUT / "asset_manifest.json").write_text(json.dumps({"episode": "ep01_short1", "items": items}, indent=1) + "\n")
    print(f"{len(shots)} shots -> {OUT}")


if __name__ == "__main__":
    main()
