"""Builds EP02 episode.json from the owner-approved narration (EP02 draft, revised 2026-11-23 to about 9 minutes).

Pre-G2 state: every shot has a `search_query` and a `source_class`, but no asset file yet.
Only the numeric facts (and one theoretical prediction) carry a claim; their source_url stays empty and
verified stays false until checked against NASA/NOAA pages before G2.
Run: python episodes/ep02/build_episode.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

BEATS = [
    ("B1", "The light on your face", None),
    ("B2", "Earth at scale", "Start with the size of home."),
    ("B3", "The travel time", "Distance is easy to draw. Time is harder to feel."),
    ("B4", "The Sun", "Now scale up: the Sun is far larger and far farther."),
    ("B5", "The eight-minute gap", "Light is a clock. It shows us what happened in the past."),
    ("B6", "Life on Earth", "Eight minutes is a fact about light. The bigger story is what sunlight does."),
    ("B7", "The nearest other star", "Our Sun is not alone. The next star is much farther."),
    ("B8", "The closing question", "Light always shows us a little of the past."),
]

# (beat, kind, narration, visual note, claim key or None)
# kind: "3d" = OUR_CGI flight or scale graphic, "photo" = real archive image
SHOTS = [
    # 1 · The light on your face
    ("B1", "3d", "Right now, the sunlight on your face left the Sun about eight minutes ago.",
     "Flight from Earth toward the Sun", "eight minutes"),
    ("B1", "3d", "It crossed roughly 150 million kilometres of nearly empty space to reach you.",
     "Light path Sun to Earth, scale marks", "150 million km"),
    ("B1", "photo", "Nothing you see in daylight is happening in this exact moment.",
     "NASA Earth from orbit, sunlit limb", None),
    ("B1", "3d", "It is all a little bit old.",
     "Sunrise over the limb, slow push", None),
    ("B1", "photo", "Most of us never notice this, because light moves so fast that the delay is invisible.",
     "Real sunrise photo from orbit", None),
    ("B1", "3d", "But it is there, every second of every day.",
     "Sun glare over Earth", None),
    ("B1", "3d", "In this episode we will follow that light from the Sun to Earth.",
     "Light beam from Sun toward Earth", None),
    ("B1", "3d", "We will ask what the delay really means for us.",
     "Earth in frame, slow pull back", None),
    ("B1", "photo", "Along the way, we will meet the Moon, the Sun, and the nearest star beyond them.",
     "NASA Earth-Moon real image", None),
    # 2 · Earth at scale
    ("B2", "photo", "Start with home, the one place we all know.",
     "NASA Blue Marble or Earth from orbit", None),
    ("B2", "3d", "Earth is about 12,742 kilometres across, measured through its middle.",
     "Earth diameter arrow, scale label", "earth diameter"),
    ("B2", "photo", "That is a number we can picture, because we have all stood on its surface.",
     "Real surface photo, ground level", None),
    ("B2", "photo", "The Moon is much smaller, about a quarter of Earth's width.",
     "NASA Moon full-disc photo", "moon quarter"),
    ("B2", "3d", "Yet it sits roughly thirty Earth-widths away, close enough to pull on our oceans and make the tides.",
     "Earth-Moon distance arrow, 30 Earth diameters", "moon distance"),
    ("B2", "3d", "Picture thirty Earth-widths laid end to end between the two.",
     "Row of Earth-sized discs between Earth and Moon", None),
    ("B2", "3d", "That is the gap light must cross to reach the Moon.",
     "Light beam Earth to Moon", None),
    ("B2", "3d", "It is a long way for us, but a short trip for light.",
     "Pull back, Earth and Moon in frame", None),
    ("B2", "photo", "Hold that picture in mind, because every distance in this episode is measured against it.",
     "NASA Earth and Moon in one frame, real image", None),
    # 3 · The travel time
    ("B3", "3d", "Light is the fastest thing we know of; nothing carries information faster.",
     "Light beam across the frame", None),
    ("B3", "3d", "Even so, light needs time to cross space.",
     "Light beam with a moving marker", None),
    ("B3", "3d", "To reach the Moon, it takes about one and a quarter seconds.",
     "Label: LIGHT takes 1.28 s to reach the Moon", "moon light time"),
    ("B3", "photo", "That sounds quick, and it is.",
     "Earth-Moon real image, short hold", None),
    ("B3", "3d", "But distance turns into time, and time turns into a kind of delay.",
     "Distance bar converting to a clock", None),
    ("B3", "3d", "A signal sent to the Moon and back takes a few seconds.",
     "Round-trip signal arc, Earth-Moon", None),
    ("B3", "3d", "That is already enough to make a live conversation feel slightly off.",
     "Two speech bubbles with a gap", None),
    ("B3", "photo", "Engineers who control spacecraft on Mars plan around this delay, because their commands take minutes to arrive.",
     "Real Mars rover or orbiter photo", None),
    ("B3", "3d", "The farther something is, the more out of date its light becomes.",
     "Light beam stretching outward", None),
    # 4 · The Sun
    ("B4", "photo", "Now the Sun, the star that sets our clock.",
     "NASA SDO full-disc Sun image", None),
    ("B4", "3d", "It is about 109 Earth diameters across.",
     "Earth beside the Sun, scale label", "sun diameter"),
    ("B4", "3d", "Its distance from us is roughly 150 million kilometres.",
     "Sun-Earth distance arrow", "150 million km"),
    ("B4", "3d", "Astronomers call that distance one astronomical unit, the standard yardstick of the solar system.",
     "1 AU label on the distance arrow", None),
    ("B4", "photo", "Real images of the Sun show its surface in fine detail.",
     "NASA SDO close-up, real image", None),
    ("B4", "photo", "Dark sunspots, bright flares, and loops of glowing gas.",
     "NASA SDO flare or loop, real image", None),
    ("B4", "photo", "They come from spacecraft that watch the Sun all the time.",
     "Spacecraft over the Sun, real image", None),
    ("B4", "3d", "Put the size and the distance together, and you get the central number of this episode.",
     "Sun and Earth in one frame, scale on", None),
    ("B4", "3d", "Sunlight needs about eight minutes and twenty seconds to cover that gap.",
     "Label: LIGHT takes 8 min 20 s", "8 min 20 s"),
    ("B4", "photo", "Every image of the Sun you have ever seen is a snapshot of a few minutes ago.",
     "Sun image held, slow push", None),
    ("B4", "photo", "Inside the Sun, energy from nuclear fusion starts its journey.",
     "NASA solar interior diagram, real image", None),
    ("B4", "3d", "It takes a very long time to escape as light.",
     "Energy path inside the Sun, OUR_CGI", None),
    # 5 · The eight-minute gap
    ("B5", "3d", "Follow that light for a moment.",
     "Light path from the Sun surface", None),
    ("B5", "3d", "It leaves the Sun's surface, crosses empty space, and slips into Earth's atmosphere.",
     "Light path into Earth's atmosphere", None),
    ("B5", "3d", "It moves at roughly 300,000 kilometres every second.",
     "Speed label on the light beam", "speed of light"),
    ("B5", "3d", "Now imagine the Sun switched off this very second.",
     "Sun dims in the frame, clock overlay", None),
    ("B5", "3d", "You would not notice anything for eight minutes.",
     "Earth in daylight, clock running", None),
    ("B5", "3d", "The sky would look normal, the warmth on your skin would feel the same.",
     "Earth in daylight, calm pan", None),
    ("B5", "3d", "The light would keep arriving as if nothing had happened.",
     "Light beams still arriving at Earth", None),
    ("B5", "3d", "Only after those minutes would it stop.",
     "Light stream ends, Sun dark", None),
    ("B5", "3d", "Physics also says the Sun's gravity would take about the same time to change.",
     "Gravity ripple from the Sun, dashed prediction", "gravity theory"),
    ("B5", "3d", "That is a prediction we cannot test directly.",
     "Dashed outline, hold", None),
    ("B5", "3d", "What is certain is this: light always tells you the past, never the present.",
     "Light beam with a timestamp", None),
    ("B5", "photo", "Astronomers use the same idea to study the past.",
     "NASA Hubble deep field, real image", None),
    ("B5", "photo", "When you look at a distant galaxy, you are seeing it as it was long ago.",
     "Real galaxy photo, slow push", None),
    # 6 · Life on Earth
    ("B6", "3d", "Eight minutes of delay is a fact about light.",
     "Sun-Earth light path, clock", None),
    ("B6", "photo", "The bigger story is what sunlight does once it arrives.",
     "NASA Earth from orbit, real image", None),
    ("B6", "photo", "Almost every food chain on our planet starts with it.",
     "Plants and vegetation from orbit, real image", "food chain"),
    ("B6", "photo", "Plants, algae and some bacteria capture that energy and turn it into food.",
     "Phytoplankton bloom, real image", None),
    ("B6", "photo", "Animals eat them, and other animals eat those animals.",
     "Food web scene, real photo", None),
    ("B6", "3d", "Seasons, weather and the water cycle are all driven by the energy that arrives in those eight minutes.",
     "Earth with seasons and clouds, OUR_CGI", None),
    ("B6", "photo", "Sunlight also warms the ocean surface.",
     "Real ocean surface photo from orbit", None),
    ("B6", "photo", "That warmth drives currents that move heat around the planet.",
     "Ocean current satellite image, real", None),
    ("B6", "3d", "Yet there is an exception.",
     "Slow dive from sunlit ocean into dark", None),
    ("B6", "3d", "Deep in the ocean, far below the reach of sunlight, there are hydrothermal vents.",
     "Dive into the dark ocean floor, OUR_CGI", None),
    ("B6", "photo", "They release hot, chemical-rich water from Earth's interior.",
     "NOAA black smoker vent, real photo", "vent water"),
    ("B6", "photo", "Microbes there turn those chemicals into energy.",
     "Vent microbial mat, real photo", None),
    ("B6", "photo", "Life does not strictly need the Sun, even though most life on Earth depends on it.",
     "Tube worms at a vent, real photo", None),
    # 7 · The nearest other star
    ("B7", "photo", "Our Sun is the nearest star to Earth, but it is not alone.",
     "Milky Way star field, real image", None),
    ("B7", "3d", "The next nearest star is Proxima Centauri.",
     "Star ladder from the Sun to Proxima Centauri", None),
    ("B7", "3d", "Its light takes about four years to reach us.",
     "Label: 4.24 light-years", "proxima distance"),
    ("B7", "photo", "Proxima Centauri is part of a three-star system, with Alpha Centauri A and B nearby.",
     "Alpha Centauri real image, star field", None),
    ("B7", "3d", "That light set out before anyone on Earth could see it, and it has been travelling ever since.",
     "Light beam from Proxima toward Earth, timeline", None),
    ("B7", "3d", "Compare that with our own Sun, whose light needs eight minutes.",
     "Sun and Proxima side by side, light-time labels", None),
    ("B7", "photo", "Proxima Centauri is a small, faint red star.",
     "Real red dwarf or star field photo", None),
    ("B7", "photo", "It is too dim to see with the naked eye from most places.",
     "Night sky real photo, slow pull", None),
    ("B7", "3d", "Yet it follows the same rule.",
     "Light beam from a distant star", None),
    ("B7", "3d", "Every star you see is a message that left it long ago.",
     "Star field with distance marks", None),
    ("B7", "3d", "The farther the star, the older the message.",
     "Star field, depth fade", None),
    # 8 · The closing question
    ("B8", "3d", "So here is the question.",
     "Slow pull back to Earth", None),
    ("B8", "photo", "Every sunrise you have ever watched was eight minutes old by the time it reached your eyes.",
     "Sunrise from the ISS, real photo", "sunrise age"),
    ("B8", "photo", "Every star you have ever seen is older than your sense of time.",
     "Night sky star field, real photo", None),
    ("B8", "3d", "Light lets us see the universe, but it always shows us a little of the past.",
     "Light path across the frame", None),
    ("B8", "photo", "The next time you stand in sunlight, notice the warmth on your skin.",
     "Sunlight on a person's shoulder, real photo", None),
    ("B8", "photo", "Remember where it came from.",
     "Sun over Earth from orbit, real image", None),
    ("B8", "3d", "It left the Sun eight minutes ago.",
     "Light path from the Sun to Earth, final pass", None),
    ("B8", "3d", "It crossed the emptiness between us and arrived in time for you to feel it.",
     "Light reaching the viewer's frame", None),
    ("B8", "photo", "So what else in your sky is already old?",
     "Earth from orbit at night, real image", None),
]

# Numeric facts and one theoretical prediction. Sources are checked before G2.
CLAIMS = {
    "eight minutes": ("Sunlight takes about eight minutes to reach Earth",
                      "NASA Sun fact sheet (to confirm)"),
    "150 million km": ("Sun-Earth distance about 150 million km (1 AU)",
                       "NASA Sun fact sheet (to confirm)"),
    "earth diameter": ("Earth diameter about 12,742 km",
                       "NASA Earth fact sheet (to confirm)"),
    "moon quarter": ("Moon about a quarter of Earth's diameter",
                     "NASA Moon fact sheet (to confirm)"),
    "moon distance": ("Moon about 30 Earth diameters away (384,400 km / 12,742 km, derived)",
                      "NASA Moon fact sheet (to confirm)"),
    "moon light time": ("Light takes about 1.28 s to reach the Moon (384,400 km / c, derived)",
                        "derived; confirm with speed of light"),
    "sun diameter": ("Sun about 109 Earth diameters across",
                     "NASA Sun fact sheet (to confirm)"),
    "8 min 20 s": ("Sunlight takes about 8 min 20 s to reach Earth",
                   "NASA Sun fact sheet (to confirm)"),
    "speed of light": ("Light travels about 300,000 km per second",
                       "speed of light constant (to confirm)"),
    "gravity theory": ("Sun's gravity change would take about the same time as its light; theoretical prediction",
                       "general relativity; source needed"),
    "proxima distance": ("Proxima Centauri light takes about 4.24 years to reach Earth",
                         "Proxima Centauri source (to confirm)"),
    "vent water": ("Hydrothermal vents release hot, chemical-rich water",
                   "NOAA vent source (to confirm)"),
    "food chain": ("Almost every food chain starts with sunlight",
                   "NASA/NOAA source (to confirm)"),
    "sunrise age": ("Sunrise light is about eight minutes old when it reaches us",
                    "derived from the sunlight travel time"),
}

# Short keyword queries for the NASA image search (the long notes above returned 0 results, 2026-11-23).
QUERY = {
    "S003": "Earth limb ISS", "S005": "orbital sunrise", "S009": "DSCOVR moon Earth", "S010": "Blue Marble",
    "S012": "Kennedy Space Center sunrise", "S013": "full moon", "S018": "Earth and Moon", "S022": "Earthrise",
    "S026": "Curiosity rover selfie", "S028": "SDO sun", "S032": "sunspots", "S033": "coronal loops",
    "S034": "Parker Solar Probe", "S037": "solar flare", "S038": "Sun layers", "S051": "Hubble Ultra Deep Field",
    "S052": "spiral galaxy Hubble", "S054": "Earth from space", "S055": "vegetation Earth satellite",
    "S056": "phytoplankton bloom", "S057": "Merritt Island wildlife", "S059": "sun glint ocean",
    "S060": "ocean currents", "S066": "Milky Way", "S069": "Alpha Centauri", "S072": "red dwarf star",
    "S073": "night sky stars", "S078": "sunrise International Space Station", "S079": "star trails",
    "S081": "astronaut spacewalk sun", "S082": "sun over Earth", "S085": "city lights night Earth",
}


def build_shots():
    shots = []
    for i, (beat, kind, vo, note, claim_key) in enumerate(SHOTS, 1):
        sid = f"S{i:03d}"
        if kind == "3d":
            visual = {"type": "still", "source_class": "OUR_CGI",
                      "search_query": f"3D visualization: {note}",
                      "credit": "Our visualization, Solar System Scope textures where used (CC BY 4.0)",
                      "source_url": "", "credit_verified": False, "credit_short": "Visualization"}
            camera = {"move": "push_in", "strength": 0.05, "focus": [0.5, 0.5]}
        else:
            visual = {"type": "still", "source_class": "REAL_PHOTO", "search_query": QUERY.get(sid, note),
                      "credit": "", "source_url": "", "credit_verified": False, "credit_short": ""}
            camera = {"move": "push_in", "strength": 0.06, "focus": [0.5, 0.5]}
        shot = {
            "id": sid, "beat": beat, "voiceover": vo,
            "visual": visual, "camera": camera,
            "transition_out": {"type": "cut"},
            "on_screen_text": "", "label": kind == "3d",
            "min_duration": 6.5 if kind == "3d" else 6.0,  # owner target 8-9 min (2026-11-23)
        }
        if claim_key:
            text, hint = CLAIMS[claim_key]
            shot["claims"] = [{"text": text, "source_url": "", "verified": False, "source_hint": hint}]
        shots.append(shot)
    return shots


def main():
    shots = build_shots()
    shots[0]["vo_lead"] = 2.2
    shots[0]["min_duration"] = 7.0
    ep = {
        "schema_version": 2,
        "episode": {
            "id": "ep02",
            "title": "Sunlight Takes 8 Minutes to Reach Us",
            "language": "en",
            "central_question": "What does the eight-minute delay of sunlight tell us about the universe and about life on Earth?",
        },
        "voice": {"engine": "kokoro", "voice": "am_michael", "speed": 1.0},
        "beats": [
            dict(id=b, name=name, **({"because": because} if because else {}), chapter=name)
            for b, name, because in BEATS
        ],
        "shots": shots,
    }
    (HERE / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    n3 = sum(1 for s in shots if s["visual"]["source_class"] == "OUR_CGI")
    words = sum(len(s["voiceover"].split()) for s in shots)
    print(f"{len(shots)} shots, {n3} OUR_CGI ({n3 / len(shots):.0%}), {words} narration words, "
          f"{sum(len(s.get('claims', [])) for s in shots)} claims pending sources")


if __name__ == "__main__":
    main()
