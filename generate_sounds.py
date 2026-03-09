#!/usr/bin/env python3
"""
Tron Bit sound generator.
Generates WAV files mimicking the Bit's ascending (yes) and descending (no) arpeggios
from the 1982 film. Uses only numpy and the stdlib wave module.
"""

import wave
import struct
import math
import os
import numpy as np

SAMPLE_RATE = 44100


def make_note(freq, duration, sample_rate=SAMPLE_RATE, wave_mix=None):
    """
    Generate a single synthetic note with:
    - Mix of sine + square harmonics for that retro digital character
    - Fast attack, moderate decay envelope
    """
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    # Blend sine with a softened square wave (odd harmonics) for digital texture
    sine = np.sin(2 * math.pi * freq * t)
    square = np.sign(np.sin(2 * math.pi * freq * t)) * 0.3
    # Add 3rd harmonic for brightness
    third = np.sin(2 * math.pi * freq * 3 * t) * 0.15

    signal = sine + square + third

    # Envelope: sharp attack, exponential decay
    attack_samples = int(sample_rate * 0.008)
    envelope = np.ones(n)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    decay = np.exp(-5.0 * t / duration)
    envelope *= decay

    signal *= envelope
    return signal


def make_silence(duration, sample_rate=SAMPLE_RATE):
    return np.zeros(int(sample_rate * duration))


def normalize(signal, peak=0.85):
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val * peak
    return signal


def write_wav(path, signal, sample_rate=SAMPLE_RATE):
    signal = normalize(signal)
    int_signal = (signal * 32767).astype(np.int16)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(int_signal.tobytes())
    print(f"Written: {path}")


def generate_bit_yes(path):
    """
    Ascending arpeggio — the Bit's affirmative.
    Fast staccato notes climbing up, with a final held resolution tone.
    """
    # Pentatonic-ish ascending run, ending on a bright high note
    notes = [
        (523.25, 0.07),   # C5
        (659.25, 0.07),   # E5
        (783.99, 0.07),   # G5
        (1046.5, 0.07),   # C6
        (1318.5, 0.18),   # E6 — held resolution
    ]
    gap = 0.015  # brief silence between notes

    parts = []
    for freq, dur in notes:
        parts.append(make_note(freq, dur))
        parts.append(make_silence(gap))

    signal = np.concatenate(parts)
    write_wav(path, signal)


def generate_bit_no(path):
    """
    Descending arpeggio — the Bit's negative.
    Same character but falling, with a low unsettled ending.
    """
    notes = [
        (1046.5, 0.07),   # C6
        (783.99, 0.07),   # G5
        (587.33, 0.07),   # D5
        (369.99, 0.07),   # F#4
        (261.63, 0.18),   # C4 — low, unresolved
    ]
    gap = 0.015

    parts = []
    for freq, dur in notes:
        parts.append(make_note(freq, dur))
        parts.append(make_silence(gap))

    signal = np.concatenate(parts)
    write_wav(path, signal)


def generate_bit_work_start(path):
    """
    A short two-note confirmation ping — used when a work session starts.
    """
    notes = [
        (783.99, 0.06),   # G5
        (1046.5, 0.14),   # C6
    ]
    gap = 0.01

    parts = []
    for freq, dur in notes:
        parts.append(make_note(freq, dur))
        parts.append(make_silence(gap))

    signal = np.concatenate(parts)
    write_wav(path, signal)


if __name__ == "__main__":
    os.makedirs("sounds", exist_ok=True)
    generate_bit_yes("sounds/bit_yes.wav")       # Work session complete
    generate_bit_no("sounds/bit_no.wav")          # Break complete (back to work)
    generate_bit_work_start("sounds/bit_start.wav")  # Session started
    print("\nDone. Files in ./sounds/")
