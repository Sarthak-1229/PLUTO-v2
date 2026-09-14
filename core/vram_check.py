import warnings
import torch
import tempfile
import os
import numpy as np
from scipy.io.wavfile import write as wav_write

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.audio_stt import transcribe
from core.brain import LLMReasoner
import core.config


def get_vram_usage_mb() -> float:
    """Return current GPU memory usage in megabytes, or 0 if no GPU is available."""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / (1024 ** 2)
    return 0.0


def get_free_vram_mb() -> float:
    """Return free GPU VRAM in MB via cuda.mem_get_info(), or 0 if unavailable."""
    if torch.cuda.is_available():
        total, used = torch.cuda.mem_get_info()
        return (total - used) / (1024 ** 2)
    return 0.0


def _create_silent_wav(duration_sec: float = 0.1, sample_rate: int = 16000) -> str:
    """Create a short silent WAV file and return its path.

    Args:
        duration_sec: Length of the audio in seconds.
        sample_rate: Sample rate for the WAV file.
    """
    samples = int(duration_sec * sample_rate)
    # Mono silence (int16 zeros)
    audio = np.zeros((samples, 1), dtype=np.int16)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wav_write(path, sample_rate, audio)
    return path


def main() -> None:
    print(f"Initial VRAM usage: {get_vram_usage_mb():.2f} MB")
    print(f"Initial VRAM free:  {get_free_vram_mb():.2f} MB")

    # STT runs on CPU now (FORCE_STT_CPU=True), so it does not touch VRAM.
    # Create a tiny silent audio file for a dummy transcription.
    dummy_wav = _create_silent_wav()
    try:
        print("Running STT transcription (CPU mode — no VRAM impact)...")
        _ = transcribe(dummy_wav)
        print("STT complete (CPU).")
    except Exception as exc:
        warnings.warn(f"Dummy transcription failed: {exc}")
    finally:
        try:
            os.remove(dummy_wav)
        except OSError:
            pass

    print(f"VRAM after STT (CPU): {get_vram_usage_mb():.2f} MB allocated / {get_free_vram_mb():.2f} MB free")

    # Check free VRAM before LLM call to warn if qwen2.5:7b may not fit.
    free_before_llm = get_free_vram_mb()
    print(f"VRAM before LLM prompt: {get_vram_usage_mb():.2f} MB allocated / {free_before_llm:.2f} MB free")

    # qwen2.5:7b at Q4 quantization needs roughly 4.5 GB; allow some headroom.
    VRAM_BUDGET_MB = getattr(core.config, "VRAM_BUDGET_MB", 6000)
    if free_before_llm < 5000:
        warnings.warn(
            f"WARNING: Free VRAM ({free_before_llm:.0f} MB) is below 5 GB. "
            f"qwen2.5:7b (Q4, ~4.5 GB) may not fit comfortably. "
            f"Expected budget: {VRAM_BUDGET_MB} MB."
        )
    else:
        print(f"VRAM headroom OK: {free_before_llm:.0f} MB free (budget: {VRAM_BUDGET_MB} MB)")

    # Instantiate the LLM reasoner and run a simple prompt.
    llm = LLMReasoner()
    print("Running LLM prompt...")
    response = llm.reason("What is the capital of France?")
    print(f"LLM response: {response}")
    print(f"VRAM after LLM prompt: {get_vram_usage_mb():.2f} MB allocated / {get_free_vram_mb():.2f} MB free")

    # Verify we stay within the configured budget (LLM-only, since STT is CPU).
    total_usage = get_vram_usage_mb()
    if total_usage > VRAM_BUDGET_MB:
        warnings.warn(
            f"VRAM usage {total_usage:.2f} MB exceeds budget of {VRAM_BUDGET_MB} MB"
        )
    assert total_usage <= VRAM_BUDGET_MB, f"VRAM usage {total_usage:.0f} MB exceeded budget of {VRAM_BUDGET_MB} MB"
    print(f"All checks passed. VRAM within {VRAM_BUDGET_MB} MB budget.")


if __name__ == "__main__":
    main()
