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

## 2026-11-22 (afternoon) — documentary pacing and the mixed 3D format
- Owner on the first 30 s GitHub render: "tempo too fast; feels like sliding slides, not a documentary". Then sent a reference (NatGeo "Journey to the Edge of the Universe": continuous 3D camera flight).
- Diagnosis: every shot eased from rest to rest (= slideshow), crossfades everywhere, no pauses in narration, only stills.
- Decisions: linear camera motion (still moving at cuts), subtle float, hard cuts; vo_lead 0.45 s, vo_tail 1.0 s, min_shot 3.5 s, voice speed 1.0; shot warn 10 s / error 14 s; per-shot `vo_lead` for cold opens; film grain off (19 s test grew to 97 MB and YouTube removes it).
- Owner chose the **mixed format**: our 3D fly-through scenes + real NASA imagery, about half and half. New `scripts/space3d.py` (perspective camera on a spline, textured spheres, rings with shadows both ways, 3D star field with true parallax, backlit plume particles, sun glare, limb glow). CGI share warning moved from 15 % to 60 %.
- Textures: Enceladus = Cassini map PIA18435 (NASA/JPL); Saturn + rings = Solar System Scope (CC BY 4.0, credit in the description).
- Parallax tested: clean on a single body on black (ocean cutaway); tears plume/limb photos and Saturn's rings, so it is limited to `layer: body`.

## 2026-11-22 (evening) — parallel rendering and the Earth connection
- Owner asked for several Actions running at once. produce.yml is now prepare -> cgi matrix (3D chunks, ~90 frames) -> render matrix (30 s chunks) -> finish (ffmpeg concat without re-encode, audio, meta, release). First run: 15 3D jobs + 2 picture jobs, 7.5 min end to end (single machine: ~16 min). Local simulation joined 13 chunks to exactly the timeline's 438 frames.
- Owner liked v2 and asked to also cover what affects life on Earth. Rule added to RETENTION_STANDARD: every episode gets an Earth-connection beat. v3 adds an Earth fly-in (NASA Blue Marble) and two NOAA deep-sea vent photos (1977 Galapagos Rift discovery, Lost City hydrogen chemistry) before the closing question.
- Saturn ring radii calibrated from the texture's Cassini division: 1.22-2.41 Saturn radii.
- Owner rule (on-screen text): no corner labels ever ("REAL PHOTO", "VISUALIZATION" ...). Instead a top-left chapter card (brand, chapter title, subtitle, one small source line such as "Illustration · NASA/JPL Cassini map" / "Photo · NOAA") fades in at each chapter start, holds ~4.5 s and fades out completely. config corner_labels=false; shot "card" or beat "chapter"/"chapter_sub"; visual.credit_short for the source line.
- Earth texture: the NASA Blue Marble server was unreachable from the runner; v3 uses the Solar System Scope Earth map and its credit says so.

## 2026-11-22 (night): EP01 production
- Script approved by the owner ("Tamam"); two lines corrected after fact-check (line 11 now matches JPL PIA01394; line 55 no longer says "almost out of fuel").
- EP01 is generated by `episodes/ep01/build_episode.py` (shots, credits, claims) and `episodes/ep01/make_scenes.py` (3D flights). Edit those, not the JSON.
- New: a 3D spec with `"fit": true` is stretched in `ci/run.py prepare` to the exact voice-over length of the shots that use it; a video shot with `"continue": true` picks up the same flight where the previous shot cut (render.py). Reason: the camera never freezes at the end of a flight.
- Lines 7, 38 and 62 were split into two shots each (same flight continues) to stay near the 10 s shot rule.

## 2026-11-22 (late): Shorts
- Owner asked for Shorts cut from EP01 without losing picture quality. Not a crop of the 16:9 master (that would upscale ~1.8x): the Short is rendered natively at 1080x1920 (`episode.format`), 3D flights re-rendered vertically (`spec.size`, vertical field of view kept), photos cropped from the high-resolution originals or framed whole on black.
- Shorts get burned-in captions (`burn_captions`, 3 words at a time, timed to the real voice-over) and only reuse lines of the approved script. Built by `episodes/ep01/build_short.py`.
