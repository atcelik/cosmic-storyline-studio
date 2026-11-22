#!/usr/bin/env python3
"""Same text in several Kokoro English voices -> voice_test/<voice>.wav. NOT TESTED in the build sandbox.
Usage: python3 scripts/voice_test.py "30-second excerpt" """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from tts import write_wav

text = sys.argv[1] if len(sys.argv) > 1 else ("Four hundred years ago, a telescope showed us something that did not fit. "
                                              "Tonight, we follow the evidence, one clue at a time.")
voices = ["am_michael", "am_fenrir", "am_puck", "bm_george", "bm_fable", "af_heart"]
out = Path("voice_test"); out.mkdir(exist_ok=True)
from kokoro import KPipeline
pipes = {}
for v in voices:
    try:
        p = pipes.setdefault(v[0], KPipeline(lang_code=v[0]))
        ch = [a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a) for _, _, a in p(text, voice=v, speed=1.05)]
        write_wav(out / f"{v}.wav", np.concatenate(ch)); print("ok", v)
    except Exception as e:
        print("skipped", v, "->", e)
print("Listen to voice_test/*.wav, then set tts.voice in config.json")
