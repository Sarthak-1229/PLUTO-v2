"""Speech-to-text (STT) module using FasterWhisper.

Provides a `transcribe` function that loads the model on demand, logs VRAM usage,
and unloads the model to free resources.
"""

import logging
import os

# Conditional import of torch; may not be installed.
try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

from faster_whisper import WhisperModel

# Import configuration and logger from the core package.
from .config import STT_MODEL_SIZE
from .logger import logger


def _get_device() -> str:
    """Return the best device for Whisper inference.

    Prefers CUDA if torch is available and a GPU is present; otherwise falls back
    to CPU.
    """
    if torch and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _log_vram(stage: str, device: str) -> None:
    """Log VRAM usage for the given stage.

    Args:
        stage: Description of the current stage (e.g., "before loading").
        device: The device being used ("cuda" or "cpu").
    """
    if device == "cuda" and torch:
        allocated = torch.cuda.memory_allocated()
        logger.info(f"VRAM {stage}: {allocated / (1024 ** 2):.2f} MB allocated")
    else:
        logger.info(f"VRAM {stage}: CUDA not available; running on CPU")


def transcribe(audio_path: str) -> str:
    """Transcribe an audio file using FasterWhisper.

    The model is loaded lazily, VRAM usage is logged before and after loading,
    and the model is explicitly deleted after transcription to free memory.

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        The transcription as a single string.
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    device = _get_device()
    _log_vram("before loading", device)

    # Load the Whisper model.
    model = WhisperModel(STT_MODEL_SIZE, device=device, compute_type="float16" if device == "cuda" else "int8")
    _log_vram("after loading", device)

    # Perform transcription.
    segments, _ = model.transcribe(audio_path)
    transcript = " ".join([segment.text for segment in segments])

    # Clean up to free VRAM.
    del model
    if device == "cuda" and torch:
        torch.cuda.empty_cache()
    _log_vram("after cleanup", device)

    return transcript.strip()


if __name__ == "__main__":
    # Demonstration block.
    demo_device = _get_device()
    _log_vram("initial", demo_device)
    # Assume a file named 'sample.wav' exists in the current directory.
    sample_path = "sample.wav"
    try:
        result = transcribe(sample_path)
        print("Transcription:")
        print(result)
    except Exception as e:
        logger.error(f"Failed to transcribe {sample_path}: {e}")
    _log_vram("final", demo_device)
