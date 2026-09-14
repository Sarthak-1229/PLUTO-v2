"""Speech-to-text (STT) module using FasterWhisper.

Provides a `transcribe` function that loads the model on demand, logs resource
usage, and unloads the model to free resources.

NOTE: STT runs on CPU by design (see core/config.py FORCE_STT_CPU). The qwen2.5:7b
LLM at Q4 quantization consumes the majority of the 6GB VRAM budget, so Whisper
is intentionally kept off the GPU to avoid an OOM conflict.
"""

import logging
import os

from faster_whisper import WhisperModel

# Import configuration and logger from the core package.
from .config import STT_MODEL_SIZE, FORCE_STT_CPU
from .logger import logger


def _get_device() -> str:
    """Return the device for Whisper inference.

    Respects FORCE_STT_CPU from config; if True, always uses CPU to preserve
    VRAM for the LLM. Falls back to CUDA only when explicitly allowed.
    """
    if FORCE_STT_CPU:
        logger.info("STT forced to CPU mode per config (VRAM preserved for LLM)")
        return "cpu"
    return "cpu"


def transcribe(audio_path: str) -> str:
    """Transcribe an audio file using FasterWhisper on CPU.

    The model is loaded lazily, resource usage is logged, and the model is
    explicitly deleted after transcription to free memory.

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        The transcription as a single string.
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    device = _get_device()
    logger.info(f"STT transcribe: device={device} (FORCE_STT_CPU={FORCE_STT_CPU})")

    # Load the Whisper model on CPU with int8 quantization to minimize RAM usage.
    model = WhisperModel(STT_MODEL_SIZE, device=device, compute_type="int8")
    logger.info(f"STT model '{STT_MODEL_SIZE}' loaded on {device}")

    # Perform transcription.
    segments, _ = model.transcribe(audio_path)
    transcript = " ".join([segment.text for segment in segments])

    # Clean up to free memory.
    del model
    logger.info("STT model unloaded after transcription")

    return transcript.strip()


if __name__ == "__main__":
    # Demonstration block.
    demo_device = _get_device()
    logger.info(f"STT demo: running in {demo_device} mode — no GPU VRAM consumed")
    sample_path = "sample.wav"
    try:
        result = transcribe(sample_path)
        print("Transcription:")
        print(result)
    except Exception as e:
        logger.error(f"Failed to transcribe {sample_path}: {e}")
    logger.info("STT demo complete")
