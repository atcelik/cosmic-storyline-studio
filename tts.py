#!/usr/bin/env python3
"""Generate voice-over per shot, measure real durations, write build/timeline.json.
Usage: tts.py episodes/ep01/episode.json [--engine kokoro|dummy]
'dummy' makes tone bursts so the rest of the pipeline can be tested without a TTS install.
Optional lexicon: episodes/epXX/lexicon.json  {"Enceladus": "en-sell-uh-dus"}  (plain-text replacements, check by ear)."""
import argparse, hashlib, json, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import *

SR = 24000


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def dummy(text, sr=SR):
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    out = []
    for _ in text.split():
        n = int(sr * 0.17)
        f = rng.uniform(150, 260)
        tt = np.arange(n) / sr
        out.append(0.15 * np.sin(2 * np.pi * f * tt) * np.hanning(n))
        out.append(np.zeros(int(sr * 0.2 * (0.8 + 0.4 * rng.random()))))
    return np.concatenate(out) if out else np.zeros(1)


class Kokoro:
    def __init__(self, cfg):
        from kokoro import KPipeline  # pip install kokoro soundfile ; apt install espeak-ng
        self.p = KPipeline(lang_code=cfg["tts"]["lang_code"])
        self.voice, self.speed = cfg["tts"]["voice"], cfg["tts"]["speed"]

    def __call__(self, text):
        chunks = []
        for _, _, audio in self.p(text, voice=self.voice, speed=self.speed):
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            chunks.append(a.astype(np.float32))
        return np.concatenate(chunks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--engine", default=None)
    a = ap.parse_args()
    cfg = load_config()
    base, build = ep_dirs(a.episode)
    ep = load_json(a.episode)
    engine = a.engine or ep.get("voice", {}).get("engine") or cfg["tts"]["engine"]
    if ep.get("voice"):
        cfg["tts"].update({k: v for k, v in ep["voice"].items() if k != "engine"})
    lex = load_json(base / "lexicon.json") if (base / "lexicon.json").exists() else {}
    (build / "audio").mkdir(exist_ok=True)
    cache_f = build / "audio" / "_cache.json"
    cache = load_json(cache_f) if cache_f.exists() else {}
    synth = None
    durs = {}
    for s in ep["shots"]:
        text = (s.get("voiceover") or "").strip()
        if not text:
            continue
        spoken = text
        for k, v in lex.items():
            spoken = spoken.replace(k, v)
        key = hashlib.sha1(f"{engine}|{cfg['tts']}|{spoken}".encode()).hexdigest()
        wav = build / "audio" / f"{s['id']}.wav"
        if cache.get(s["id"], {}).get("key") != key or not wav.exists():
            if engine == "dummy":
                x = dummy(spoken)
            else:
                synth = synth or Kokoro(cfg)
                x = synth(spoken)
            write_wav(wav, x)
            cache[s["id"]] = {"key": key, "dur": len(x) / SR}
            print(f"  {s['id']}: {len(x) / SR:.2f}s")
        durs[s["id"]] = cache[s["id"]]["dur"]
    save_json(cache_f, cache)
    tl = build_timeline(ep, cfg, durs)
    save_json(build / "timeline.json", tl)
    print(f"Timeline: {tl['total'] / 60:.2f} min, {len(tl['shots'])} shots -> build/timeline.json")


if __name__ == "__main__":
    main()
