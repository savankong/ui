"""Beat grid for the song: tempo, phase, downbeats and the 7-bar window we use.

Onsets come from low-band (kick) spectral flux. Tempo and phase are fitted by
maximising the kick flux sampled on the grid; the loop starts on the downbeat
where the 8-bar drop lands (the biggest energy jump). Writes analysis/beats.json.
"""
import json, subprocess, sys
import numpy as np

SR, HOP, N = 22050, 128, 1024
BPM_RANGE = np.arange(119.0, 121.0, 0.005)
song = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/house-vibes.mp3"

x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "quiet", "-i", song, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                 capture_output=True, check=True).stdout, np.float32)
fps = SR / HOP
frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP] * np.hanning(N)
spec = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
freqs = np.fft.rfftfreq(N, 1 / SR)
kick = np.r_[0, np.maximum(np.diff(spec[:, freqs < 150], axis=0), 0).sum(1)]
rms = np.sqrt((frames ** 2).mean(1))
t = np.arange(len(kick)) / fps

best = (-1, 0, 0)
for bpm in BPM_RANGE:
    p = 60 / bpm
    for ph in np.arange(0, p, 0.002):
        v = np.interp(np.arange(ph, t[-1] - 0.1, p), t, kick).mean()
        if v > best[0]:
            best = (v, bpm, ph)
_, bpm, phase = best
period = 60 / bpm
beats = np.arange(phase, t[-1] - 0.1, period)

# Per-beat deviation of the actual kick peak from the grid (±30 ms search)
dev = []
for bt in beats:
    m = (t > bt - 0.03) & (t < bt + 0.03)
    dev.append(t[m][np.argmax(kick[m])] - bt)
dev = np.abs(np.array(dev)) * 1000

bar_energy = [float(rms[(t >= beats[i]) & (t < beats[i] + 4 * period)].mean()) for i in range(0, len(beats) - 4, 4)]
jumps = np.diff(bar_energy)
drop_bar = int(np.argmax(jumps) + 1)          # first bar after the biggest energy jump
start = float(beats[drop_bar * 4])

out = {
    "song": song, "bpm": round(float(bpm), 3), "first_beat": round(float(phase), 4),
    "grid_deviation_ms": {"median": round(float(np.median(dev)), 1), "p95": round(float(np.percentile(dev, 95)), 1)},
    "loop": {"start": round(start, 4), "bars": 7, "beats": 28, "duration": round(28 * period, 4), "drop_bar": drop_bar},
    "bar_energy": [round(e, 4) for e in bar_energy],
}
json.dump(out, open("analysis/beats.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("bpm", "first_beat", "grid_deviation_ms", "loop")}, indent=1))
