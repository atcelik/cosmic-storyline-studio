# Audio standard

## Narration
- Engine: **Kokoro-82M** (Apache-2.0, runs on CPU), English. Default voice `af_heart`; audition 3–4 voices on a 30 s excerpt before choosing, then fix it in `config.json` (or per episode in `episode.json → voice`).
- Speed 0.95–1.0. Write for the ear: short sentences, no parentheses, numbers as you would say them.
- Pronunciation: put hard words in `episodes/epNN/lexicon.json` (`{"Enceladus": "en-sell-uh-dus"}`) and listen. Re-run `make tts`; only changed lines are regenerated.
- The voice is synthetic. The description says so (done by `meta.py`). Also check YouTube Studio's current "altered or synthetic content" question when uploading and answer it as the form requires.

## Mix
- Music bed at −20 dB, ducked automatically under the voice (sidechain), fades in 1.5 s / out 3 s. Final loudness normalised to about −14 LUFS, true peak −1.5 dBTP (single-pass `loudnorm`; check with ebur128).
- Music and SFX: only CC0 / public-domain / CC-BY you can credit. Put `credit` and `license` in `episode.json → music`; they land in the description. Check each track's own licence page.
- SFX: `"sfx": [{"file": "assets/sfx/whoosh.wav", "at": 0.0, "gain_db": -8}]` on a shot.

## Check
`ffmpeg -i build/final.mp4 -af ebur128=peak=true -f null -` → read Integrated loudness (≈ −14 LUFS) and True peak (≤ −1 dBTP).
Listen to the draft once with headphones and once on a phone speaker.
