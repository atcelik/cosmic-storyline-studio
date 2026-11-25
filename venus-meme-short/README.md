# Venus meme short (Cosmic Storyline, ~2:42)

Separate format from the documentary pipeline on `main` (fast meme edit with shake/zoom resets), kept on this branch only.

- `build_video.py` — one-command MP4 builder (edge-tts voiceover, Pillow frames, synthesized SFX/music, 0.6 s silence cuts).
  `pip install moviepy pillow numpy edge-tts` then `python build_video.py`
- `storyboard_preview.html` — open in a browser to play the timing preview with Web Audio.
- `cosmic_storyline_out.mp4` — test render, 1920x1080 30 fps, **no voiceover** (edge-tts had no internet in the build sandbox).
