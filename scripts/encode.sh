#!/usr/bin/env bash
# 4 subframes per frame averaged with tmix → 60 fps motion blur, then mux the audio loop.
set -euo pipefail
cd "$(dirname "$0")/.."
ffmpeg -loglevel error -y -framerate 240 -i out/frames/s%05d.png \
  -i out/loop.wav \
  -filter_complex "[0:v]tmix=frames=4:weights='1 1 1 1',select='eq(mod(n\,4)\,3)',setpts=N/(60*TB),format=yuv420p[v]" \
  -map "[v]" -map 1:a -r 60 -c:v libx264 -preset slow -crf 16 -tune animation -movflags +faststart \
  -c:a aac -b:a 256k -shortest out/one-shape.mp4
ffmpeg -loglevel error -y -i out/loop.wav -c:a aac -b:a 192k out/loop.m4a
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration -of compact out/one-shape.mp4
