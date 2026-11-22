# Server setup

Assumes Ubuntu 22.04/24.04 (x86_64 or arm64), shell access, sudo. Free Oracle Cloud Ampere A1 allowances were reduced in 2026 (check your console for what your tenancy has); this pipeline is designed for 2 CPU cores / 12 GB RAM.

1. `bash scripts/setup_server.sh` (installs ffmpeg, espeak-ng, DejaVu font, a Python venv with numpy/OpenCV/Pillow/soundfile and Kokoro).
   - If the Kokoro/PyTorch install fails or is too large, run `SKIP_TTS=1 bash scripts/setup_server.sh` and fix TTS separately; everything else still works with `--engine dummy`.
2. `. .venv/bin/activate && make smoke` → must print `SMOKE TEST: PASS`.
3. `python3 tests/smoke.py --full-res` → note the fps printed by the renderer; that number predicts your render time (frames ≈ runtime_s × 30).
4. Audition voices: create `episodes/voice_test/episode.json` or run Kokoro by hand on a 30 s excerpt; choose a voice; set it in `config.json`.
5. Disk: ~2–4 GB per episode with originals; delete `assets/candidates/` after picking.

Idle-instance reclamation: some free VMs are reclaimed after a week of very low CPU use. Nightly renders keep the machine busy; do not rely on it, keep a copy of the repo and assets elsewhere.
