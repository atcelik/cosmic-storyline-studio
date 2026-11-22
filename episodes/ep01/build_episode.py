"""Builds EP01 episode.json + asset_manifest.json from the approved script (Claude Doc rev 9, 2026-11-22).
Run: python episodes/ep01/build_episode.py"""
import json
from pathlib import Path

HERE = Path(__file__).parent
JPL = "https://d2pn8kiwq2w21t.cloudfront.net/original_images/jpeg{}.jpg"
SSI, JPLC = "NASA/JPL/Space Science Institute", "NASA/JPL-Caltech"

# id: (url, title, source_class, credit, page)
ASSETS = {
    "A007": (JPL.format("PIA11688"), "Bursting at the Seams: the Geyser Basin of Enceladus", "REAL_PHOTO", SSI,
             "https://www.jpl.nasa.gov/images/bursting-at-the-seams-the-geyser-basin-of-enceladus"),
    "P11684": (JPL.format("PIA11684"), "Enceladus Leading Hemisphere (Cassini mosaic, 2009)", "REAL_PHOTO", SSI,
               "https://www.jpl.nasa.gov/images/pia11684-enceladus-leading-hemisphere/"),
    "P01394": (JPL.format("PIA01394"), "Enceladus from Voyager 2, 25 Aug 1981", "REAL_PHOTO", "NASA/JPL",
               "https://www.jpl.nasa.gov/images/pia01394-saturn-enceladus-from-a-distance-of-119000-kilometers-74000-miles/"),
    "A008": (JPL.format("PIA06254"), "Zooming In On Enceladus (false-colour mosaic)", "PROCESSED_DATA", SSI,
             "https://www.jpl.nasa.gov/images/pia06254-zooming-in-on-enceladus-mosaic/"),
    "A006": (JPL.format("PIA11135"), "Tiger Stripes...Magnified! (mosaic)", "REAL_PHOTO", SSI,
             "https://www.jpl.nasa.gov/images/pia11135-tiger-stripesmagnified/"),
    "A003": (JPL.format("PIA07798"), "Spray Above Enceladus III", "REAL_PHOTO", SSI,
             "https://www.jpl.nasa.gov/images/pia07798-spray-above-enceladus-iii/"),
    "A002": (JPL.format("PIA12713"), "High-Phase Plumes (Enceladus jets backlit)", "REAL_PHOTO", SSI,
             "https://www.jpl.nasa.gov/images/pia12713-high-phase-plumes/"),
    "A005": (JPL.format("PIA07762"), "Enceladus Plume (still)", "REAL_PHOTO", SSI,
             "https://www.jpl.nasa.gov/images/pia07762-enceladus-plume-movie/"),
    "P10360": (JPL.format("PIA10360"), "Stripes and Heat Map Side by Side (Cassini, 2008)", "PROCESSED_DATA",
               "NASA/JPL/GSFC/SwRI/SSI", "https://www.jpl.nasa.gov/images/pia10360-stripes-and-heat-map-side-by-side"),
    "A004": (JPL.format("PIA21887"), "Last Enceladus Plume Observation", "REAL_PHOTO", "NASA/JPL-Caltech/Space Science Institute",
             "https://www.jpl.nasa.gov/images/pia21887-last-enceladus-plume-observation/"),
    "P08321": (JPL.format("PIA08321"), "Ghostly Fingers of Enceladus (E ring)", "REAL_PHOTO", SSI,
               "https://www.jpl.nasa.gov/images/pia08321-ghostly-fingers-of-enceladus/"),
    "P18071": (JPL.format("PIA18071"), "Ocean Inside Saturn's Moon Enceladus (diagram)", "SCIENTIFIC_CGI", JPLC,
               "https://www.jpl.nasa.gov/images/pia18071-ocean-inside-saturns-moon-enceladus/"),
    "A009": (JPL.format("PIA19656"), "Global Ocean on Enceladus (artist's rendering)", "ARTIST_CONCEPT", JPLC,
             "https://www.jpl.nasa.gov/images/pia19656-global-ocean-on-enceladus-artists-rendering/"),
    "A010": (JPL.format("PIA23175"), "Enceladus Global View with Plume (artist's rendering)", "ARTIST_CONCEPT", JPLC,
             "https://www.jpl.nasa.gov/images/pia23175-enceladus-global-view-with-plume-artists-rendering/"),
    "A011": (JPL.format("PIA19058"), "Enceladus: Possible Hydrothermal Activity (artist's concept)", "ARTIST_CONCEPT", JPLC,
             "https://www.jpl.nasa.gov/images/enceladus-possible-hydrothermal-activity-artists-concept"),
    "A001": (JPL.format("PIA17172"), "The Day the Earth Smiled (Saturn backlit mosaic)", "REAL_PHOTO", "NASA/JPL-Caltech/SSI",
             "https://www.jpl.nasa.gov/images/pia17172-the-day-the-earth-smiled"),
    "STS66": ("https://images-assets.nasa.gov/image/sts066-127-006/sts066-127-006~orig.jpg",
              "Hurricane Florence seen from Space Shuttle Atlantis (STS-66, 1994)", "REAL_PHOTO", "NASA (JSC)",
              "https://images.nasa.gov/details/sts066-127-006"),
    "N008": ("https://oceanexplorer.noaa.gov/wp-content/uploads/2025/08/1605vent-hires.jpg",
             "Black smoker, Mariana back-arc", "REAL_PHOTO", "NOAA Office of Ocean Exploration and Research",
             "https://oceanexplorer.noaa.gov/"),
    "NUR": ("https://s3.amazonaws.com/s3-east-testmedia-noaa.woc.noaa.gov/dam/Photos/legacy/pl23_nur04512.jpg",
            "Tube worms at the base of a black smoker", "REAL_PHOTO", "OAR/National Undersea Research Program (NURP)",
            "https://noaa.gov/media/digital-library-photo/pl23nur04512jpg"),
    "LOST": ("https://s3.amazonaws.com/s3-east-testmedia-noaa.woc.noaa.gov/dam/Photos/legacy/pl23_expl2224.jpg",
             "A white carbonate spire in the Lost City vent field", "REAL_PHOTO",
             "IFE, URI-IAO, UW, Lost City Science Party; NOAA/OAR/OER; The Lost City 2005 Expedition",
             "https://noaa.gov/media/digital-library-photo/pl23expl2224jpg"),
    "P21439": (JPL.format("PIA21439"), "Cassini Grand Finale Dive (illustration)", "ARTIST_CONCEPT", JPLC,
               "https://www.jpl.nasa.gov/images/pia21439-cassini-grand-finale-dive-illustration/"),
    "P21440": (JPL.format("PIA21440"), "Cassini Versus Saturn (illustration)", "ARTIST_CONCEPT", JPLC,
               "https://www.jpl.nasa.gov/images/pia21440-cassini-versus-saturn-illustration/"),
    "WEBB": ("https://cdn.esawebb.org/archives/images/large/weic2314a.jpg", "Webb: water plume of Enceladus (2023)",
             "PROCESSED_DATA", "NASA, ESA, CSA, STScI, G. Villanueva (NASA's Goddard Space Flight Center), A. Pagan (STScI)",
             "https://esawebb.org/images/weic2314a"),
    # textures for the 3D scenes
    "T003": ("https://images-assets.nasa.gov/image/PIA18435/PIA18435~orig.jpg", "Color Maps of Enceladus - 2014 (globe texture)",
             "PROCESSED_DATA", "NASA/JPL-Caltech/Space Science Institute/Lunar and Planetary Institute", "https://images.nasa.gov/details/PIA18435"),
    "SAT8": ("https://www.solarsystemscope.com/textures/download/8k_saturn.jpg", "Solar System Scope texture 8k_saturn.jpg",
             "PROCESSED_DATA", "Solar System Scope (CC BY 4.0), based on NASA data", "https://www.solarsystemscope.com/textures/"),
    "SAT2": ("https://www.solarsystemscope.com/textures/download/2k_saturn.jpg", "Solar System Scope texture 2k_saturn.jpg",
             "PROCESSED_DATA", "Solar System Scope (CC BY 4.0), based on NASA data", "https://www.solarsystemscope.com/textures/"),
    "RING8": ("https://www.solarsystemscope.com/textures/download/8k_saturn_ring_alpha.png", "Solar System Scope 8k_saturn_ring_alpha.png",
              "PROCESSED_DATA", "Solar System Scope (CC BY 4.0), based on NASA data", "https://www.solarsystemscope.com/textures/"),
    "RING2": ("https://www.solarsystemscope.com/textures/download/2k_saturn_ring_alpha.png", "Solar System Scope 2k_saturn_ring_alpha.png",
              "PROCESSED_DATA", "Solar System Scope (CC BY 4.0), based on NASA data", "https://www.solarsystemscope.com/textures/"),
    "EARTHSS": ("https://www.solarsystemscope.com/textures/download/8k_earth_daymap.jpg", "Solar System Scope Earth day map",
                "PROCESSED_DATA", "Solar System Scope (CC BY 4.0), based on NASA data", "https://www.solarsystemscope.com/textures/"),
}

SMALL = {"P01394", "A003", "A002", "P08321", "NUR", "WEBB"}

CGI_CREDIT = "Our visualization: Enceladus map PIA18435 (NASA/JPL/SSI/LPI), Saturn and ring textures Solar System Scope (CC BY 4.0)"
EARTH_CREDIT = "Our visualization: Solar System Scope Earth map (CC BY 4.0, based on NASA data)"

SRC = {
    "nasa": "https://science.nasa.gov/missions/cassini/cassini-at-enceladus-a-decade-plus-of-discovery",
    "ocean": "https://www.jpl.nasa.gov/news/cassini-finds-global-ocean-in-saturns-moon-enceladus/",
    "h2": "https://www.jpl.nasa.gov/news/nasa-missions-provide-new-insights-into-ocean-worlds-in-our-solar-system/",
    "phos": "https://www.washington.edu/news/2023/06/14/phosphate-a-key-building-block-of-life-found-on-saturns-moon-enceladus/",
    "whoi": "https://www.whoi.edu/feature/history-hydrothermal-vents/discovery/1977.html",
    "webb": "https://www.sciencenews.org/article/jwst-enceladus-plume-water-space",
    "esa": "https://www.esa.int/Science_Exploration/Space_Science/Saturn_s_moon_Enceladus_top_target_for_ESA",
    "voy": "https://www.jpl.nasa.gov/images/pia01394-saturn-enceladus-from-a-distance-of-119000-kilometers-74000-miles/",
    "end": "https://science.nasa.gov/mission/cassini/",
    "lost": "https://www.science.org/doi/10.1126/science.1102556",
}

BEATS = [
    ("B1", "Hook", "Enceladus", "A frozen moon of Saturn"),
    ("B2", "A moon that should be dead", "Too small to be alive", ""),
    ("B3", "The discovery", "The jets", "Cassini, 2005 to 2017"),
    ("B4", "The hidden ocean", "An ocean under the ice", ""),
    ("B5", "The ingredients", "The recipe for life", ""),
    ("B6", "Life without sunlight", "Life without sunlight", "Earth's deep-sea vents"),
    ("B7", "What we still don't know", "The missing answer", ""),
    ("B8", "The answer", None, None),
]
BECAUSE = {"B2": "But a moon that small should be frozen solid.",
           "B3": "Therefore only a closer look could explain it.",
           "B4": "But where was all that water coming from?",
           "B5": "Therefore the next question: could it support life?",
           "B6": "Therefore we look at Earth, where that chemistry already feeds life.",
           "B7": "But Cassini could not answer the last question.",
           "B8": "Therefore the answer is still open."}

# (beat, narration, visual, focus or None, claim source key or None)
# visual: "3d:<scene>" new flight, "3d+:<scene>" same flight continues, otherwise an asset id
SHOTS = [
    ("B1", "In 2005, a spacecraft circling Saturn noticed something odd about one of its smallest moons.", "3d:a_saturn_approach", None, "nasa"),
    ("B1", "Something there was pushing back against Saturn's magnetic field.", "3d+:a_saturn_approach", None, "nasa"),
    ("B1", "Months later, Cassini flew in for a closer look.", "3d:b_enc_approach", None, None),
    ("B1", "And it saw this: water, spraying out of a frozen moon, into space.", "3d:c_jets_backlit", None, None),
    ("B1", "This is the real image.", "A007", (0.5, 0.55), None),
    ("B1", "A moon barely five hundred kilometres across, leaking an ocean.", "P11684", (0.5, 0.5), "nasa"),
    ("B1", "Today we follow that water down, to the ocean it came from.", "3d:d_saturn_eclipse3", None, None),
    ("B1", "And we ask the question scientists now ask out loud: could something be alive down there?", "3d+:d_saturn_eclipse3", None, None),
    ("B2", "Enceladus is one of Saturn's smaller moons.", "3d:e_enc_turn", None, None),
    ("B2", "Small worlds lose their heat fast. They freeze solid, and they stay that way.", "3d+:e_enc_turn", None, None),
    ("B2", "When Voyager 2 flew past in 1981, it saw something that didn't fit.", "P01394", (0.5, 0.5), "voy"),
    ("B2", "Whole regions were smooth, with no craters at all. Something had been repaving this moon.", "A008", (0.55, 0.5), "voy"),
    ("B2", "Fresh ice. Long fractures. A surface that looked young.", "A006", (0.45, 0.5), None),
    ("B2", "Voyager only had a glimpse. The answer had to wait more than twenty years.", "3d:f_south_low", None, None),
    ("B3", "Cassini reached Saturn in 2004.", "3d:g_saturn_wide", None, "ocean"),
    ("B3", "In February 2005, its magnetometer felt Saturn's magnetic field bending around Enceladus, as if something like an atmosphere was in the way.", "3d:h_enc_approach2", None, "nasa"),
    ("B3", "In July, Cassini found a cloud of water vapour hanging over the south pole.", "A003", (0.5, 0.5), "nasa"),
    ("B3", "Below it were four long, warm fractures in the ice. Scientists called them tiger stripes.", "A006", (0.55, 0.45), "nasa"),
    ("B3", "Each one is about a hundred and thirty-five kilometres long.", "3d:i_stripes_flight", None, "nasa"),
    ("B3", "Over the years, Cassini counted a hundred and one separate geysers along them.", "A002", (0.5, 0.55), "nasa"),
    ("B3", "And the south pole was not just warm for an ice moon. It was hot.", "3d:j_jets_close", None, None),
    ("B3", "It gives off about sixteen gigawatts of heat, around two and a half times the power of all the hot springs in Yellowstone.", "P10360", (0.75, 0.5), "nasa"),
    ("B3", "The spray was not a thin mist. It was feeding an entire ring of Saturn.", "A001", (0.5, 0.5), "nasa"),
    ("B3", "Saturn's faint outer E ring is made mostly of ice from these jets.", "P08321", (0.5, 0.5), "nasa"),
    ("B3", "So where was all that water coming from?", "3d:d_saturn_eclipse", None, None),
    ("B4", "Ice can turn straight into vapour without ever melting. Scientists needed proof of liquid water.", "3d:f_south_low2", None, None),
    ("B4", "The proof was salt.", "3d:j_jets_close2", None, None),
    ("B4", "In 2009, Cassini found sodium salts in ice grains from Saturn's outer ring, the ring Enceladus feeds.", "P08321", (0.5, 0.5), "nasa"),
    ("B4", "Salt like that dissolves out of rock, in liquid water. Somewhere below, water was touching stone.", "3d:j_jets_close3", None, None),
    ("B4", "By 2014, gravity measurements pointed to a sea under the south pole, about ten kilometres deep, under thirty to forty kilometres of ice.", "P18071", (0.5, 0.65), "nasa"),
    ("B4", "Then came a stranger clue. Enceladus wobbles as it orbits Saturn.", "3d:e_enc_turn2", None, None),
    ("B4", "Scientists tracked craters across hundreds of Cassini images, taken over more than seven years.", "P11684", (0.45, 0.35), "ocean"),
    ("B4", "The wobble was too large for a moon frozen solid. The ice shell had to be floating.", "3d:e_enc_turn4", None, "ocean"),
    ("B4", "In 2015 came the verdict: a global ocean, wrapped around the entire moon.", "A009", (0.5, 0.5), "ocean"),
    ("B4", "A hidden ocean, on a moon with roughly the surface area of Turkey.", "A010", (0.5, 0.5), None),
    ("B5", "Life as we know it needs three things: liquid water, a source of energy, and the right chemistry.", "3d:b_enc_approach2", None, None),
    ("B5", "Water, Enceladus clearly has.", "3d:j_jets_close4", None, None),
    ("B5", "In 2008, Cassini flew straight through the plume and tasted it.", "A007", (0.35, 0.6), "nasa"),
    ("B5", "It was full of organic molecules, about twenty times denser than expected.", "3d:k_plume_flythrough", None, "nasa"),
    ("B5", "Scientists compared it to carbonated water with an essence of natural gas.", "3d+:k_plume_flythrough", None, "nasa"),
    ("B5", "In 2015, tiny grains of silica pointed to something more: hot water reacting with rock, on the ocean floor.", "A011", (0.5, 0.6), "nasa"),
    ("B5", "Then, on the 28th of October 2015, Cassini made its deepest dive through the plume.", "3d:k_plume_dive2", None, "h2"),
    ("B5", "It found hydrogen, about one percent of the gas.", "3d+:k_plume_dive2", None, "h2"),
    ("B5", "Hydrogen like that forms when hot water reacts with rock. And for microbes, it is food: chemical energy.", "A011", (0.4, 0.7), "h2"),
    ("B5", "In 2023, one more ingredient: phosphates, at least a hundred times more concentrated than in Earth's oceans.", "A010", (0.5, 0.75), "phos"),
    ("B5", "Phosphorus forms the backbone of every DNA molecule on Earth.", "3d:e_enc_turn3", None, "phos"),
    ("B5", "Water. Energy. Chemistry. Every box we know how to tick.", "3d:d_saturn_eclipse2", None, None),
    ("B6", "To see what that chemistry can do, we only have to look at home.", "STS66", (0.5, 0.45), None),
    ("B6", "Two and a half kilometres below the Pacific, there is no sunlight at all.", "3d:s7_earth_ocean", None, "whoi"),
    ("B6", "In 1977, scientists exploring the Galápagos Rift found hot springs on the seafloor, and life crowded around them.", "N008", (0.5, 0.45), "whoi"),
    ("B6", "Clams, crabs, tubeworms, living in total darkness.", "NUR", (0.5, 0.5), "whoi"),
    ("B6", "At the base of that food web are microbes that live on chemistry, not sunlight.", "LOST", (0.5, 0.4), "whoi"),
    ("B6", "At places like the Lost City vent field in the Atlantic, hydrogen from the rocks feeds them.", "LOST", (0.5, 0.7), "lost"),
    ("B6", "Hydrogen. Carbon dioxide. Warm rock. Liquid water. The same recipe Cassini found at Enceladus.", "3d:j_jets_close5", None, "h2"),
    ("B6", "Some scientists think life on Earth itself may have started at vents like these.", "3d:h_enc_approach3", None, None),
    ("B7", "Cassini was built before anyone knew Enceladus had an ocean. It could not detect life.", "P21439", (0.5, 0.5), "h2"),
    ("B7", "On the 15th of September 2017, it was steered into Saturn on purpose, so it could never crash into Enceladus and contaminate it.", "P21440", (0.5, 0.5), "end"),
    ("B7", "But the jets are still going. In 2023, the James Webb Space Telescope showed the plume reaching nearly ten thousand kilometres into space.", "WEBB", (0.5, 0.5), "webb"),
    ("B7", "That is about nineteen times the width of the moon itself.", "3d:l_wide_enc_saturn", None, "webb"),
    ("B7", "In 2024, the European Space Agency named Enceladus the top target for its next large science mission.", "3d:f_south_low3", None, "esa"),
    ("B7", "The idea: land near the tiger stripes and catch the ocean as it falls back down. The earliest launch: the 2040s.", "3d+:f_south_low3", None, "esa"),
    ("B8", "So, is something alive in the ocean of Enceladus?", "3d:m_pullback", None, None),
    ("B8", "Nobody knows. Not yet.", "3d+:m_pullback", None, None),
    ("B8", "But for the first time, we know a place in our solar system where every ingredient is there,", "3d+:m_pullback", None, None),
    ("B8", "and the ocean sends us samples for free. We just have to go and catch them.", "3d+:m_pullback", None, None),
]


def main():
    shots, used = [], {}
    for i, (beat, vo, vis, focus, src) in enumerate(SHOTS, 1):
        sid = f"S{i:03d}"
        s = {"id": sid, "beat": beat, "voiceover": vo}
        if vis.startswith("3d"):
            scene = vis.split(":", 1)[1]
            earth = scene.startswith("s7_")
            s["visual"] = {"type": "video", "file": f"assets/{scene}.mp4", "source_class": "OUR_CGI",
                           "credit": EARTH_CREDIT if earth else CGI_CREDIT,
                           "source_url": "https://www.solarsystemscope.com/textures/" if earth else "https://images.nasa.gov/details/PIA18435",
                           "credit_short": "Visualization, Solar System Scope map" if earth else "Visualization, NASA/JPL Cassini map"}
            if vis.startswith("3d+"):
                s["visual"]["continue"] = True
            s["camera"] = {"move": "hold"}
        else:
            url, title, cls, credit, page = ASSETS[vis]
            s["visual"] = {"type": "still", "source_class": cls, "credit": credit, "source_url": page,
                           "search_query": "manifest", "credit_short": credit.split(";")[0][:60]}
            s["camera"] = {"move": "push_in", "strength": 0.07, "focus": list(focus)}
            if vis in SMALL:                     # archive photo smaller than the frame: whole picture on black
                s["visual"]["fit"] = "contain"
                s["camera"] = {"move": "push_in", "strength": 0.05, "focus": [0.5, 0.5]}
            used.setdefault(vis, []).append(sid)
        s["transition_out"] = {"type": "cut"}
        # documentary breathing room: a 3D flight holds at least 8 s, a photo 6.5 s
        s["min_duration"] = 8.0 if s["visual"]["type"] == "video" else 6.5
        if src:
            s["claims"] = [{"text": vo, "source_url": SRC[src], "verified": True}]
        shots.append(s)
    shots[0]["vo_lead"] = 2.2
    shots[0]["min_duration"] = 7.0
    # change of place: Enceladus -> Earth and back, with a dip to black
    for s in shots:
        if s["visual"].get("file") == "assets/s7_earth_ocean.mp4":
            s["transition_out"] = {"type": "dip_black", "duration": 0.8}
    shots[-1]["min_duration"] = 8.0
    ep = {"schema_version": 2,
          "episode": {"id": "ep01", "title": "The Moon That Leaks an Ocean", "language": "en",
                      "central_question": "Is something alive in the ocean under the ice of Enceladus?"},
          "voice": {"engine": "kokoro", "voice": "am_michael", "speed": 1.0},
          "music": {"file": "assets/music/drone.wav", "credit": "Procedurally generated by us", "license": "own work", "gain_db": -15},
          "beats": [dict(id=b, name=n, **({"because": BECAUSE[b]} if b in BECAUSE else {}), **({"chapter": c, "chapter_sub": sub} if c else {})) for b, n, c, sub in BEATS],
          "shots": shots}
    for s in shots:
        if s["beat"] == "B8":
            pass
    # cards: only for beats with a chapter (render.py uses the first shot of each beat)
    (HERE / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    items = []
    for k, (url, title, cls, credit, page) in ASSETS.items():
        items.append({"id": k, "url": url, "kind": "image", "title": title, "source_class": cls, "credit": credit,
                      "source_url": page, "credit_checked": True,
                      "note": "credit line read from the source page on 2026-11-22", "shots": used.get(k, [])})
    (HERE / "asset_manifest.json").write_text(json.dumps({"episode": "ep01", "items": items}, indent=1) + "\n")
    n3 = sum(1 for s in shots if s["visual"]["type"] == "video")
    print(f"{len(shots)} shots, {n3} 3D ({n3 / len(shots):.0%}), {len(used)} real images")


if __name__ == "__main__":
    main()
