#!/usr/bin/env python3
"""Mix voice-over + SFX + ducked music, normalise loudness, mux with video -> build/final.mp4
Usage: audio.py episodes/ep01/episode.json [--draft]"""
import argparse, subprocess, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import *


def load_audio(path, sr):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    A = cfg["audio"]
    sr = A["sample_rate"]
    base, build = ep_dirs(a.episode)
    ep = load_json(a.episode)
    tl = load_json(build / "timeline.json")
    total = tl["total"]
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for s, t in zip(ep["shots"], tl["shots"]):
        w = build / "audio" / f"{s['id']}.wav"
        if (s.get("voiceover") or "").strip() and w.exists():
            x = load_audio(w, sr)
            i = int(t["vo_start"] * sr)
            track[i:i + len(x)] += x[: len(track) - i]
        for fx in s.get("sfx", []):
            x = load_audio(base / fx["file"], sr) * 10 ** (fx.get("gain_db", -6) / 20)
            i = int((t["start"] + fx.get("at", 0)) * sr)
            track[i:i + len(x)] += x[: max(0, len(track) - i)]
    track = np.clip(track[: int(total * sr)], -1, 1)
    vo = build / "vo_sfx.wav"
    with wave.open(str(vo), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    video = build / ("video_draft.mp4" if a.draft else "video_silent.mp4")
    out = build / ("final_draft.mp4" if a.draft else "final.mp4")
    music = ep.get("music")
    loud = f"loudnorm=I={A['loudness_i']}:TP={A['true_peak']}:LRA=11,aformat=sample_fmts=fltp:channel_layouts=stereo"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(vo)]
    if music:
        g = music.get("gain_db", A["music_gain_db"])
        cmd += ["-stream_loop", "-1", "-i", str(base / music["file"])]
        fc = (f"[1:a]aresample={sr},asplit=2[vo][sc];"
              f"[2:a]aresample={sr},volume={g}dB,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0, total - 3):.2f}:d=3[m];"
              f"[m][sc]sidechaincompress=threshold={A['duck_threshold']}:ratio={A['duck_ratio']}:attack=15:release=450[md];"
              f"[vo][md]amix=inputs=2:duration=first:dropout_transition=0,volume=2,{loud}[a]")
    else:
        fc = f"[1:a]aresample={sr},{loud}[a]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
