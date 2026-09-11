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

    # Create a tiny silent audio file for a dummy transcription.
    dummy_wav = _create_silent_wav()
    try:
        _ = transcribe(dummy_wav)
    except Exception as exc:
        warnings.warn(f"Dummy transcription failed: {exc}")
    finally:
        try:
            os.remove(dummy_wav)
        except OSError:
            pass

    print(f"VRAM after dummy transcription: {get_vram_usage_mb():.2f} MB")

    # Instantiate the LLM reasoner and run a simple prompt.
    llm = LLMReasoner()
    print(f"VRAM before LLM prompt: {get_vram_usage_mb():.2f} MB")
    response = llm.reason("What is the capital of France?")
    print(f"LLM response: {response}")
    print(f"VRAM after LLM prompt: {get_vram_usage_mb():.2f} MB")

    # Verify we stay within the configured budget, if it exists.
    budget = getattr(core.config, "VRAM_BUDGET_MB", None)
    total_usage = get_vram_usage_mb()
    if budget is not None and total_usage > budget:
        warnings.warn(
            f"VRAM usage {total_usage:.2f} MB exceeds budget of {budget} MB"
        )
    assert budget is None or total_usage <= budget, "VRAM usage exceeded budget"


if __name__ == "__main__":
    main()
