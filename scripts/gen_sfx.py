"""Generate all game sounds procedurally (self-made, no external assets): python3 scripts/gen_sfx.py
Writes assets/sfx/*.wav (16-bit mono 22050 Hz). Deterministic."""
import math
import os
import random
import struct
import wave

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sfx")


def note(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def tone(freq, dur, vol=0.5, attack=0.01, decay=None, kind="sine", slide=0.0):
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = freq + slide * t
        ph += 2 * math.pi * f / SR
        s = math.sin(ph) if kind == "sine" else (1.0 if math.sin(ph) > 0 else -1.0) * 0.4
        env = min(1.0, t / attack) * (math.exp(-t / decay) if decay else max(0.0, 1 - t / dur))
        out.append(s * env * vol)
    return out


def noise(dur, vol=0.3, decay=0.1, seed=1):
    r = random.Random(seed)
    return [(r.random() * 2 - 1) * vol * math.exp(-(i / SR) / decay) for i in range(int(SR * dur))]


def mix(*tracks, offsets=None):
    offsets = offsets or [0.0] * len(tracks)
    n = max(int(o * SR) + len(t) for t, o in zip(tracks, offsets))
    buf = [0.0] * n
    for t, o in zip(tracks, offsets):
        s = int(o * SR)
        for i, v in enumerate(t):
            buf[s + i] += v
    return buf


def save(name, buf):
    os.makedirs(OUT, exist_ok=True)
    peak = max(1e-9, max(abs(v) for v in buf))
    k = 0.9 / peak if peak > 0.9 else 1.0
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * k)) * 32767)) for v in buf))


def main():
    save("pick", mix(tone(note(84), 0.12, 0.4, decay=0.05), tone(note(91), 0.12, 0.3, decay=0.05), offsets=[0, 0.05]))
    save("lit", mix(*[tone(note(m), 0.6, 0.35, decay=0.25) for m in (72, 76, 79, 84)], offsets=[0, 0.08, 0.16, 0.24]))
    save("pulse", mix(tone(300, 0.5, 0.5, decay=0.2, slide=900), noise(0.4, 0.15, 0.15)))
    save("hit", mix(tone(180, 0.35, 0.6, decay=0.12, kind="square", slide=-300), noise(0.25, 0.3, 0.08, seed=2)))
    save("jump", tone(400, 0.18, 0.35, decay=0.08, slide=1200))
    save("dash", noise(0.22, 0.45, 0.07, seed=3))
    save("win", mix(*[tone(note(m), 0.9, 0.3, decay=0.4) for m in (72, 76, 79, 84, 88)],
                    offsets=[0, 0.15, 0.3, 0.45, 0.6]))
    save("lose", mix(*[tone(note(m), 0.9, 0.3, decay=0.4) for m in (67, 63, 60, 55)], offsets=[0, 0.25, 0.5, 0.75]))
    save("shade", mix(tone(110, 0.8, 0.5, attack=0.2, decay=0.4, slide=-40), tone(117, 0.8, 0.3, attack=0.2, decay=0.4)))
    save("tick", tone(1200, 0.06, 0.4, decay=0.02))
    save("wind", mix(noise(2.0, 0.25, 1.2, seed=4), tone(220, 2.0, 0.05, attack=0.6, decay=1.0)))
    save("charm", mix(*[tone(note(m), 0.3, 0.3, decay=0.1) for m in (79, 83, 86)], offsets=[0, 0.06, 0.12]))
    save("steal", tone(900, 0.4, 0.35, decay=0.2, slide=-1500))
    # night music: soft pentatonic loop (16 s)
    r = random.Random(7)
    scale = [57, 60, 62, 64, 67, 69, 72]
    tracks, offs = [], []
    for i in range(32):
        tracks.append(tone(note(r.choice(scale)), 1.6, 0.18, attack=0.15, decay=0.7))
        offs.append(i * 0.5)
    for i in range(4):
        tracks.append(tone(note(45 + (0, 5, 3, 7)[i]), 4.0, 0.12, attack=0.8, decay=2.0))
        offs.append(i * 4.0)
    buf = mix(*tracks, offsets=offs)[: SR * 16]
    save("music", buf)
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
