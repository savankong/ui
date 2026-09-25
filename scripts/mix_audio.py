"""Mixes the 7-bar song loop with the UI sounds → out/loop.wav.

Each sound is placed so its measured peak (loudest 5 ms) lands exactly on its
event time from window.SOUNDS in index.html (exported to out/sounds.json by the
renderer). Sounds and the song wrap around the loop point so it plays seamlessly.
"""
import json, subprocess
import numpy as np

SR = 48000
A = "assets/audio/"


def load(path, ch=2):
    raw = subprocess.run(["ffmpeg", "-loglevel", "quiet", "-i", path, "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()


def envelope(x, win=0.005):
    m = np.abs(x).max(1)
    n = int(win * SR)
    return np.sqrt(np.convolve(m ** 2, np.ones(n) / n, "same"))


def peak_of(x):
    return int(np.argmax(envelope(x)))


def hits(x, count):
    """First `count` transients (keystrokes) as separate clips."""
    e = envelope(x)
    rise = np.maximum(np.diff(e), 0)
    thr = rise.max() * 0.3
    idx, last = [], -SR
    for i in np.where(rise > thr)[0]:
        if i - last > 0.08 * SR:
            idx.append(i); last = i
        if len(idx) == count:
            break
    clips = []
    for i in idx:
        a = max(0, i - int(0.01 * SR))
        c = x[a:a + int(0.09 * SR)].copy()
        c[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))[:, None]
        clips.append(c)
    return clips


beats = json.load(open("analysis/beats.json"))
cue = json.load(open("out/sounds.json"))
dur = cue["duration"]
N = int(round(dur * SR))

song = load(A + "house-vibes.mp3")
s0 = int(round(beats["loop"]["start"] * SR))
out = song[s0:s0 + N].copy()
# Loop seam: crossfade the bar after the loop into the first 12 ms.
xf = int(0.012 * SR)
ramp = np.linspace(0, 1, xf)[:, None]
out[:xf] = out[:xf] * np.sqrt(ramp) + song[s0 + N:s0 + N + xf] * np.sqrt(1 - ramp)

sfx = {name: load(A + f"{name}.mp3") for name in ("click", "switch", "tick", "whoosh", "chime")}
k1, k2, k3 = hits(load(A + "keys.mp3"), 3)
sfx.update(key1=k1, key2=k2, key3=k3)
LEVEL = {"click": 0.30, "switch": 0.34, "tick": 0.22, "whoosh": 0.22, "chime": 0.20, "key1": 0.30, "key2": 0.30, "key3": 0.30}
for name, clip in sfx.items():
    clip *= LEVEL[name] / max(1e-6, np.abs(clip).max())
peaks = {name: peak_of(clip) for name, clip in sfx.items()}

placed = []
for s in cue["sounds"]:
    clip = sfx[s["sfx"]] * s.get("gain", 1.0)
    start = int(round(s["t"] * SR)) - peaks[s["sfx"]]
    idx = (start + np.arange(len(clip))) % N          # wrap around the loop
    np.add.at(out, idx, clip)
    placed.append({"t": s["t"], "sfx": s["sfx"], "peak_ms": round(peaks[s["sfx"]] / SR * 1000, 1)})

gain = min(1.0, 0.97 / np.abs(out).max())
out *= gain
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "out/loop.wav"],
               input=out.astype(np.float32).tobytes(), check=True)
json.dump(placed, open("out/sounds_placed.json", "w"), indent=1)
print(f"out/loop.wav  {dur}s  {len(placed)} sounds  master gain {gain:.2f}")
