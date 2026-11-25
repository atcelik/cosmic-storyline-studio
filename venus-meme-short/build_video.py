#!/usr/bin/env python3
"""
Cosmic Storyline - automated MP4 builder
=========================================
Topic : "Why Venus Is a Literal Nightmare"  (swap BEATS below for any topic)
Output: cosmic_storyline_out.mp4  (1920x1080, 30 fps, H.264 + AAC)

Pipeline
  1. Timeline   - BEATS -> exact timecodes (2.5 s resets, 0.6 s comedy vacuums)
  2. Voiceover  - edge-tts per beat (cached), time-fitted to its slot
  3. Audio mix  - music bed + SFX + VO, ducking, true digital-silence vacuums
  4. Frames     - Pillow space scenes, micro-zooms, shakes, meme cards,
                  1.3 s NASA-style telemetry badges, karaoke captions
  5. Encode     - moviepy (v1 or v2) if installed, else a direct ffmpeg pipe

Optional folders (everything has a synthesized fallback, nothing is required):
  assets/<asset_or_beat_id>.(png|jpg|jpeg|webp|mp4)   e.g. assets/venera13.jpg
  assets/font_bold.ttf, assets/font_meme.ttf
  sfx/<name>.(wav|mp3|ogg|m4a|flac)   names: ping pop boom drop crunch beep
                                       whoosh riser sizzle scratch
  sfx/music_upbeat.*, sfx/music_tense.*   (looped)

Install:  pip install moviepy pillow numpy edge-tts      (+ ffmpeg on PATH)
Run:      python build_video.py
Quick:    python build_video.py --max-seconds 15 --out test.mp4
Tables:   python build_video.py --table            (prints the production table)
          python build_video.py --export-json tl.json
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- settings --
TOPIC = "Why Venus Is a Literal Nightmare"
CHANNEL = "COSMIC STORYLINE"
VOICE = "en-US-AndrewNeural"          # or en-US-ChristopherNeural
TTS_RATE = "+12%"
W, H, FPS, SR = 1920, 1080, 30, 44100
VACUUM = 0.60          # seconds of 0-sample silence before a punchline
TEL_DUR = 1.30         # telemetry popup lifetime
TEL_AT = 0.60          # telemetry offset inside a beat
MEME_AT = 0.15         # meme card pop offset inside a beat
RESET = 2.50           # sensory reset period (micro-zoom 100% -> 108%)
ZOOM_MAX = 0.08
WPS = 3.1              # words per second used to size beats

ROOT = Path(__file__).resolve().parent
ASSETS, SFX_DIR, CACHE = ROOT / "assets", ROOT / "sfx", ROOT / "build_cache"

# ------------------------------------------------------------------- beats --
# vo: voiceover | meme: on-screen reaction | tel: telemetry badge | scene:
# background | vac: 0.6 s comedy vacuum BEFORE this beat, impact at its start
# impact: boom|drop | sfx: [(offset, name)] | music: up|tense
# vis / aud: human notes for the production table
BEATS = [
    dict(vo="Venus looks like Earth's cute little twin sister.", meme="awww (wholesome)", tel=None,
         scene="earthvenus", music="up", sfx=[(0.0, "ping")],
         vis="Earth + Venus side by side, slow push 100→108%", aud="Upbeat synth loop starts, soft ping"),
    dict(vo="Same size. Same rocky body. Basically Earth... but beige.", meme="EARTH 2.0??", tel="DIAMETER: 95% OF EARTH",
         scene="earthvenus", music="up", sfx=[(1.6, "pop")],
         vis="Snap-zoom on Venus at 2.5 s reset, tilt 2°", aud="Loop continues, pop on 'beige', riser into vacuum"),
    dict(vo="Venus would crush you, cook you, and corrode you. Pick your fighter.", meme="PICK YOUR FIGHTER", tel=None,
         scene="globe_hot", vac=True, impact="boom", music="tense",
         vis="0.6 s frozen frame → white flash, screen shake, punch-in 115%", aud="0 dB SILENCE 0.6 s → Vine-boom impact, tense drone"),
    dict(vo="But wait. Mercury is way closer to the Sun. So why is Venus hotter?", meme="MATH ISN'T MATHING", tel="MERCURY MAX: 430°C",
         scene="compare", music="up", sfx=[(0.0, "scratch")],
         vis="Mercury vs Venus split, micro-zoom alternates L/R", aud="Record scratch, loop back in  ⟶ OPEN LOOP #1"),
    dict(vo="Hold that thought. First, let's land. You step out of your ship and...", meme="POV: you landed", tel=None,
         scene="clouds", music="up", sfx=[(0.2, "whoosh"), (1.8, "whoosh")],
         vis="Fast descent through cloud deck, zoom 100→108% twice", aud="Whooshes on each reset"),
    dict(vo="The air is so thick, it's like standing 900 meters underwater.", meme="SUBMARINE MODE", tel="PRESSURE: 92 BAR",
         scene="surface", music="tense", sfx=[(0.6, "beep")],
         vis="Surface reveal, heavy vignette", aud="Music drops to tense bed, telemetry beep"),
    dict(vo="Gravity is 90% of Earth's, so you'd feel almost normal. For about one second.", meme="vibes: normal (for 1s)", tel="GRAVITY: 0.9 G",
         scene="surface", music="tense", sfx=[(0.6, "beep")],
         vis="Push toward the horizon, anchor shifts at reset", aud="Beep, low heartbeat kick"),
    dict(vo="Then your lungs fold like a lawn chair.", meme="lawn_chair.exe", tel=None,
         scene="surface", music="tense", sfx=[(0.9, "crunch")],
         vis="Micro shake on 'fold'", aud="Crunch SFX, riser into vacuum"),
    dict(vo="And the ground? 465 degrees Celsius.", meme="NOT A TYPO", tel="SURFACE: +465°C",
         scene="surface_hot", vac=True, impact="drop", music="tense", sfx=[(0.5, "sizzle")],
         vis="Freeze → red flash, shake, punch-in", aud="0 dB SILENCE 0.6 s → bass drop + sizzle"),
    dict(vo="Hotter than a pizza oven. Lead would literally melt into a puddle.", meme="pizza oven: weak", tel="LEAD MELTS: 327°C",
         scene="surface_hot", music="up", sfx=[(0.6, "beep")],
         vis="Red-hot ground, zoom anchors right", aud="Upbeat loop returns (ironic), beep"),
    dict(vo="Day, night, pole, equator. Same temperature. There is no shade. There is no escape.", meme="NO SHADE (literally)", tel=None,
         scene="globe_hot", music="up", sfx=[(2.6, "pop")],
         vis="Globe rotates, 2 resets, 4-corner anchor cycle", aud="Pop on 'no escape'"),
    dict(vo="Okay, look up. Clouds! Nice, fluffy... sulfuric acid clouds.", meme="fluffy?? (NO)", tel=None,
         scene="clouds", music="up", sfx=[(1.8, "record")],
         vis="Tilt up to cloud deck", aud="Music stutter on 'sulfuric'"),
    dict(vo="It rains acid up there. But it's so hot the rain evaporates before it lands.", meme="rain: nah I'm good", tel=None,
         scene="clouds", music="up", sfx=[(0.3, "sizzle")],
         vis="Cloud deck, anchor jumps each 2.5 s reset", aud="Sizzle, loop continues"),
    dict(vo="And the air you're not breathing? 96.5% carbon dioxide.", meme="breathable? NO", tel="CO₂: 96.5%",
         scene="clouds", music="up", sfx=[(0.6, "beep")],
         vis="Telemetry badge flickers in (scanner style)", aud="Telemetry beep"),
    dict(vo="Which brings us back to Mercury. Almost no air, so its heat just leaks into space.", meme="mercury: shivering", tel="MERCURY NIGHT: −180°C",
         scene="compare", music="up", sfx=[(0.6, "beep")],
         vis="Back to split screen, zoom on Mercury", aud="Beep  ⟶ starts CLOSING LOOP #1"),
    dict(vo="Venus? That thick CO2 blanket traps everything. A runaway greenhouse effect.", meme="THE BLANKET IS THE PROBLEM", tel=None,
         scene="globe_hot", music="tense",
         vis="Venus glows hotter each reset", aud="Tension riser into vacuum"),
    dict(vo="Venus didn't turn the heat up. It ripped the knob off.", meme="ZERO CHILL", tel=None,
         scene="globe_hot", vac=True, impact="boom", music="up",
         vis="Freeze → flash, shake, punch-in", aud="0 dB SILENCE → Vine boom  ⟶ LOOP #1 CLOSED"),
    dict(vo="So would anyone be brave enough to land a robot here? The Soviet Union: bet.", meme="BET.", tel=None,
         scene="lander", music="up", sfx=[(2.9, "ping")],
         vis="Lander reveal, push in", aud="Ping on 'bet'  ⟶ OPEN LOOP #2"),
    dict(vo="Their Venera landers were basically armored pressure cookers with cameras.", meme="built different", tel="VENERA 7: 1ST LANDING 1970",
         scene="lander", music="up", sfx=[(0.6, "beep")],
         vis="Push on lander, 2.5 s reset", aud="Beep"),
    dict(vo="In 1982, Venera 13 sent back the first color photos from the surface.", meme="first pics from hell", tel="VENERA 13: MAR 1982",
         scene="lander", asset="venera13", music="up", sfx=[(0.6, "beep")],
         vis="Real Venera 13 panorama (assets/venera13.jpg)", aud="Camera shutter-ish pop"),
    dict(vo="Engineers hoped it would survive about 32 minutes.", meme="goal: 32 min", tel="DESIGN LIFE: 32 MIN",
         scene="lander", music="tense", sfx=[(0.6, "beep")],
         vis="Slow push, countdown feel", aud="Tense bed, riser into vacuum"),
    dict(vo="It lasted 127.", meme="ABSOLUTE UNIT", tel="SURVIVED: 127 MIN",
         scene="lander", vac=True, impact="boom", music="up",
         vis="Freeze → flash, punch-in 115%", aud="0 dB SILENCE → boom  ⟶ LOOP #2 CLOSED"),
    dict(vo="Then it got cooked and crushed. Rest in pieces, king.", meme="o7", tel=None,
         scene="lander", music="up", sfx=[(1.8, "crunch")],
         vis="Lander tint red, slow zoom out", aud="Crunch on 'crushed'"),
    dict(vo="But the part that really breaks my brain? The clock.", meme="wait what", tel=None,
         scene="orbit", music="up", sfx=[(0.0, "scratch")],
         vis="Orbit diagram, scratch-cut", aud="Record scratch  ⟶ OPEN LOOP #3"),
    dict(vo="Venus spins so slowly, one full turn takes 243 Earth days.", meme="slowest spinner", tel="1 SPIN = 243 EARTH DAYS",
         scene="orbit", music="up", sfx=[(0.6, "beep")],
         vis="Zoom onto spin arrow", aud="Beep"),
    dict(vo="But one lap around the Sun takes just 225.", meme="hmm...", tel="1 ORBIT = 225 EARTH DAYS",
         scene="orbit", music="tense", sfx=[(0.6, "beep")],
         vis="Zoom onto orbit arrow", aud="Beep, riser into vacuum"),
    dict(vo="Its day is longer than its year.", meme="BIRTHDAY BEFORE BEDTIME", tel=None,
         scene="orbit", vac=True, impact="boom", music="up",
         vis="Freeze → flash, shake", aud="0 dB SILENCE → boom  ⟶ LOOP #3 CLOSED"),
    dict(vo="Oh, and it spins backwards. The Sun rises in the west.", meme="Venus: built different", tel="ROTATION: RETROGRADE",
         scene="orbit", music="up", sfx=[(0.3, "scratch")],
         vis="Image flips horizontally on reset", aud="Reverse-scratch"),
    dict(vo="Meanwhile the cloud tops race around at 360 kilometers per hour.", meme="speedrun any%", tel="CLOUD WINDS: 360 KM/H",
         scene="clouds", music="up", sfx=[(0.2, "whoosh"), (0.6, "beep")],
         vis="Cloud layer, fast pan + zoom", aud="Whoosh + beep"),
    dict(vo="They lap the whole planet in about four days. The planet itself? Still on day one.", meme="clouds: 4 days / planet: 243", tel=None,
         scene="globe", music="up", sfx=[(2.8, "pop")],
         vis="Globe with fast cloud bands", aud="Pop on 'day one'"),
    dict(vo="From Earth, it's the brightest planet in our sky. Pretty from far, far from pretty.", meme="far from pretty", tel="BRIGHTEST PLANET IN SKY",
         scene="globe", music="up", sfx=[(0.6, "beep")],
         vis="Pull back to starfield", aud="Beep"),
    dict(vo="Now the weirdest part. On its highest mountains, scientists think there's frost.", meme="frost?? on VENUS??", tel=None,
         scene="mountains", music="tense",
         vis="Mountain silhouettes, slow push", aud="Tense bed, riser into vacuum  ⟶ OPEN LOOP #4"),
    dict(vo="Not ice. Metal.", meme="METAL.", tel=None,
         scene="mountains", vac=True, impact="drop", music="up",
         vis="Freeze → flash, shake, punch-in", aud="0 dB SILENCE → bass drop"),
    dict(vo="NASA's Magellan radar saw weirdly shiny mountaintops. Best guess? Lead and bismuth compounds.", meme="chemistry jumpscare", tel="MAGELLAN RADAR: 1990–94",
         scene="mountains", music="up", sfx=[(0.6, "beep")],
         vis="Zoom onto the silver peaks", aud="Beep"),
    dict(vo="Heavy metal snow. Venus has the most metal weather in the solar system.", meme="HEAVY METAL SNOW", tel=None,
         scene="mountains", music="up", sfx=[(0.0, "ping")],
         vis="Shake on 'metal', 2 resets", aud="Ping  ⟶ LOOP #4 CLOSED"),
    dict(vo="Quick recap of Earth's twin: 465 degrees, 92 times the pressure, acid clouds...", meme="RECAP SPEEDRUN", tel="SURFACE: +465°C",
         scene="globe_hot", music="up", sfx=[(0.6, "beep")],
         vis="Hot globe, punchy resets", aud="Beep"),
    dict(vo="...a day longer than its year, spinning backwards, with metal snow.", meme="RECAP: ALL BAD", tel="1 DAY > 1 YEAR",
         scene="orbit", music="up", sfx=[(0.6, "beep")],
         vis="Orbit flash-back", aud="Beep"),
    dict(vo="And some scientists think it might once have had oceans.", meme="oceans?? (maybe)", tel="STATUS: HYPOTHESIS",
         scene="earthvenus_blue", music="tense", sfx=[(0.6, "beep")],
         vis="Back to the twin shot, Venus tinted ocean-blue", aud="Tense, soft"),
    dict(vo="Then the greenhouse effect went full send.", meme="FULL SEND", tel=None,
         scene="globe_hot", music="tense",
         vis="Hard cut to Venus glowing red-hot", aud="Big riser into final vacuum"),
    dict(vo="Earth's twin? More like Earth's evil twin who got way too into saunas.", meme="EVIL TWIN UNLOCKED", tel=None,
         scene="earthvenus", vac=True, impact="boom", music="up",
         vis="Freeze → flash, shake, punch-in → HARD CUT TO BLACK", aud="0 dB SILENCE → boom → PEAK CUT (no outro)"),
]

TITLES = [
    "Venus Is 465°C and It Only Gets Worse",
    "This Robot Survived 127 Min on Venus",
    "Venus: 92x Pressure, 243-Day Spin",
]

# ----------------------------------------------------------------- helpers --
def log(*a):
    print("[cosmic]", *a, flush=True)


def _words(s: str) -> int:
    return len([w for w in s.replace("...", " ").split() if w.strip(".,?!")])


def build_timeline(beats=BEATS):
    """Fixed, deterministic timecodes shared by the HTML preview and the MP4."""
    out, t = [], 0.0
    for i, b in enumerate(beats):
        nxt = beats[i + 1] if i + 1 < len(beats) else None
        vo_off = 0.35 if b.get("vac") else 0.10
        speak = max(1.2, _words(b["vo"]) / WPS)
        dur = vo_off + speak + 0.25
        dur = max(dur, 2.4)
        tail = VACUUM if (nxt and nxt.get("vac")) else 0.0
        if nxt is None:
            dur = vo_off + speak + 0.15          # peak cut: end right on the line
        dur = round(dur + tail, 2)
        e = dict(b)
        e.update(i=i, id=f"B{i+1:02d}", start=round(t, 3), end=round(t + dur, 3),
                 vo_start=round(t + vo_off, 3), vo_max=round(dur - vo_off - tail - 0.05, 3),
                 vac_window=[round(t - VACUUM, 3), round(t, 3)] if b.get("vac") else None,
                 sfx=[list(x) for x in b.get("sfx", [])])
        out.append(e)
        t += dur
    return out, round(t, 3)


def tc(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:05.2f}"


def markdown_table(tl):
    rows = ["| Timecode | Voiceover Line (Punchy English) | On-Screen Meme / Telemetry Text | Visual & Zoom Action | Music & SFX Cue |",
            "|---|---|---|---|---|"]
    for b in tl:
        meme = f"**{b['meme']}**" + (f" · `{b['tel']}` (1.3 s)" if b.get("tel") else "")
        rows.append(f"| {tc(b['start'])}–{tc(b['end'])} | {b['vo']} | {meme} | {b['vis']} | {b['aud']} |")
    return "\n".join(rows)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install it (https://ffmpeg.org) or `pip install imageio-ffmpeg`.")


FFMPEG = None


def decode_audio(path: Path, tempo: float | None = None) -> np.ndarray:
    cmd = [FFMPEG, "-v", "error", "-i", str(path)]
    if tempo and abs(tempo - 1) > 1e-3:
        cmd += ["-filter:a", f"atempo={tempo:.4f}"]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore")[:300])
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def find_file(folder: Path, stem: str, exts):
    for e in exts:
        p = folder / f"{stem}{e}"
        if p.exists():
            return p
    return None


AUDIO_EXT = (".wav", ".mp3", ".ogg", ".m4a", ".flac")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

# ------------------------------------------------------------- synth audio --
_rng = np.random.default_rng(7)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _sweep(f0, f1, d, shape="exp"):
    t = _t(d)
    if shape == "exp":
        f = f0 * (f1 / f0) ** (t / d)
    else:
        f = f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _noise(d):
    return _rng.uniform(-1, 1, int(d * SR))


def _onepole(x, a):
    """Simple low-pass; a may be scalar or array (0..1, higher = brighter)."""
    y = np.empty_like(x)
    a = np.broadcast_to(np.asarray(a, dtype=np.float64), x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _env(d, attack=0.003, decay=None):
    t = _t(d)
    e = np.minimum(1, t / max(attack, 1e-4))
    if decay:
        e *= np.exp(-t / decay)
    return e


def synth(name: str) -> np.ndarray:
    if name == "ping":
        d = 0.6
        x = (np.sin(2 * np.pi * 1318.5 * _t(d)) + 0.5 * np.sin(2 * np.pi * 1975.5 * _t(d))) * _env(d, decay=0.16)
        return 0.35 * x
    if name == "pop":
        d = 0.12
        return 0.5 * _sweep(380, 950, d) * _env(d, 0.002, 0.04)
    if name == "boom":            # vine-boom style
        d = 1.1
        body = _sweep(120, 36, d) * _env(d, 0.002, 0.33)
        click = np.zeros_like(body)
        n = int(0.012 * SR)
        click[:n] = _noise(0.012) * np.linspace(1, 0, n)
        x = np.tanh(3.2 * (body + 0.6 * click))
        return 0.95 * x
    if name == "drop":            # bass drop
        d = 1.6
        x = _sweep(170, 30, d) * _env(d, 0.003, 0.6) + 0.5 * _sweep(85, 28, d) * _env(d, 0.003, 0.8)
        return 0.9 * np.tanh(2.2 * x)
    if name == "crunch":
        d = 0.32
        n = _noise(d)
        hp = n - _onepole(n, 0.25)
        am = (np.sin(2 * np.pi * 37 * _t(d)) > 0).astype(float) * 0.7 + 0.3
        return 0.55 * hp * am * _env(d, 0.002, 0.09)
    if name == "beep":
        d = 0.2
        t = _t(d)
        sq = np.sign(np.sin(2 * np.pi * 2093 * t))
        gate = ((t < 0.06) | ((t > 0.1) & (t < 0.16))).astype(float)
        return 0.12 * sq * gate
    if name == "whoosh":
        d = 0.45
        n = _noise(d)
        a = 0.02 + 0.35 * np.sin(np.pi * _t(d) / d) ** 2
        return 0.4 * _onepole(n, a) * np.sin(np.pi * _t(d) / d)
    if name == "riser":
        d = 1.5
        t = _t(d)
        n = _noise(d)
        x = 0.5 * _onepole(n, 0.02 + 0.5 * (t / d) ** 2) + 0.25 * _sweep(180, 1900, d)
        return 0.38 * x * (t / d) ** 1.6
    if name == "sizzle":
        d = 0.9
        n = _noise(d)
        return 0.18 * (n - _onepole(n, 0.3)) * _env(d, 0.02, 0.35)
    if name in ("scratch", "record"):
        d = 0.38
        t = _t(d)
        f = 520 + 380 * np.sin(2 * np.pi * 7 * t)
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        n = _noise(d) * 0.4
        return 0.32 * _onepole(saw + n, 0.25) * _env(d, 0.004, 0.18)
    return np.zeros(int(0.1 * SR))


_SFX_CACHE: dict[str, np.ndarray] = {}


def get_sfx(name: str) -> np.ndarray:
    if name not in _SFX_CACHE:
        p = find_file(SFX_DIR, name, AUDIO_EXT)
        x = None
        if p:
            try:
                x = decode_audio(p)
                log(f"sfx '{name}' <- {p.name}")
            except Exception as e:
                log(f"could not decode {p}: {e} - using synth")
        _SFX_CACHE[name] = x if x is not None else synth(name).astype(np.float32)
    return _SFX_CACHE[name]


def synth_music(total: float, mode: str) -> np.ndarray:
    """Upbeat 120 BPM chip-pop loop, or a tense drone + heartbeat bed."""
    n = int(total * SR) + SR
    out = np.zeros(n, dtype=np.float32)
    step = 0.125  # 16th at 120 BPM

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += gain * sig[: j - i]

    if mode == "up":
        prog = [(261.63, 329.63, 392.00), (196.00, 246.94, 293.66), (220.00, 261.63, 329.63), (174.61, 220.00, 261.63)]
        bass = [65.41, 49.00, 55.00, 43.65]
        stab_d = 0.11
        tt = _t(stab_d)
        for k in range(int(total / step) + 1):
            t0 = k * step
            bar = int(t0 // 2) % 4
            s16 = k % 16
            if s16 % 4 == 2:  # offbeat chord stabs
                ch = sum(np.sign(np.sin(2 * np.pi * f * 2 * tt)) for f in prog[bar]) / 3
                add(ch * np.exp(-tt / 0.05) * 0.10, t0)
            if s16 % 4 == 0:  # bass + kick
                bd = 0.22
                bt = _t(bd)
                tri = 2 * np.abs(2 * ((bass[bar] * bt) % 1) - 1) - 1
                add(tri * np.exp(-bt / 0.12) * 0.22, t0)
                if s16 in (0, 8):
                    add(_sweep(140, 45, 0.18) * _env(0.18, 0.002, 0.06) * 0.35, t0)
            if s16 % 2 == 0:  # hats
                h = _noise(0.04)
                add((h - _onepole(h, 0.5)) * np.exp(-_t(0.04) / 0.012) * 0.06, t0)
            if s16 in (4, 12):  # clap
                c = _noise(0.12)
                add(_onepole(c, 0.4) * np.exp(-_t(0.12) / 0.03) * 0.12, t0)
            if s16 in (3, 7, 11, 14):  # arp sparkle
                f = prog[bar][s16 % 3] * 4
                add(np.sin(2 * np.pi * f * _t(0.09)) * np.exp(-_t(0.09) / 0.03) * 0.04, t0)
    else:
        t = np.arange(n) / SR
        drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.3 * np.sin(2 * np.pi * 0.2 * t)))
        out += (0.10 * drone * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t))).astype(np.float32)
        hb = _sweep(90, 40, 0.16) * _env(0.16, 0.002, 0.05) * 0.4
        for k in range(int(total) + 1):
            add(hb, k * 1.0)
            add(hb * 0.6, k * 1.0 + 0.28)
        pad = np.sin(2 * np.pi * 880 * t) * 0.012 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
        out += pad.astype(np.float32)
    return out[: int(total * SR)]


def music_bed(total: float, mode: str) -> np.ndarray:
    p = find_file(SFX_DIR, f"music_{'upbeat' if mode == 'up' else 'tense'}", AUDIO_EXT)
    if p:
        try:
            x = decode_audio(p)
            reps = int(math.ceil(total * SR / max(1, len(x))))
            log(f"music '{mode}' <- {p.name}")
            return 0.5 * np.tile(x, reps)[: int(total * SR)]
        except Exception as e:
            log(f"music file failed ({e}); using synth")
    return synth_music(total, mode)

# ------------------------------------------------------------------ voice ---
async def _edge(text, voice, rate, path):
    import edge_tts  # noqa: WPS433
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def make_voiceover(tl, voice, rate, enabled=True):
    """Returns list[np.ndarray|None] aligned to beats (already fitted)."""
    CACHE.mkdir(exist_ok=True)
    res = []
    warned = False
    for b in tl:
        clip = None
        if enabled:
            key = hashlib.md5(f"{voice}|{rate}|{b['vo']}".encode()).hexdigest()[:12]
            mp3 = CACHE / f"vo_{b['id']}_{key}.mp3"
            try:
                if not mp3.exists():
                    asyncio.run(_edge(b["vo"], voice, rate, mp3))
                clip = decode_audio(mp3)
                # trim leading/trailing silence from TTS
                nz = np.where(np.abs(clip) > 0.01)[0]
                if len(nz):
                    clip = clip[max(0, nz[0] - 200): nz[-1] + 800]
                max_len = int(b["vo_max"] * SR)
                if len(clip) > max_len:
                    tempo = min(1.45, len(clip) / max_len)
                    clip = decode_audio(mp3, tempo=tempo)
                    nz = np.where(np.abs(clip) > 0.01)[0]
                    if len(nz):
                        clip = clip[max(0, nz[0] - 200): nz[-1] + 800]
                    if len(clip) > max_len:
                        f = int(0.03 * SR)
                        clip = clip[:max_len]
                        clip[-f:] *= np.linspace(1, 0, f)
                    log(f"{b['id']}: VO sped x{tempo:.2f} to fit {b['vo_max']:.2f}s")
            except Exception as e:
                if not warned:
                    log(f"edge-tts unavailable ({type(e).__name__}: {str(e)[:120]}). "
                        "Continuing with captions only (silent VO). Check internet / `pip install edge-tts`.")
                    warned = True
                clip = None
        res.append(clip)
    return res


def mix_audio(tl, total, vo_clips) -> np.ndarray:
    n = int(total * SR)
    up, tense = music_bed(total, "up"), music_bed(total, "tense")
    mode = np.zeros(n, dtype=np.float32)
    for b in tl:
        i0, i1 = int(b["start"] * SR), int(b["end"] * SR)
        mode[i0:i1] = 1.0 if b["music"] == "up" else 0.0
    k = int(0.05 * SR)
    mode = np.convolve(mode, np.ones(k) / k, mode="same").astype(np.float32)
    music = up * mode + tense * (1 - mode)

    vo = np.zeros(n, dtype=np.float32)
    duck = np.ones(n, dtype=np.float32)
    for b, c in zip(tl, vo_clips):
        if c is None:
            continue
        c = c / (np.max(np.abs(c)) + 1e-9) * 0.9
        i = int(b["vo_start"] * SR)
        j = min(n, i + len(c))
        vo[i:j] += c[: j - i]
        duck[i:j] = 0.45
    duck = np.convolve(duck, np.ones(int(0.08 * SR)) / int(0.08 * SR), mode="same").astype(np.float32)

    fx = np.zeros(n + 3 * SR, dtype=np.float32)

    def place(name, t, gain=1.0):
        s = get_sfx(name)
        i = int(t * SR)
        if 0 <= i < n:
            fx[i:i + len(s)] += gain * s[: len(fx) - i]

    for b in tl:
        for off, name in b["sfx"]:
            place(name, b["start"] + off)
        if b.get("tel"):
            place("beep", b["start"] + TEL_AT, 0.6)
        if b.get("vac"):
            place("riser", b["start"] - VACUUM - 1.5, 0.9)
            place(b.get("impact", "boom"), b["start"], 1.0)
        # 2.5 s sensory reset - soft whoosh on every reset boundary
        k = 1
        while b["start"] + k * RESET < b["end"] - 0.3:
            place("whoosh", b["start"] + k * RESET - 0.15, 0.35)
            k += 1
    fx = fx[:n]

    mixed = 0.55 * music * duck + fx + 1.0 * vo
    # comedy vacuum: true digital silence (0 samples) with a 4 ms anti-click fade
    f = int(0.004 * SR)
    for b in tl:
        if b.get("vac_window"):
            a, z = int(b["vac_window"][0] * SR), int(b["vac_window"][1] * SR)
            if a - f > 0:
                mixed[a - f:a] *= np.linspace(1, 0, f)
            mixed[a:z] = 0.0
    mixed = np.tanh(1.1 * mixed)
    peak = np.max(np.abs(mixed)) + 1e-9
    mixed = mixed / peak * 0.89
    for b in tl:  # re-assert exact zeros after normalisation
        if b.get("vac_window"):
            a, z = int(b["vac_window"][0] * SR), int(b["vac_window"][1] * SR)
            mixed[a:z] = 0.0
    return mixed.astype(np.float32)


def write_wav(path: Path, x: np.ndarray):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    st = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())

# ----------------------------------------------------------------- visuals --
FONT_BOLD = ["assets/font_bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
FONT_MEME = ["assets/font_meme.ttf", "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
             "/System/Library/Fonts/Supplemental/Impact.ttf", "/Library/Fonts/Impact.ttf",
             "C:/Windows/Fonts/impact.ttf"] + FONT_BOLD
FONT_MONO = ["assets/font_mono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consolab.ttf"] + FONT_BOLD


@lru_cache(maxsize=64)
def font(kind: str, size: int):
    for p in {"bold": FONT_BOLD, "meme": FONT_MEME, "mono": FONT_MONO}[kind]:
        pp = Path(p) if Path(p).is_absolute() else ROOT / p
        if pp.exists():
            try:
                return ImageFont.truetype(str(pp), size)
            except Exception:
                pass
    return ImageFont.load_default(size=size)


def strip_emoji(s: str) -> str:
    """Most system fonts can't draw colour emoji in Pillow - keep it clean."""
    return "".join(ch for ch in s if ord(ch) < 0x2190 or 0x2190 <= ord(ch) <= 0x21FF or ch in "−–—°₂").strip()


def starfield(seed=1) -> Image.Image:
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    base[..., 0] = 6 + 10 * y
    base[..., 1] = 7 + 6 * y
    base[..., 2] = 18 + 22 * y
    img = Image.fromarray(base.astype(np.uint8))
    neb = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(neb)
    for _ in range(6):
        cx, cy, r = rng.integers(0, W), rng.integers(0, H), rng.integers(200, 520)
        col = tuple(int(c) for c in rng.choice([(60, 20, 80), (20, 40, 90), (90, 40, 20)]))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    neb = neb.filter(ImageFilter.GaussianBlur(160))
    img = ImageChops.add(img, neb)
    d = ImageDraw.Draw(img)
    for _ in range(1400):
        x, yy = rng.integers(0, W), rng.integers(0, H)
        b = int(rng.uniform(60, 255) ** 1.0)
        d.point((x, yy), fill=(b, b, min(255, b + 20)))
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    for _ in range(60):
        x, yy, r = rng.integers(0, W), rng.integers(0, H), rng.integers(2, 4)
        gd.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 255, 255))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(2)))
    return ImageChops.add(img, glow)


PAL = {
    "venus": ((236, 200, 130), (196, 132, 62), (255, 150, 60)),
    "venus_hot": ((255, 170, 80), (190, 50, 20), (255, 70, 20)),
    "venus_blue": ((120, 190, 230), (40, 90, 160), (80, 160, 255)),
    "earth": ((70, 140, 230), (40, 150, 80), (90, 160, 255)),
    "mercury": ((170, 165, 160), (95, 90, 88), (160, 160, 170)),
    "sun": ((255, 245, 200), (255, 190, 60), (255, 180, 40)),
}


def draw_planet(img: Image.Image, cx, cy, r, pal="venus", seed=0, bands=14.0, glow=0.55):
    c1, c2, gcol = [np.array(c, np.float32) for c in PAL[pal]]
    if glow:
        g = Image.new("RGB", img.size)
        ImageDraw.Draw(g).ellipse([cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12],
                                  fill=tuple(int(v * glow) for v in gcol))
        img = ImageChops.add(img, g.filter(ImageFilter.GaussianBlur(r * 0.22)))
    x0, y0 = int(cx - r - 2), int(cy - r - 2)
    size = int(2 * r + 4)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    nx, ny = (xx + x0 - cx) / r, (yy + y0 - cy) / r
    rr = nx * nx + ny * ny
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.55, -0.45, 0.70])
    L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0.04, 1)
    rng = np.random.default_rng(seed)
    nse = np.asarray(Image.fromarray((rng.random((9, 9)) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC),
                     np.float32) / 255
    band = 0.5 + 0.5 * np.sin(ny * bands + 2.6 * np.sin(nx * 3 + seed) + 4 * nse)
    col = c1 * band[..., None] + c2 * (1 - band[..., None])
    shade = (0.18 + 0.95 * lam) * (nz ** 0.3)
    col = np.clip(col * shade[..., None], 0, 255)
    alpha = np.clip((1 - np.sqrt(rr)) * r, 0, 1)
    tile = Image.fromarray(col.astype(np.uint8))
    img.paste(tile, (x0, y0), Image.fromarray((alpha * 255).astype(np.uint8)))
    return img


def label(img, xy, text, size=44, fill=(255, 255, 255), anchor="mm", kind="bold"):
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=font(kind, size), fill=fill, anchor=anchor, stroke_width=max(2, size // 14), stroke_fill=(0, 0, 0))


def surface(hot=False, seed=3) -> Image.Image:
    rng = np.random.default_rng(seed)
    hz = int(H * 0.44)
    arr = np.zeros((H, W, 3), np.float32)
    y = np.arange(H)[:, None].astype(np.float32)
    top, bot = (np.array([255, 190, 110]), np.array([200, 110, 40])) if not hot else (np.array([255, 120, 60]), np.array([170, 30, 10]))
    sky = top + (bot - top) * np.clip(y / hz, 0, 1)
    g0, g1 = (np.array([110, 70, 35]), np.array([45, 25, 12])) if not hot else (np.array([120, 40, 15]), np.array([40, 8, 4]))
    ground = g0 + (g1 - g0) * np.clip((y - hz) / (H - hz), 0, 1)
    arr[:hz] = sky[:hz][:, None, :]
    arr[hz:] = ground[hz:][:, None, :]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(140):  # flat basalt slabs (Venera-13 look)
        yc = rng.uniform(hz + 10, H)
        p = (yc - hz) / (H - hz)
        w = 40 + 420 * p * rng.uniform(0.5, 1.4)
        h = 6 + 70 * p * rng.uniform(0.4, 1.0)
        xc = rng.uniform(-100, W + 100)
        sh = rng.integers(-40, 40)
        poly = [(xc - w / 2, yc), (xc - w / 2 + sh, yc - h), (xc + w / 2 + sh, yc - h * 0.8), (xc + w / 2, yc)]
        tone = rng.integers(0, 2)
        d.polygon(poly, fill=(30, 15, 8, 120) if tone else (200, 130, 70, 70) if not hot else (255, 80, 30, 70))
    haze = Image.new("RGB", (W, H))
    ImageDraw.Draw(haze).rectangle([0, hz - 70, W, hz + 50], fill=(120, 60, 20) if not hot else (140, 30, 5))
    img = ImageChops.add(img, haze.filter(ImageFilter.GaussianBlur(50)))
    return img


def clouds(seed=5) -> Image.Image:
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None, None]
    arr = np.array([230, 190, 120], np.float32) * (1 - y) + np.array([170, 120, 60], np.float32) * y
    img = Image.fromarray(np.broadcast_to(arr, (H, W, 3)).astype(np.uint8))
    for layer in range(3):
        lay = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(lay)
        for _ in range(70):
            cx, cy = rng.uniform(-200, W + 200), rng.uniform(0, H)
            rx, ry = rng.uniform(150, 520), rng.uniform(30, 110)
            c = rng.choice([(255, 235, 180), (200, 150, 80), (240, 210, 140), (170, 110, 50)])
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*[int(v) for v in c], int(rng.uniform(40, 110))))
        img = Image.alpha_composite(img.convert("RGBA"), lay.filter(ImageFilter.GaussianBlur(22 - layer * 6))).convert("RGB")
    return img


def draw_lander(img):
    d = ImageDraw.Draw(img)
    cx, cy = 1180, 650
    d.ellipse([cx - 260, cy + 60, cx + 260, cy + 150], fill=(70, 70, 75), outline=(20, 20, 20), width=6)  # landing ring
    d.rectangle([cx - 120, cy - 120, cx + 120, cy + 100], fill=(170, 170, 175), outline=(30, 30, 30), width=6)
    d.ellipse([cx - 150, cy - 240, cx + 150, cy - 60], fill=(200, 200, 205), outline=(30, 30, 30), width=6)
    d.rectangle([cx - 25, cy - 360, cx + 25, cy - 230], fill=(140, 140, 145), outline=(30, 30, 30), width=4)
    d.ellipse([cx - 70, cy - 400, cx + 70, cy - 340], fill=(150, 150, 155), outline=(30, 30, 30), width=4)
    for k in (-1, 1):
        d.rectangle([cx + k * 200 - 30, cy - 40, cx + k * 200 + 30, cy + 70], fill=(120, 120, 125), outline=(30, 30, 30), width=4)
    label(img, (cx, cy + 10), "ВЕНЕРА-13", 40, fill=(20, 20, 20), kind="bold")
    return img


def scene_image(key: str) -> Image.Image:
    if key in ("globe", "globe_hot"):
        img = starfield(11)
        img = draw_planet(img, 1210, 560, 400, "venus_hot" if key == "globe_hot" else "venus", seed=2)
        if key == "globe_hot":
            img = Image.blend(img, Image.new("RGB", (W, H), (120, 10, 0)), 0.18)
        return img
    if key in ("earthvenus", "earthvenus_blue"):
        img = starfield(4)
        img = draw_planet(img, 610, 540, 300, "earth", seed=9, bands=6)
        img = draw_planet(img, 1320, 540, 286, "venus_blue" if key.endswith("blue") else "venus", seed=2)
        label(img, (610, 190), "EARTH", 54)
        label(img, (1320, 200), "VENUS", 54, fill=(255, 210, 130))
        return img
    if key == "compare":
        img = starfield(6)
        sun = Image.new("RGB", (W, H))
        ImageDraw.Draw(sun).ellipse([-500, 140, 300, 940], fill=(255, 200, 80))
        img = ImageChops.add(img, sun.filter(ImageFilter.GaussianBlur(60)))
        img = draw_planet(img, 700, 520, 95, "mercury", seed=4, bands=3, glow=0.2)
        img = draw_planet(img, 1380, 520, 230, "venus", seed=2)
        label(img, (700, 380), "MERCURY · 58M km", 42)
        label(img, (1380, 250), "VENUS · 108M km", 42, fill=(255, 210, 130))
        return img
    if key in ("surface", "surface_hot"):
        return surface(hot=key == "surface_hot")
    if key == "clouds":
        return clouds()
    if key == "lander":
        return draw_lander(surface())
    if key == "mountains":
        img = surface(seed=8)
        d = ImageDraw.Draw(img)
        for x, w, h in [(250, 700, 420), (900, 900, 560), (1550, 700, 380)]:
            d.polygon([(x - w / 2, 480), (x, 480 - h), (x + w / 2, 480)], fill=(70, 40, 25))
            d.polygon([(x - w * 0.12, 480 - h * 0.76), (x, 480 - h), (x + w * 0.12, 480 - h * 0.76),
                       (x + w * 0.04, 480 - h * 0.7), (x - w * 0.05, 480 - h * 0.72)], fill=(225, 230, 240))
        return img
    if key == "orbit":
        img = starfield(8)
        sun = Image.new("RGB", (W, H))
        ImageDraw.Draw(sun).ellipse([440, 420, 680, 660], fill=(255, 210, 90))
        img = ImageChops.add(img, sun.filter(ImageFilter.GaussianBlur(40)))
        img = draw_planet(img, 560, 540, 80, "sun", seed=1, bands=2, glow=0.6)
        d = ImageDraw.Draw(img)
        d.ellipse([560 - 720, 540 - 300, 560 + 720, 540 + 300], outline=(255, 220, 150), width=4)
        img = draw_planet(img, 1240, 330, 95, "venus", seed=3, glow=0.3)
        d = ImageDraw.Draw(img)
        d.arc([1240 - 150, 330 - 150, 1240 + 150, 330 + 150], 200, 520, fill=(120, 220, 255), width=6)
        label(img, (1240, 520), "SPIN ↺ 243 d (backwards)", 40, fill=(140, 230, 255))
        label(img, (560, 170), "ORBIT ↻ 225 d", 44, fill=(255, 220, 150))
        return img
    return starfield(0)


@lru_cache(maxsize=32)
def base_for(key: str, asset: str | None, bid: str):
    for stem in filter(None, [asset, bid]):
        p = find_file(ASSETS, stem, IMG_EXT)
        if p:
            log(f"{bid}: using asset {p.name}")
            im = Image.open(p).convert("RGB")
            s = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
            x, y = (im.width - W) // 2, (im.height - H) // 2
            im = im.crop((x, y, x + W, y + H))
            return ("img", Image.blend(im, Image.new("RGB", (W, H)), 0.12))
        p = find_file(ASSETS, stem, (".mp4", ".mov", ".webm"))
        if p:
            log(f"{bid}: using video asset {p.name}")
            return ("vid", str(p))
    return ("img", scene_image(key))


_VID = {}


def video_frame(path: str, t: float) -> Image.Image:
    try:
        if path not in _VID:
            try:
                from moviepy import VideoFileClip
            except ImportError:
                from moviepy.editor import VideoFileClip
            _VID[path] = VideoFileClip(path, audio=False)
        c = _VID[path]
        fr = Image.fromarray(c.get_frame(t % max(0.04, c.duration - 0.05)))
        s = max(W / fr.width, H / fr.height)
        fr = fr.resize((int(fr.width * s) + 1, int(fr.height * s) + 1))
        x, y = (fr.width - W) // 2, (fr.height - H) // 2
        return fr.crop((x, y, x + W, y + H))
    except Exception:
        return scene_image("globe")


@lru_cache(maxsize=64)
def meme_card(text: str, idx: int) -> Image.Image:
    text = strip_emoji(text) or "!!"
    f = font("meme", 78)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = tmp.textbbox((0, 0), text, font=f, stroke_width=3)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 40
    card = Image.new("RGBA", (tw + pad * 2, th + pad * 2 + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    colors = [(255, 230, 0), (255, 255, 255), (0, 240, 255), (255, 90, 160)]
    bg = colors[idx % len(colors)]
    d.rounded_rectangle([6, 6, card.width - 1, card.height - 1], 28, fill=(0, 0, 0, 200))
    d.rounded_rectangle([0, 0, card.width - 7, card.height - 7], 28, fill=(*bg, 255), outline=(0, 0, 0, 255), width=6)
    d.text(((card.width - 7) / 2, (card.height - 7) / 2), text, font=f, fill=(0, 0, 0), anchor="mm")
    ang = [-6, 5, -3, 7][idx % 4]
    return card.rotate(ang, resample=Image.BICUBIC, expand=True)


@lru_cache(maxsize=64)
def telemetry_badge(text: str) -> Image.Image:
    f1, f2 = font("mono", 52), font("mono", 22)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = tmp.textlength("▲ " + text, font=f1)
    w, h = int(tw) + 80, 140
    badge = Image.new("RGBA", (w + 40, h + 40))
    d = ImageDraw.Draw(badge)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], 14, outline=(0, 255, 210, 255), width=5)
    glow = badge.filter(ImageFilter.GaussianBlur(10))
    badge = Image.alpha_composite(glow, badge)
    d = ImageDraw.Draw(badge)
    d.rounded_rectangle([24, 24, 16 + w, 16 + h], 12, fill=(0, 20, 25, 215))
    d.text((50, 42), "● NASA/JPL TELEMETRY  ·  LIVE SCAN", font=f2, fill=(0, 255, 210))
    d.text((50, 76), "▲ " + text, font=f1, fill=(230, 255, 250))
    for yy in range(28, 16 + h, 6):  # scanlines
        d.line([(26, yy), (14 + w, yy)], fill=(0, 0, 0, 40))
    return badge


@lru_cache(maxsize=1024)
def caption(text: str, hi: int) -> Image.Image:
    words = text.split()
    f = font("bold", 62)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    space = tmp.textlength(" ", font=f)
    lines, cur, curw = [], [], 0
    for i, wd in enumerate(words):
        wl = tmp.textlength(wd, font=f)
        if cur and curw + space + wl > 1600:
            lines.append(cur)
            cur, curw = [], 0
        cur.append((i, wd, wl))
        curw += (space if len(cur) > 1 else 0) + wl
    if cur:
        lines.append(cur)
    lh = 80
    img = Image.new("RGBA", (W, lh * len(lines) + 20))
    d = ImageDraw.Draw(img)
    for li, line in enumerate(lines):
        tot = sum(x[2] for x in line) + space * (len(line) - 1)
        x = (W - tot) / 2
        for i, wd, wl in line:
            col = (255, 225, 0) if i == hi else (255, 255, 255) if i < hi else (225, 225, 225)
            d.text((x, 10 + li * lh), wd, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
            x += wl + space
    return img


@lru_cache(maxsize=1)
def watermark():
    img = Image.new("RGBA", (520, 60))
    ImageDraw.Draw(img).text((510, 30), CHANNEL, font=font("bold", 30), fill=(255, 255, 255, 150), anchor="rm")
    return img


def ease(p):
    return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, p)))


ANCHORS = [(0.5, 0.5), (0.25, 0.35), (0.75, 0.4), (0.4, 0.7), (0.65, 0.3)]


class Renderer:
    def __init__(self, tl, total, vo_lens):
        self.tl, self.total = tl, total
        self.starts = np.array([b["start"] for b in tl])
        self.vo_lens = vo_lens

    def beat_at(self, t):
        i = int(np.searchsorted(self.starts, t, side="right") - 1)
        return self.tl[max(0, min(i, len(self.tl) - 1))]

    def frame(self, t: float) -> np.ndarray:
        b = self.beat_at(t)
        local = t - b["start"]
        nxt = self.tl[b["i"] + 1] if b["i"] + 1 < len(self.tl) else None
        in_vac = bool(nxt and nxt.get("vac") and t >= nxt["start"] - VACUUM)
        tz = (nxt["start"] - VACUUM - b["start"]) if in_vac else local  # freeze during vacuum

        kind, src = base_for(b["scene"], b.get("asset"), b["id"])
        base = video_frame(src, local) if kind == "vid" else src

        seg = int(tz // RESET)
        p = (tz % RESET) / RESET
        z = 1 + ZOOM_MAX * ease(p)
        ax, ay = ANCHORS[(b["i"] + seg) % len(ANCHORS)]
        dx = dy = 0.0
        if b.get("vac") and local < 0.55:
            k = 1 - local / 0.55
            z *= 1 + 0.15 * k * k
            rng = np.random.default_rng(int(t * FPS))
            dx, dy = rng.uniform(-1, 1, 2) * 34 * k
        cw, ch = W / z, H / z
        x0 = min(max(ax * (W - cw) + dx, 0), W - cw)
        y0 = min(max(ay * (H - ch) + dy, 0), H - ch)
        frame = base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)) if z > 1.0005 or dx else base.copy()
        if b["id"] == "B28" and seg % 2 == 1:  # 'spins backwards' gag
            frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        if in_vac:
            frame = Image.blend(frame, Image.new("RGB", (W, H)), 0.30)
        frame = frame.convert("RGBA")

        # meme card pop (spring)
        lm = local - MEME_AT
        if lm >= 0 and not in_vac:
            card = meme_card(b["meme"], b["i"])
            s = 1.0
            if lm < 0.35:
                q = lm / 0.35
                s = max(0.05, min(1.3, q * 1.25 if q < 0.6 else 1.25 - (q - 0.6) * 0.625))
            c = card if abs(s - 1) < 0.01 else card.resize((max(1, int(card.width * s)), max(1, int(card.height * s))), Image.BILINEAR)
            pos = [(1880, 120), (100, 140), (1860, 360), (110, 380)][b["i"] % 4]
            x = pos[0] - c.width if pos[0] > W / 2 else pos[0]
            frame.alpha_composite(c, (int(max(0, x)), int(pos[1])))

        # telemetry (1.3 s)
        if b.get("tel") and TEL_AT <= local < TEL_AT + TEL_DUR and not in_vac:
            bd = telemetry_badge(b["tel"])
            lt = local - TEL_AT
            vis = (int(lt * 30) % 2 == 0) if lt < 0.15 else True
            if vis:
                pos = (W - bd.width - 60, 590) if b["i"] % 2 else (60, 590)  # opposite the meme card
                frame.alpha_composite(bd, pos)

        # karaoke caption
        if not in_vac and t >= b["vo_start"]:
            words = b["vo"].split()
            dur = self.vo_lens[b["i"]] or min(b["vo_max"], _words(b["vo"]) / WPS)
            lens = np.cumsum([len(w) + 1 for w in words])
            hi = int(np.searchsorted(lens / lens[-1] * dur, t - b["vo_start"]))
            cap = caption(b["vo"], min(hi, len(words)))
            frame.alpha_composite(cap, (0, H - cap.height - 40))

        frame.alpha_composite(watermark(), (W - 540, 20))
        if b.get("vac") and local < 0.09:  # impact flash
            col = (255, 60, 30, 150) if b.get("impact") == "drop" else (255, 255, 255, 170)
            frame.alpha_composite(Image.new("RGBA", (W, H), col))
        return np.asarray(frame.convert("RGB"))

# ------------------------------------------------------------------ encode --
def encode_ffmpeg(render, total, wav, out, preset):
    n = int(round(total * FPS))
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", preset, "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(render.frame(k / FPS).tobytes())
        if k % (FPS * 5) == 0:
            log(f"frame {k}/{n}  ({k / FPS:5.1f}s)")
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("ffmpeg encode failed")


def encode_moviepy(render, total, wav, out, preset):
    try:
        from moviepy import AudioFileClip, VideoClip  # moviepy >= 2
        v2 = True
    except ImportError:
        from moviepy.editor import AudioFileClip, VideoClip  # moviepy 1.x
        v2 = False
    clip = VideoClip(render.frame, duration=total)
    audio = AudioFileClip(str(wav))
    clip = clip.with_audio(audio) if v2 else clip.set_audio(audio)
    clip.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", preset=preset,
                         ffmpeg_params=["-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                         threads=os.cpu_count() or 4)


def main():
    global FFMPEG
    ap = argparse.ArgumentParser(description="Cosmic Storyline MP4 builder")
    ap.add_argument("--out", default="cosmic_storyline_out.mp4")
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--rate", default=TTS_RATE, help='edge-tts speed, e.g. "+12%%"')
    ap.add_argument("--no-tts", action="store_true", help="skip voiceover (captions only)")
    ap.add_argument("--engine", choices=["auto", "moviepy", "ffmpeg"], default="auto")
    ap.add_argument("--preset", default="veryfast", help="x264 preset (veryfast default)")
    ap.add_argument("--max-seconds", type=float, default=None, help="render only the first N seconds")
    ap.add_argument("--table", action="store_true", help="print the production table and exit")
    ap.add_argument("--export-json", metavar="PATH", help="write the timeline JSON and exit")
    ap.add_argument("--audio-only", action="store_true", help="only build the mixed WAV")
    a = ap.parse_args()

    tl, total = build_timeline()
    if a.table:
        print(markdown_table(tl))
        print(f"\nTOTAL: {tc(total)} ({total:.2f}s)")
        return
    if a.export_json:
        Path(a.export_json).write_text(json.dumps(dict(topic=TOPIC, total=total, vacuum=VACUUM, tel_dur=TEL_DUR,
                                                       tel_at=TEL_AT, meme_at=MEME_AT, reset=RESET, zoom=ZOOM_MAX,
                                                       titles=TITLES, beats=tl), ensure_ascii=False, indent=1))
        log(f"timeline -> {a.export_json}")
        return

    FFMPEG = ffmpeg_exe()
    CACHE.mkdir(exist_ok=True)
    log(f"{TOPIC}: {len(tl)} beats, {total:.2f}s")
    vo = make_voiceover(tl, a.voice, a.rate, enabled=not a.no_tts)
    vo_lens = [len(c) / SR if c is not None else None for c in vo]
    log("mixing audio ...")
    mix = mix_audio(tl, total, vo)
    render_total = min(total, a.max_seconds) if a.max_seconds else total
    wav = CACHE / "mix.wav"
    write_wav(wav, mix[: int(render_total * SR)])
    log(f"audio -> {wav}")
    if a.audio_only:
        return
    r = Renderer(tl, total, vo_lens)
    engine = a.engine
    if engine == "auto":
        try:
            import moviepy  # noqa: F401
            engine = "moviepy"
        except ImportError:
            engine = "ffmpeg"
            log("moviepy not installed - encoding through a direct ffmpeg pipe")
    log(f"rendering {render_total:.1f}s with {engine} ...")
    (encode_moviepy if engine == "moviepy" else encode_ffmpeg)(r, render_total, wav, Path(a.out), a.preset)
    log(f"done -> {a.out}")


if __name__ == "__main__":
    main()
