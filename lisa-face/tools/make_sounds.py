"""LISA's sound set, synthesized from scratch.
Copyright (C) 2026 Sharat. All rights reserved.

  listen.wav  the moment she starts listening: an airy rise into a
              two-note glass bell, like a system waking up
  ack.wav     she has your command: a quick three-note confirm
  think.wav   while she works on the answer: a seamless 16-second loop
              (120 bpm) of a warm pad, a soft pentatonic arpeggio with
              echoes, ticking data hats and a felt sub pulse

Everything shares one synthetic hall reverb so the set sounds like it
lives in the same room. Run with the voice line's Python:
  lisa-voice\\.venv\\Scripts\\python.exe tools\\make_sounds.py
Writes into ../sounds/.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "sounds"
rng = np.random.default_rng(2026)


# ---------------- building blocks ----------------
def t_of(sec):
    return np.arange(int(sec * SR)) / SR


def fft_filter(x, lo=None, hi=None):
    """Brick-ish band filter with soft (1-pole-like) skirts, done in the FFT."""
    n = len(x)
    spec = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)
    gain = np.ones_like(f)
    if hi:
        gain /= np.sqrt(1 + (f / hi) ** 4)
    if lo:
        gain /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    spec = spec * (gain[:, None] if x.ndim == 2 else gain)
    return np.fft.irfft(spec, n, axis=0)


def hall_ir(seconds=2.4, decay=0.55, bright=5500):
    """Stereo impulse response: decorrelated noise, exponential tail, darkening."""
    t = t_of(seconds)
    ir = rng.standard_normal((len(t), 2)) * np.exp(-t / decay)[:, None]
    ir = fft_filter(ir, lo=180, hi=bright)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]  # pre-delay feel
    return ir / np.sqrt((ir ** 2).sum(axis=0, keepdims=True))


IR = hall_ir()


def reverb(dry, wet=0.3, circular=False):
    """Convolve with the hall. circular=True wraps the tail to the start (for loops)."""
    n = len(dry)
    if circular:
        size = n
        D = np.fft.rfft(dry, size, axis=0)
        ir = np.zeros((size, 2))
        m = min(size, len(IR))
        ir[:m] = IR[:m]
        R = np.fft.rfft(ir, size, axis=0)
        w = np.fft.irfft(D * R, size, axis=0)
    else:
        size = n + len(IR)
        D = np.fft.rfft(dry, size, axis=0)
        R = np.fft.rfft(IR, size, axis=0)
        w = np.fft.irfft(D * R, size, axis=0)
        dry = np.vstack([dry, np.zeros((len(IR), 2))])
    return dry * (1 - wet * 0.5) + w * wet


def env(n, attack, decay, sustain=0.0, curve=1.0):
    e = np.exp(-np.arange(n) / (decay * SR)) ** curve
    e = sustain + (1 - sustain) * e
    a = max(1, int(attack * SR))
    e[:a] *= np.sin(np.linspace(0, np.pi / 2, a))
    return e


def bell(freq, dur, bright=1.0):
    """Glassy bell: inharmonic partials, each with its own decay, gentle vibrato."""
    t = t_of(dur)
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 5.2 * t) * (1 - np.exp(-t * 3))
    out = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1, .9), (2.0, .45 * bright, .5), (3.01, .25 * bright, .32),
                            (4.2, .14 * bright, .2), (5.43, .07 * bright, .12)]:
        out += amp * np.sin(2 * np.pi * freq * ratio * np.cumsum(vib) / SR) * env(len(t), .002, dec)
    return out


def pluck(freq, dur, fm=1.2):
    t = t_of(dur)
    mod = fm * np.exp(-t * 18) * np.sin(2 * np.pi * freq * 2 * t)
    return np.sin(2 * np.pi * freq * t + mod) * env(len(t), .003, .16)


def pan(mono, p):
    """p in -1..1, equal power."""
    a = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def place(buf, sig, at, wrap=False):
    i = int(at * SR)
    if wrap:                       # loops: whatever runs past the end comes back at the start
        idx = (i + np.arange(len(sig))) % len(buf)
        np.add.at(buf, idx, sig)
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def finish(x, peak_db=-3.0):
    x = x - x.mean(axis=0)
    return x * (10 ** (peak_db / 20) / np.abs(x).max())


def write(name, x):
    OUT.mkdir(exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {name}  {len(x) / SR:.2f}s")


# ---------------- listen.wav: waking up ----------------
def make_listen():
    buf = np.zeros((int(0.9 * SR), 2))
    # airy rise: noise swept upward through a band
    t = t_of(0.32)
    noise = rng.standard_normal(len(t))
    swoosh = np.zeros_like(noise)
    for k, (lo, hi) in enumerate([(400, 1200), (900, 2600), (2000, 6000), (4000, 11000)]):
        seg = fft_filter(noise, lo=lo, hi=hi)
        w = np.clip(1 - abs(t / 0.32 * 4 - k - .5), 0, 1)       # crossfade the bands upward
        swoosh += seg * w
    swoosh *= np.sin(np.pi * t / 0.32) ** 2 * 0.22
    place(buf, pan(swoosh, -.2), 0)
    # felt thump for weight
    t = t_of(0.12)
    place(buf, pan(np.sin(2 * np.pi * 90 * t * (1 - t * 2)) * env(len(t), .002, .04) * .45, 0), .06)
    # the two-note bell: E6 then B6, left then right, with an octave shimmer
    place(buf, pan(bell(1318.5, .85) * .55, -.3), .07)
    place(buf, pan(bell(1975.5, .8) * .5, .3), .15)
    place(buf, pan(bell(3951, .4, .5) * .08, .45), .15)
    write("listen.wav", finish(reverb(buf, wet=.38), -4))


# ---------------- ack.wav: got it ----------------
def make_ack():
    buf = np.zeros((int(0.6 * SR), 2))
    for i, (f, p) in enumerate([(880, -.35), (1318.5, 0), (1760, .35)]):
        place(buf, pan(pluck(f, .3) * (.6 - i * .08), p), i * .065)
        place(buf, pan(bell(f * 2, .25, .4) * .06, p), i * .065)
    write("ack.wav", finish(reverb(buf, wet=.3), -6))


# ---------------- think.wav: working on it (seamless loop) ----------------
def make_think():
    bpm, bars = 120, 8
    beat = 60 / bpm
    dur = bars * 4 * beat                                   # 16 s
    n = int(dur * SR)
    t = np.arange(n) / SR
    mix = np.zeros((n, 2))

    # pad: A minor 9, detuned saw stack, darkened, breathing twice per loop
    pad = np.zeros((n, 2))
    for f in (110, 164.81, 220, 261.63, 329.63, 493.88):
        for side, det in ((0, -.35), (1, .35)):
            ph = rng.uniform(0, 1)
            # whole cycles per loop, so the loop point never clicks
            fq = round(f * (1 + det / 1200 * 8) * dur) / dur
            saw = 2 * ((fq * t + ph) % 1) - 1
            pad[:, side] += saw
    pad = fft_filter(pad, lo=80, hi=1400)
    swell = .65 + .35 * np.sin(2 * np.pi * t / (dur / 2) - np.pi / 2)
    mix += pad / np.abs(pad).max() * swell[:, None] * .30

    # arpeggio: A minor pentatonic, 8th notes, a 2-bar pattern that repeats
    scale = [440, 523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.66]
    pattern = [0, 2, 4, 5, 4, 2, 6, 4, 1, 3, 5, 7, 5, 3, 4, 2]
    step = beat / 2
    for k in range(int(dur / step)):
        f = scale[pattern[k % len(pattern)]]
        vel = .55 if k % 4 == 0 else .38
        note = pluck(f, .35) * vel
        p = .45 * np.sin(k * .9)
        place(mix, pan(note, p) * .22, k * step, wrap=True)
        place(mix, pan(note * .45, -p) * .22, k * step + beat * .75, wrap=True)   # dotted-8th echo
        place(mix, pan(note * .2, p) * .22, k * step + beat * 1.5, wrap=True)

    # data hats: very soft filtered noise ticks on 8ths, accent on the off-beat
    hat_src = fft_filter(rng.standard_normal(int(.05 * SR)), lo=6000, hi=14000)
    for k in range(int(dur / step)):
        h = hat_src * env(len(hat_src), .001, .012 if k % 2 == 0 else .025) * (.05 if k % 2 == 0 else .08)
        place(mix, pan(h, .25 if k % 2 else -.25), k * step, wrap=True)

    # sub pulse on every beat: felt more than heard
    sub_t = t_of(.25)
    sub = np.sin(2 * np.pi * 55 * sub_t) * env(len(sub_t), .01, .09) * .35
    for k in range(int(dur / beat)):
        place(mix, pan(sub, 0), k * beat, wrap=True)

    # circular reverb: the hall's tail wraps to the start too, so the loop is seamless
    mix = reverb(mix, wet=.35, circular=True)
    write("think.wav", finish(mix, -6))


if __name__ == "__main__":
    make_listen()
    make_ack()
    make_think()
