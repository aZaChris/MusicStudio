"""Original soundtrack for the brand video, synthesised with the standard library only.

120 BPM, so one beat is 0.5 s and one bar 2 s: index.html cuts its scenes on bar lines and pops
the package "beats" on the music's beats. Change LENGTH or the bar layout here and there together.

    python3 music.py && ffmpeg -y -i assets/music.wav -af loudnorm=I=-16:TP=-1.5 -ar 44100 -c:a aac -b:a 128k assets/music.m4a
"""

import array
import math
import random
import wave

RATE = 44100
BEAT = 0.5
BAR = 4 * BEAT
LENGTH = 28.0  # seconds, the root composition's data-duration
random.seed(7)  # the hats are noise: seeded, so every run writes the same file

# Cmaj7 - Am7 - Fmaj7 - G6, warm and unresolved until the last bar.
CHORDS = [(60, 64, 67, 71), (57, 60, 64, 67), (53, 57, 60, 64), (55, 59, 62, 64)]
BASS = [36, 33, 41, 43]
ARP = [0, 1, 2, 3, 2, 1, 2, 3]

out = array.array("f", [0.0] * int(LENGTH * RATE + RATE))


def hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def add(start: float, samples) -> None:
    i = int(start * RATE)
    for k, s in enumerate(samples):
        out[i + k] += s


def pluck(note: int, length: float, gain: float):
    """Karplus-Strong: a noise burst in a delay line, averaged each pass, sounds like a string."""
    period = int(RATE / hz(note))
    line = [random.uniform(-1, 1) for _ in range(period)]
    for k in range(int(length * RATE)):
        a = line[k % period]
        line[k % period] = 0.996 * 0.5 * (a + line[(k + 1) % period])
        yield gain * a


def tone(note: int, length: float, gain: float, attack: float = 0.005):
    f = hz(note)
    for k in range(int(length * RATE)):
        t = k / RATE
        env = min(1.0, t / attack) * math.exp(-3 * t / length)
        yield gain * env * math.sin(2 * math.pi * f * t)


def kick(gain: float):
    phase = 0.0
    for k in range(int(0.3 * RATE)):
        t = k / RATE
        phase += 2 * math.pi * (45 + 90 * math.exp(-t * 30)) / RATE
        yield gain * math.exp(-t * 12) * math.sin(phase)


def hat(gain: float):
    last = 0.0
    for k in range(int(0.05 * RATE)):
        n = random.uniform(-1, 1)
        yield gain * math.exp(-k / RATE * 90) * (n - last)  # difference = cheap high-pass
        last = n


for bar in range(int(LENGTH / BAR)):
    t0 = bar * BAR
    chord, bass = CHORDS[bar % 4], BASS[bar % 4]
    if bar >= 12:  # outro: one last Cmaj7 strum rings out
        if bar == 12:
            for i, n in enumerate(CHORDS[0] + (72,)):
                add(t0 + i * 0.03, pluck(n, 3.5, 0.22))
            add(t0, tone(36, 3.5, 0.35))
        continue
    for i, n in enumerate(chord):  # soft pad under everything
        add(t0, tone(n - 12, BAR, 0.05, attack=0.4))
    if bar < 2:  # intro: quarter-note plucks, no drums
        for b in range(4):
            add(t0 + b * BEAT, pluck(chord[b], 1.0, 0.2))
        continue
    for s, idx in enumerate(ARP):
        add(t0 + s * BEAT / 2, pluck(chord[idx] + (12 if s == 7 else 0), 0.9, 0.17))
    for b in range(4):
        add(t0 + b * BEAT, kick(0.5 if b % 2 == 0 else 0.25))
        add(t0 + b * BEAT + BEAT / 2, hat(0.18))
        add(t0 + b * BEAT, tone(bass if b % 2 == 0 else bass + 12, BEAT, 0.3))
        if bar >= 7:  # web section lifts: hats on every 16th
            add(t0 + b * BEAT + BEAT / 4, hat(0.08))
            add(t0 + b * BEAT + 3 * BEAT / 4, hat(0.08))

# Fade in/out, normalise to -1 dBFS, write 16-bit mono.
n = int(LENGTH * RATE)
peak = max(abs(s) for s in out[:n]) or 1.0
scale = 10 ** (-1 / 20) / peak
pcm = array.array("h")
for k in range(n):
    t = k / RATE
    fade = min(1.0, t / 0.3, (LENGTH - t) / 1.5)
    pcm.append(int(max(-1.0, min(1.0, out[k] * scale * fade)) * 32767))
with wave.open("assets/music.wav", "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(pcm.tobytes())
print(f"assets/music.wav: {LENGTH} s, peak scaled by {scale:.2f}")
