"""Builds EP02 episode.json from the owner-approved narration (EP02 full draft, approved 2026-11-23).

Pre-G2 state: every shot has a `search_query` and a `source_class`, but no asset file yet.
Claims with numbers have `source_url` empty and `verified: false` until sources are checked.
Run: python episodes/ep02/build_episode.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

BEATS = [
    ("B1", "The light on your face", None, None),
    ("B2", "Earth at scale", "Start with the size of home.", None),
    ("B3", "The travel time", "Distance is easy to draw. Time is harder to feel.", None),
    ("B4", "The Sun", "Now scale up: the Sun is far larger and far farther.", None),
    ("B5", "The eight-minute gap", "Light is a clock. It shows us what happened in the past.", None),
    ("B6", "Life on Earth", "Eight minutes is a fact about light. The bigger story is what sunlight does.", None),
    ("B7", "The nearest other star", "Our Sun is not alone. The next star is much farther.", None),
    ("B8", "The closing question", "Light always shows us a little of the past.", None),
]

# (beat, kind, narration, visual note, claim or None)
# kind: "3d" = OUR_CGI flight or scale graphic, "photo" = real archive image
# claim: a short label of the number/fact; its source is filled in before G2
SHOTS = [
    # Chapter 1 · The light on your face
    ("B1", "3d", "Right now, the sunlight on your face left the Sun about eight minutes ago.",
     "Flight from Earth toward the Sun", "about eight minutes"),
    ("B1", "3d", "It crossed roughly 150 million kilometres of nearly empty space to reach you.",
     "Light path Sun to Earth, scale marks", "150 million km"),
    ("B1", "3d", "Nothing you see in daylight is happening in this exact moment.",
     "Earth sunlit limb, slow push", None),
    ("B1", "3d", "It is all a little bit old.",
     "Sunrise over the limb, slow push", None),
    ("B1", "3d", "Most of us never notice this, because light moves so fast that the delay is invisible.",
     "Earth-Sun space, slow pull", None),
    ("B1", "3d", "But it is there, every second of every day.",
     "Sun glare over Earth", None),
    ("B1", "3d", "In this episode we will follow that light from the Sun to Earth, and ask what the delay really means.",
     "Light beam from Sun toward Earth", None),
    ("B1", "photo", "We will start small, with the size of home, and climb outward toward the Sun.",
     "NASA Earth from orbit, real image", None),
    # Chapter 2 · Earth at scale
    ("B2", "photo", "Start with home.",
     "NASA Blue Marble or Earth from orbit", None),
    ("B2", "3d", "Earth is about 12,742 kilometres across, measured through its middle.",
     "Earth diameter arrow, scale label", "Earth diameter 12,742 km"),
    ("B2", "photo", "That is a number we can picture, because we have all stood on its surface.",
     "Real surface photo, ground level", None),
    ("B2", "photo", "The Moon is much smaller, about a quarter of Earth's width.",
     "NASA Moon full-disc photo", "Moon about a quarter of Earth's width"),
    ("B2", "3d", "Yet it sits roughly thirty Earth-widths away, close enough to pull on our oceans and make the tides.",
     "Earth-Moon distance arrow, 30 Earth diameters", "Moon about 30 Earth diameters away"),
    ("B2", "3d", "Picture thirty Earth-widths laid end to end between the two.",
     "Row of Earth-sized discs between Earth and Moon", None),
    ("B2", "3d", "That is the gap light must cross to reach the Moon.",
     "Light beam Earth to Moon", None),
    ("B2", "3d", "It is a long way for us, but a short trip for light.",
     "Pull back, Earth and Moon in frame", None),
    # Chapter 3 · The travel time
    ("B3", "3d", "Light is the fastest thing we know of.",
     "Light beam across the frame", "speed of light is the fastest known"),
    ("B3", "3d", "Nothing carries information faster.",
     "Signal arc, Earth to Moon", None),
    ("B3", "3d", "Even so, light needs time to cross space.",
     "Light beam with a moving marker", None),
    ("B3", "3d", "To reach the Moon, it takes about one and a quarter seconds.",
     "Label: LIGHT takes 1.28 s to reach the Moon", "light to the Moon about 1.28 s"),
    ("B3", "3d", "That sounds quick, and it is.",
     "Earth-Moon, short hold", None),
    ("B3", "3d", "But distance turns into time, and time turns into a kind of delay.",
     "Distance bar converting to a clock", None),
    ("B3", "3d", "A signal sent to the Moon and back takes a few seconds, which is already enough to make a live conversation feel slightly off.",
     "Round-trip signal arc, Earth-Moon", "round trip a few seconds"),
    ("B3", "3d", "The farther something is, the more out of date its light becomes.",
     "Light beam stretching outward", None),
    # Chapter 4 · The Sun
    ("B4", "photo", "Now the Sun.",
     "NASA SDO full-disc Sun image", None),
    ("B4", "3d", "It is about 109 Earth diameters across.",
     "Earth beside the Sun, scale label", "Sun about 109 Earth diameters"),
    ("B4", "3d", "Its distance from us is roughly 150 million kilometres, which astronomers call one astronomical unit, the standard yardstick of the solar system.",
     "Sun-Earth distance arrow, 1 AU label", "1 AU about 150 million km"),
    ("B4", "photo", "Real images of the Sun show its surface in fine detail: dark sunspots, bright flares, and loops of glowing gas.",
     "NASA SDO close-up, real image", None),
    ("B4", "photo", "They come from spacecraft that watch the Sun all the time.",
     "Spacecraft over the Sun, real image", None),
    ("B4", "3d", "Put the size and the distance together, and you get the central number of this episode.",
     "Sun and Earth in one frame, scale on", None),
    ("B4", "3d", "Sunlight needs about eight minutes and twenty seconds to cover that gap.",
     "Label: LIGHT takes 8 min 20 s", "sunlight 8 min 20 s to Earth"),
    ("B4", "photo", "Every image of the Sun you have ever seen is a snapshot of a few minutes ago.",
     "Sun image held, slow push", None),
    # Chapter 5 · The eight-minute gap
    ("B5", "3d", "Follow that light for a moment.",
     "Light path from the Sun surface", None),
    ("B5", "3d", "It leaves the Sun's surface, crosses empty space, and slips into Earth's atmosphere, moving at roughly 300,000 kilometres every second.",
     "Light path into Earth's atmosphere, speed label", "light about 300,000 km/s"),
    ("B5", "3d", "Now imagine the Sun switched off this very second.",
     "Sun dims in the frame, clock overlay", None),
    ("B5", "3d", "You would not notice anything for eight minutes.",
     "Earth in daylight, clock running", None),
    ("B5", "3d", "The sky would look normal, the warmth on your skin would feel the same, and the light would keep arriving as if nothing had happened.",
     "Light beams still arriving at Earth", None),
    ("B5", "3d", "Only after those minutes would it stop.",
     "Light stream ends, Sun dark", None),
    ("B5", "3d", "Physics also says the Sun's gravity would take about the same time to change, though that is a theoretical prediction we cannot test.",
     "Gravity ripple from the Sun, dashed prediction", "gravity change time, theoretical"),
    ("B5", "3d", "What is certain is this: light always tells you the past, never the present.",
     "Light beam with a timestamp", None),
    # Chapter 6 · Life on Earth
    ("B6", "3d", "Eight minutes of delay is a fact about light.",
     "Sun-Earth light path, clock", None),
    ("B6", "photo", "The bigger story is what sunlight does once it arrives.",
     "NASA Earth from orbit, real image", None),
    ("B6", "photo", "Almost every food chain on our planet starts with it.",
     "Plants and vegetation from orbit, real image", "almost every food chain starts with sunlight"),
    ("B6", "photo", "Plants, algae and some bacteria capture that energy and turn it into food.",
     "Phytoplankton bloom, real image", None),
    ("B6", "photo", "Animals eat them, and other animals eat those animals.",
     "Food web scene, real photo", None),
    ("B6", "3d", "Seasons, weather and the water cycle are all driven by the energy that arrives in those eight minutes.",
     "Earth with seasons and clouds, OUR_CGI", None),
    ("B6", "3d", "Yet there is an exception.",
     "Slow dive from sunlit ocean into dark", None),
    ("B6", "photo", "Deep in the ocean, far below the reach of sunlight, hydrothermal vents release hot, chemical-rich water from Earth's interior.",
     "NOAA black smoker vent, real photo", "vents release hot chemical-rich water"),
    ("B6", "photo", "Microbes there turn those chemicals into energy.",
     "Vent microbial mat, real photo", None),
    ("B6", "photo", "Life does not strictly need the Sun, even though most life on Earth depends on it.",
     "Tube worms at a vent, real photo", "most life depends on the Sun"),
    # Chapter 7 · The nearest other star
    ("B7", "photo", "Our Sun is the nearest star to Earth, but it is not alone.",
     "Milky Way star field, real image", None),
    ("B7", "3d", "The next nearest star is Proxima Centauri.",
     "Star ladder from the Sun to Proxima Centauri", "Proxima Centauri is the next nearest star"),
    ("B7", "3d", "Its light takes about four years to reach us.",
     "Label: 4.24 light-years", "Proxima about 4.24 light-years"),
    ("B7", "3d", "That light set out before anyone on Earth could see it, and it has been travelling ever since.",
     "Light beam from Proxima toward Earth, timeline", None),
    ("B7", "3d", "Compare that with our own Sun, whose light needs eight minutes.",
     "Sun and Proxima side by side, light-time labels", None),
    ("B7", "photo", "Proxima Centauri is a small, faint red star, too dim to see with the naked eye from most places.",
     "Real image of a red dwarf or star field", "Proxima too dim to see by eye from most places"),
    ("B7", "3d", "Yet it follows the same rule.",
     "Light beam from a distant star", None),
    ("B7", "3d", "Every star you see is a message that left it long ago, and the farther the star, the older the message.",
     "Star field with distance marks", None),
    # Chapter 8 · The closing question
    ("B8", "3d", "So here is the question.",
     "Slow pull back to Earth", None),
    ("B8", "photo", "Every sunrise you have ever watched was eight minutes old by the time it reached your eyes.",
     "Sunrise from the ISS, real photo", "sunrise light about eight minutes old"),
    ("B8", "photo", "Every star you have ever seen is older than your sense of time.",
     "Night sky star field, real photo", None),
    ("B8", "3d", "Light lets us see the universe, but it always shows us a little of the past.",
     "Light path across the frame", None),
    ("B8", "photo", "The next time you stand in sunlight, notice the warmth on your skin and remember where it came from.",
     "Sunlight on a person's shoulder, real photo", None),
    ("B8", "3d", "It left the Sun eight minutes ago, crossed the emptiness between us, and arrived in time for you to feel it.",
     "Light path from the Sun to Earth, final pass", None),
    ("B8", "photo", "What else in your sky is already old?",
     "Earth from orbit at night, real image", None),
]

# Claims with numbers: source_url stays empty and verified false until checked before G2.
CLAIM_SOURCE_HINT = {
    "about eight minutes": "NASA Sun fact sheet (to confirm)",
    "150 million km": "NASA Sun fact sheet, 1 AU (to confirm)",
    "Earth diameter 12,742 km": "NASA Earth fact sheet (to confirm)",
    "Moon about a quarter of Earth's width": "NASA Moon fact sheet (to confirm)",
    "Moon about 30 Earth diameters away": "384,400 km / 12,742 km, derived (to confirm)",
    "light to the Moon about 1.28 s": "derived from 384,400 km / c (to confirm)",
    "Sun about 109 Earth diameters": "NASA Sun fact sheet (to confirm)",
    "1 AU about 150 million km": "NASA Sun fact sheet (to confirm)",
    "sunlight 8 min 20 s to Earth": "NASA Sun fact sheet (to confirm)",
    "light about 300,000 km/s": "speed of light (to confirm)",
    "gravity change time, theoretical": "theoretical prediction; source needed",
    "Proxima Centauri is the next nearest star": "Proxima fact check (to confirm)",
    "Proxima about 4.24 light-years": "Proxima Centauri source (to confirm)",
    "Proxima too dim to see by eye from most places": "Proxima source (to confirm)",
    "vents release hot chemical-rich water": "NOAA vent source (to confirm)",
    "most life depends on the Sun": "NASA/NOAA source (to confirm)",
    "almost every food chain starts with sunlight": "source needed",
    "sunrise light about eight minutes old": "derived from sunlight travel time",
    "round trip a few seconds": "derived from distance / c (to confirm)",
    "speed of light is the fastest known": "source needed",
}


def build_shots():
    shots = []
    for i, (beat, kind, vo, note, claim) in enumerate(SHOTS, 1):
        sid = f"S{i:03d}"
        if kind == "3d":
            visual = {"type": "still", "source_class": "OUR_CGI",
                      "search_query": f"3D visualization: {note}",
                      "credit": "Our visualization, Solar System Scope textures where used (CC BY 4.0)",
                      "source_url": "", "credit_verified": False,
                      "credit_short": "Visualization"}
            camera = {"move": "push_in", "strength": 0.05, "focus": [0.5, 0.5]}
        else:
            visual = {"type": "still", "source_class": "REAL_PHOTO",
                      "search_query": note,
                      "credit": "", "source_url": "", "credit_verified": False,
                      "credit_short": ""}
            camera = {"move": "push_in", "strength": 0.06, "focus": [0.5, 0.5]}
        shot = {
            "id": sid, "beat": beat, "voiceover": vo,
            "visual": visual, "camera": camera,
            "transition_out": {"type": "cut"},
            "on_screen_text": "", "label": kind == "3d",
            "min_duration": 8.0 if kind == "3d" else 6.5,
        }
        if claim:
            shot["claims"] = [{"text": claim, "source_url": "", "verified": False,
                               "source_hint": CLAIM_SOURCE_HINT.get(claim, "source needed")}]
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
            dict(id=b, name=name,
                 **({"because": because} if because else {}),
                 **({"chapter": name} if name else {}))
            for b, name, because, _ in BEATS
        ],
        "shots": shots,
    }
    (HERE / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    n3 = sum(1 for s in shots if s["visual"]["source_class"] == "OUR_CGI")
    print(f"{len(shots)} shots, {n3} OUR_CGI ({n3 / len(shots):.0%}), "
          f"{sum(len(s.get('claims', [])) for s in shots)} claims pending sources")


if __name__ == "__main__":
    main()
