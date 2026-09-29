"""JARVIS beat motoru: şarkının türüne göre altyapı (beat) üretir. İnternet gerekmez.

Davul (kick/snare/hihat/clap/tom), 808/sub bas ve akor pad'ini numpy ile sentezler,
tür seçkisine göre tempo ve kalıp seçer, WAV olarak kaydeder.
"""

import ctypes
import os
import re
import struct
import wave
from pathlib import Path

import numpy as np

SR = 44100
BASE = Path(__file__).resolve().parent


def beats_dir():
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 13, None, 0, buf)  # CSIDL_MYMUSIC
    d = (Path(buf.value) if buf.value else Path.home() / "Music") / "JARVIS Beatler"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Nota adları → yarım ton (A4=440 referans)
_NOTES = {"c": -9, "c#": -8, "db": -8, "d": -7, "d#": -6, "eb": -6, "e": -5, "f": -4,
          "f#": -3, "gb": -3, "g": -2, "g#": -1, "ab": -1, "a": 0, "a#": 1, "bb": 1, "b": 2}


def note_freq(semitone_from_a4):
    return 440.0 * 2 ** (semitone_from_a4 / 12.0)


def _env(n, attack, decay, sustain=0.0, release=None):
    """Basit ADSR zarfı (örnek sayısı n)."""
    release = release if release is not None else decay
    a = int(SR * attack)
    d = int(SR * decay)
    env = np.zeros(n)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a, endpoint=False) if a else []
    d = min(d, n - a)
    if d > 0:
        env[a:a + d] = np.linspace(1, sustain, d, endpoint=False)
    if n - a - d > 0:
        env[a + d:] = sustain
    # kısa fade-out
    f = min(int(SR * 0.005), n)
    if f:
        env[-f:] *= np.linspace(1, 0, f)
    return env


def kick(dur=0.32, f0=120, f1=48, punch=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = f1 + (f0 - f1) * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * _env(n, 0.001, dur * 0.9) * punch
    click = np.random.randn(n) * np.exp(-t * 400) * 0.3
    return np.tanh((body + click) * 1.4)


def snare(dur=0.22, tone=190):
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n) * _env(n, 0.001, dur * 0.8)
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t * 22) * 0.5
    return np.tanh((noise * 0.9 + body) * 1.1)


def hihat(dur=0.05, open_=False):
    d = 0.28 if open_ else dur
    n = int(SR * d)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    # yüksek geçiren benzeri: fark alma
    noise = np.diff(noise, prepend=0)
    return noise * np.exp(-t * (10 if open_ else 60)) * 0.5


def clap(dur=0.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for off in (0, 0.008, 0.016):
        s = int(off * SR)
        seg = np.random.randn(n - s) * np.exp(-np.arange(n - s) / SR * 30)
        out[s:] += seg
    return np.tanh(out * 0.7)


def tom(dur=0.25, f=140):
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = f * np.exp(-t * 6)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(n, 0.001, dur * 0.9) * 0.8


def bass_808(freq, dur, glide_from=None, distort=1.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t * 18)
    else:
        f = np.full(n, freq)
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = _env(n, 0.004, dur * 0.5, sustain=0.7)
    return np.tanh(np.sin(phase) * env * distort)


def pad(freqs, dur, level=0.16):
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        out += np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t)
    env = _env(n, 0.05, 0.1, sustain=0.8)
    return out / max(1, len(freqs)) * env * level


# tür → tempo, akor ilerleyişi (küçük skala dereceleri), davul kalıbı (16 adım)
# X=kick, S=snare/clap, .=boş ; hats ayrı
GENRES = {
    "trap":     dict(bpm=140, prog=[0, 0, 5, 3], kick="X..X..X...X.X...", snare="....X.......X...", hat="rolls", pad=True, bass="808"),
    "drill":    dict(bpm=142, prog=[0, 3, 5, 4], kick="X....X.X..X.....", snare="....X.......X...", hat="rolls", pad=True, bass="slide"),
    "boombap":  dict(bpm=90,  prog=[0, 3, 4, 0], kick="X......X..X.....", snare="....X.......X...", hat="8th", pad=True, bass="sub", swing=0.14),
    "lofi":     dict(bpm=75,  prog=[0, 3, 5, 4], kick="X.....X...X.....", snare="....X.......X...", hat="8th", pad=True, bass="sub", swing=0.16),
    "pop":      dict(bpm=112, prog=[0, 5, 3, 4], kick="X.......X.......", snare="....X.......X...", hat="8th", pad=True, bass="sub"),
    "house":    dict(bpm=124, prog=[0, 0, 5, 5], kick="X...X...X...X...", snare="....S.......S...", hat="offbeat", pad=True, bass="sub"),
    "arabesk":  dict(bpm=100, prog=[0, 5, 6, 5], kick="X..X....X..X....", snare="....S.......S...", hat="8th", pad=True, bass="sub", scale="minor"),
    "rock":     dict(bpm=120, prog=[0, 5, 3, 4], kick="X..X....X..X....", snare="....S.......S...", hat="8th", pad=False, bass="sub"),
    "reggaeton":dict(bpm=95,  prog=[0, 3, 4, 5], kick="X..X..X.X..X..X.", snare="...S..S....S..S.", hat="8th", pad=True, bass="sub"),
}
ALIASES = {"hip hop": "boombap", "hiphop": "boombap", "rap": "trap", "lo-fi": "lofi",
           "lo fi": "lofi", "elektronik": "house", "edm": "house", "dance": "house",
           "türkçe": "arabesk", "türkü": "arabesk", "slow": "lofi"}

# doğal minör derecelerinin yarım ton karşılıkları (akor kökleri için)
MINOR_DEGREES = [0, 2, 3, 5, 7, 8, 10]


def pick_genre(name):
    n = (name or "").lower().strip()
    if n in GENRES:
        return n
    for k, v in ALIASES.items():
        if k in n:
            return v
    for g in GENRES:
        if g in n:
            return g
    return "trap"


def _place_at(track, sample, pos, gain=1.0):
    end = min(len(track), pos + len(sample))
    if 0 <= pos < len(track):
        track[pos:end] += sample[:end - pos] * gain


def make_beat(genre="trap", bpm=None, bars=8, key="A", mood="", out_name=None):
    g = GENRES[pick_genre(genre)]
    genre_name = pick_genre(genre)
    bpm = int(bpm or g["bpm"])
    if any(w in (mood or "").lower() for w in ("yavaş", "sakin", "slow")):
        bpm = int(bpm * 0.85)
    if any(w in (mood or "").lower() for w in ("hızlı", "enerjik", "fast")):
        bpm = int(bpm * 1.12)

    step_len = SR * 60 / bpm / 4          # 16'lık nota uzunluğu (örnek)
    bar_len = int(step_len * 16)
    total = bar_len * bars
    drums = np.zeros(total + SR)
    basst = np.zeros(total + SR)
    padt = np.zeros(total + SR)
    swing = g.get("swing", 0.0)

    root = _NOTES.get(key.lower(), 0)
    degrees = MINOR_DEGREES
    prog = g["prog"]

    for bar in range(bars):
        base = bar * bar_len
        deg = prog[bar % len(prog)]
        chord_semi = root + degrees[deg % 7] + (12 if deg >= 7 else 0)
        bass_freq = note_freq(chord_semi - 24)
        chord_freqs = [note_freq(chord_semi), note_freq(chord_semi + 3), note_freq(chord_semi + 7)]

        if g["pad"]:
            p = pad(chord_freqs, bar_len / SR)
            padt[base:base + len(p)] += p

        for i in range(16):
            sw = int(step_len * swing) if (i % 2 == 1) else 0
            pos = base + int(i * step_len) + sw
            if g["kick"][i] == "X":
                _place_at(drums, kick(), pos, 1.0)
            if g["snare"][i] in "S":
                _place_at(drums, clap(), pos, 0.9)
            elif g["snare"][i] == "X":
                _place_at(drums, snare(), pos, 0.9)
            # hi-hat kalıbı
            if g["hat"] == "8th" and i % 2 == 0:
                _place_at(drums, hihat(), pos, 0.5)
            elif g["hat"] == "offbeat" and i % 4 == 2:
                _place_at(drums, hihat(open_=True), pos, 0.4)
            elif g["hat"] == "rolls":
                if i % 2 == 0:
                    _place_at(drums, hihat(), pos, 0.45)
                if i in (6, 7, 14, 15):  # hızlı roll
                    for k in range(3):
                        _place_at(drums, hihat(dur=0.03), pos + int(step_len * k / 3), 0.3)
            # 808/bas: akor köküne vur
            if i in (0, 6, 10):
                if g["bass"] == "808":
                    _place_at(basst, bass_808(bass_freq, step_len * 5 / SR), pos, 0.9)
                elif g["bass"] == "slide":
                    _place_at(basst, bass_808(bass_freq, step_len * 5 / SR, glide_from=bass_freq * 1.5), pos, 0.9)
                else:
                    _place_at(basst, bass_808(bass_freq, step_len * 4 / SR, distort=0.9), pos, 0.8)

    mix = drums[:total] * 0.9 + basst[:total] * 0.8 + padt[:total] * 0.7
    peak = np.max(np.abs(mix)) or 1.0
    mix = (mix / peak) * 0.95
    stereo = np.stack([mix, mix], axis=1)

    name = re.sub(r'[<>:"/\\|?*]', "", out_name or f"{genre_name}_{bpm}bpm").strip() or "beat"
    path = beats_dir() / f"{name}.wav"
    n = 2
    while path.exists():
        path = beats_dir() / f"{name} ({n}).wav"
        n += 1
    data = (stereo * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path, genre_name, bpm
