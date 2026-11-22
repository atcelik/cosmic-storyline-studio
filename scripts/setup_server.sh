#!/usr/bin/env bash
# Ubuntu 22.04/24.04 (x86_64 or arm64). NOT TESTED on your server: run it, read errors, fix.
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-pip espeak-ng fonts-dejavu-core git make
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install numpy opencv-python-headless pillow soundfile
# Kokoro TTS (English). Pulls PyTorch; on arm64 CPU this is large (several GB). Skip with SKIP_TTS=1.
if [ "${SKIP_TTS:-0}" != "1" ]; then pip install kokoro; fi
echo "Check:"; ffmpeg -version | head -1; python -c "import cv2,numpy,PIL;print('cv2',cv2.__version__)"
echo "Next: make smoke   (full pipeline test with synthetic assets and dummy voice)"
