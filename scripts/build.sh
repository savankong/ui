#!/usr/bin/env bash
# Full pipeline: assets → beat grid → per-beat preview → subframes → audio → 60 fps video with motion blur.
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/fetch_assets.sh
python3 scripts/analyze_beats.py
node scripts/render.mjs preview                 # one frame per beat, check before the long render
node scripts/render.mjs full                    # 840 frames × 4 subframes (240 Hz)
python3 scripts/mix_audio.py
scripts/encode.sh
