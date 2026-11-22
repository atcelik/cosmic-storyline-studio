# Pipeline

```
ChatGPT script ──► episode.json ──► validate ──► fetch/pick assets ──► tts ──► render ──► audio ──► meta
   (owner)         (contract)        G1           G2                   G3 draft   G4 final        G5 publish
```

| Stage | Script | In → Out |
|---|---|---|
| validate | `scripts/validate.py` | episode.json → pass/fail, pacing + sourcing warnings |
| fetch | `scripts/fetch_nasa.py` | `visual.search_query` → `assets/candidates/<shot>/` + page URLs |
| pick | `scripts/pick.py ep S003 2` | copies candidate 2 into `assets/`, fills file/source_url/credit (unverified) |
| tts | `scripts/tts.py` | voice-over per shot → `build/audio/*.wav`, real durations → `build/timeline.json` |
| render | `scripts/render.py` | timeline + assets → `build/video_silent.mp4` (or `video_draft.mp4` with `--draft`) |
| audio | `scripts/audio.py` | VO + SFX + ducked music, loudnorm → `build/final.mp4` |
| meta | `scripts/meta.py` | `build/captions.srt`, `build/description.txt` (chapters + credits) |

## How timing works
Shot length = max(`min_duration`, voice-over length + lead/tail, 2 s). The voice-over sets the pace, so picture and
sound cannot drift apart. A transition overlaps the end of one shot with the start of the next, so it does not add time.
Without real audio (validate stage) lengths are estimated at 2.6 words/second.

## Render details
Per frame: sub-pixel affine warp (bicubic) of a pre-scaled working image with a smootherstep ease, so motion is smooth
at any speed. Output is encoded by ffmpeg with the BT.709 colour matrix tagged. Draft mode renders at half size, low quality.

## Performance (measured / not measured)
- Measured in the build sandbox (1 x86 core): ~15 fps at 1080p including x264 `medium`; 540p draft ~55–70 fps.
  At 15 fps a 11-minute video (~19,800 frames) is about 22 minutes.
- **Not measured on your server.** Run `make smoke --full-res` equivalent: `python3 tests/smoke.py --full-res` and note the fps in DECISIONS.md.
- Run long renders at night (`nohup make render audio meta EP=ep01 &`). Free cloud VMs can be reclaimed if they sit idle; a nightly render also keeps them busy.

## Known limits
- Video clips at 24 fps show mild judder at 30 fps output; keep such clips short (≤ 6 s) or use 30/60 fps sources.
- Transitions need both shots ≥ ~0.4 s longer than the transition (the timeline caps them automatically).
- Text is rendered with DejaVu Sans Bold; change `font_path` in `config.json` for another font.
- No 3D/CGI generation is included. `OUR_CGI` means graphics you supply as images/clips (e.g. Blender renders, diagrams).

## Helper scripts
| Command | Purpose |
|---|---|
| `make merge EP=ep02` | join `part_00_header.json` + `part_NN.json` into `episode.json` (refuses to overwrite an existing one) |
| `make check EP=ep02` | validate structure and pacing, no asset checks |
| `make pick-auto EP=ep02` / `scripts/pick.py ep.json S014 2` | choose fetched candidates |
| `make sheets EP=ep02` | contact sheets in `build/sheets/` for visual review |
| `scripts/mark_verified.py ep.json --all --claims [--yes]` | list, then mark, verified credits/claims |
| `scripts/patch_shots.py ep.json patch.json` | replace/insert shots (writes `.bak`) |
| `scripts/where.py episodes/ep02 2:15` | which shot is on screen at a time |
| `scripts/voice_test.py` | same text in several Kokoro voices |
Tested in the sandbox: merge, patch, where, contact sheets, mark_verified. Not tested: voice_test, fetch.

## Getting assets in one go (get_assets.py)
`make assets EP=ep01` downloads every URL in `episodes/ep01/asset_manifest.json`; `make assets-search EP=ep01` also searches the
NASA Image and Video Library for shots that have only a `search_query` (2 candidates each). Output: originals in `assets/originals/`,
transfer copies (≤ 3840 px images, ≤ 1080p video) + `report.json` + contact sheets in `bundle/`, and `ep01_assets_partNN.zip`
(≤ 400 MB each). Re-running skips finished files and retries failed ones.
Import: `python3 scripts/apply_bundle.py episodes/ep01 ep01_assets_part01.zip [...] [--pick S014=2]`.
Tested in the build sandbox against a local fake server (download, resume fallback, 404, HTML-instead-of-file, TIFF→JPEG,
1440p→1080p, split zips, NASA-search JSON parsing, import + pick). NOT tested against the real NASA/JPL servers.
