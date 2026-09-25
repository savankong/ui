#!/usr/bin/env bash
# Downloads the song and UI sounds (Mixkit, free license: https://mixkit.co/license/).
# They are not committed; the rendered video includes them.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/audio
get() { [ -s "assets/audio/$2" ] || curl -sSfL "$1" -o "assets/audio/$2"; }
get https://assets.mixkit.co/music/129/129.mp3                        house-vibes.mp3   # House Vibes — Alejandro Magaña (A. M.)
get https://assets.mixkit.co/active_storage/sfx/2577/2577-preview.mp3 click.mp3         # Interface device click
get https://assets.mixkit.co/active_storage/sfx/2585/2585-preview.mp3 switch.mp3        # On or off light switch tap
get https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3 tick.mp3          # Cool interface click tone
get https://assets.mixkit.co/active_storage/sfx/1396/1396-preview.mp3 keys.mp3          # Soft typing on a digital keyboard
get https://assets.mixkit.co/active_storage/sfx/1489/1489-preview.mp3 whoosh.mp3        # Air woosh
get https://assets.mixkit.co/active_storage/sfx/2870/2870-preview.mp3 chime.mp3         # Correct answer tone
echo "assets ready"
