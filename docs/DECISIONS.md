# Decision log

## 2026-11-22 — project setup (owner decisions)
- Videos are **English**, 10–12 minutes, about space mysteries. Scripts drafted with ChatGPT; owner approves.
- Work happens in this project folder; `AGENTS.md` + `docs/*.md` define how work runs.
- Everything automated and free. Own server, open-source tools, GitHub skills/agents allowed.
- Priorities: viewer retention (pacing, transitions) and high visual quality.

## Carried over from the v1 package (2026-11-21)
- 1920×1080, 30 fps, H.264/AAC. Real NASA/ESA/ESO/Webb material first; labelled scientific visualizations where nothing can be photographed; no generative-AI imagery.
- Webb processed data and CGI are labelled and kept apart from real camera footage.
- Rejected: the 24 fps Enceladus video (judder). Do not reuse it.
- No jitter, no x/y sine drift, no shake.

## Proposed change (needs owner confirmation after viewing a draft)
- v1 capped camera zoom at ~2–6 %. Retention goal suggests smooth eased moves up to ~10 % and a different move on nearly every shot. Smoothness rule (no jitter) is unchanged. Keep ≤ 6 % if the draft feels too busy.

## Status of verification (2026-11-22, build sandbox: x86_64, 1 core)
- TESTED: validator, timeline math, renderer (stills, video clip, all 7 transitions, labels, text, end fade), audio mix with ducking + loudnorm, SRT/description, end-to-end smoke test with synthetic assets and a dummy voice → PASS. Full-res speed ≈ 15 fps, draft ≈ 55–70 fps. Frame-to-frame motion showed no spikes (max/median ≈ 1.3).
- NOT TESTED: Kokoro voice (no install/network in sandbox), `fetch_nasa.py` against the live NASA API, `setup_server.sh`, arm64 server speed, real NASA assets, a real 11-minute episode, YouTube upload.
- Update this section after you run them on the server.

## 2026-11-22 — after reviewing the Cosmic Storyline EP01 draft (owner feedback)
- Owner rejected the EP01 draft look: small photos inside panels, HUD/labels everywhere, weak camera.
- New rules: full-frame picture only; labels only for SCIENTIFIC_CGI / ARTIST_CONCEPT / OUR_CGI, no credit text on screen (credits go to the description); OUR_CGI diagrams <= 15 % of shots (validator warns); every moving shot needs camera.focus (zoom to the point of interest, optional focus_from); validator warns when a source would be upscaled.
- Added scripts/globe.py: rotating Earth/Moon (any planet texture) rendered from NASA maps, with targeted zoom to a lon/lat. Label such shots honestly as a visualization.
- Added a subtle vignette (config look.vignette) and per-shot text_start / label_text.
- 30 s trial (episodes/trial30): 1920x1080, 30 fps, h264+aac, 32.2 s, -13.9 LUFS. Picture-only test: no narration (Kokoro not available in the build sandbox), procedural ambient music. Owner review pending.
