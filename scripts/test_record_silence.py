"""Deterministic test of main.record_audio()'s silence-detection logic.

We cannot inject a *known spoken phrase* into the mic from an automated
environment, so instead we replace sounddevice.InputStream with a fake stream
that emits synthetic 100ms blocks with controlled RMS (loud = "speech",
near-zero = "silence"). This exercises the exact stop logic (silence after
speech, and the max-duration ceiling) and confirms the captured length adapts
to the phrase instead of being fixed at 5s.

Usage: python scripts/test_record_silence.py
"""

from __future__ import annotations

import sys
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import read as wav_read

import main

SR = 16000
BLOCK = int(SR * 0.1)  # 100ms blocks, matching record_audio default


class FakeStream:
    """Yields pre-scripted blocks; read() returns (block, overflowed)."""

    def __init__(self, blocks):
        self._blocks = blocks
        self._i = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, frames):
        if self._i < len(self._blocks):
            b = self._blocks[self._i]
        else:
            # Ran out of scripted audio: emit silence so the loop can still stop.
            b = np.zeros((frames, 1), dtype="int16")
        self._i += 1
        return b, False


def speech_block(frames):
    # ~half-scale sine -> high RMS, well above SILENCE_THRESHOLD.
    t = np.linspace(0, 0.1, frames, endpoint=False)
    tone = (np.sin(2 * np.pi * 220 * t) * 16000).astype("int16")
    return tone.reshape(-1, 1)


def silence_block(frames):
    # Tiny noise -> RMS below threshold.
    return (np.random.randint(-30, 30, size=(frames, 1))).astype("int16")


def build(script):
    """script: list of (kind, seconds)."""
    blocks = []
    for kind, secs in script:
        n = int(secs / 0.1)
        maker = speech_block if kind == "speech" else silence_block
        blocks.extend(maker(BLOCK) for _ in range(n))
    return blocks


def run_case(name, script, install):
    blocks = build(script)
    orig = sd.InputStream
    sd.InputStream = lambda *a, **k: FakeStream(blocks)
    try:
        path = main.record_audio(sample_rate=SR)
    finally:
        sd.InputStream = orig
    sr, data = wav_read(path)
    secs = len(data) / sr
    print(f"\n[{name}]")
    print(f"  scripted: {script}")
    print(f"  captured: {secs:.1f}s")
    return secs


def main_test() -> None:
    print(f"MAX_RECORDING_SECONDS={main.MAX_RECORDING_SECONDS}  "
          f"SILENCE_CONSECUTIVE_SECONDS={main.SILENCE_CONSECUTIVE_SECONDS}  "
          f"SILENCE_THRESHOLD={main.SILENCE_THRESHOLD}")

    # A) short phrase (<5s): 2s speech then silence -> ~2s + ~1.5s tail
    a = run_case("A short phrase (2s speech)", [("speech", 2.0), ("silence", 3.0)], install=True)
    okA = 3.0 <= a <= 4.5  # 2s speech + ~1.5s silence tail before stop

    # B) long phrase (>5s): 8s speech then silence -> NOT cut at 5s
    b = run_case("B long phrase (8s speech)", [("speech", 8.0), ("silence", 3.0)], install=True)
    okB = 9.0 <= b <= 10.5 and b > 5.0

    # C) no pause at all: 20s speech -> capped at MAX_RECORDING_SECONDS
    c = run_case("C no pause (20s speech)", [("speech", 20.0)], install=True)
    okC = abs(c - main.MAX_RECORDING_SECONDS) <= 0.3

    # D) leading silence must NOT end recording early: 3s silence, 2s speech, 3s silence
    d = run_case("D leading silence then speech", [("silence", 3.0), ("speech", 2.0), ("silence", 3.0)], install=True)
    okD = d >= 6.0  # 3 + 2 + ~1.5 tail; leading silence did not trigger stop

    print("\n=== verdict ===")
    for label, ok in [("A short not padded to max", okA),
                      ("B long NOT truncated at 5s", okB),
                      ("C capped at max duration", okC),
                      ("D leading silence ignored", okD)]:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    sys.exit(0 if all([okA, okB, okC, okD]) else 1)


if __name__ == "__main__":
    main_test()
