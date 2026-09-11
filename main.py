"""Main entry point for PLUTO voice assistant.

This script sets up a push‑to‑talk loop that records audio, transcribes it, routes the
text to the brain, synthesizes a spoken response, and plays it back.  Each stage is
logged, and if PyTorch is available the initial VRAM usage is reported.
"""

import os
import sys
import time
import tempfile
import logging
import threading

# Import core components – these modules are assumed to exist in the project.
try:
    from core.audio_stt import transcribe
    from core.audio_tts import speak
    from core.brain import handle_request
except ImportError as e:
    logging.error(f"Failed to import core modules: {e}")
    sys.exit(1)

# Optional: report initial VRAM usage if torch is installed.
try:
    import torch
    if torch.cuda.is_available():
        vram_bytes = torch.cuda.memory_allocated()
        vram_mb = vram_bytes / (1024 * 1024)
        logging.info(f"Initial VRAM usage: {vram_mb:.2f} MB")
except Exception:
    # torch not available or error – continue silently.
    pass

# Configure basic logging to stdout.
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Simple cross‑platform audio recording.
# We use the `sounddevice` library which works on Windows, macOS and Linux.
# It records to a NumPy array which we then write to a temporary WAV file using
# `scipy.io.wavfile`.  If the library is missing we fall back to a helpful error.

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    """Record `duration` seconds of mono audio and return the path to a temporary WAV file.

    Args:
        duration: Recording length in seconds.
        sample_rate: Sample rate for the WAV file.

    Returns:
        Path to the temporary WAV file.
    """
    logging.info("Recording audio (duration=%ds)...", duration)
    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io.wavfile import write as wav_write
    except ImportError as e:
        logging.error(
            "Audio recording dependencies missing. Install `sounddevice`, `numpy`, and `scipy`."
        )
        raise e

    # Record – `sd.rec` returns a NumPy array of shape (samples, channels).
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()  # Block until recording is finished.

    # Write to a temporary WAV file.
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)  # Close the file descriptor – `wav_write` will open the file.
    wav_write(path, sample_rate, recording)
    logging.info("Audio recorded to %s", path)
    return path


def main_loop():
    """Push‑to‑talk loop.

    The loop records a short audio snippet, transcribes it, forwards the text to the
    brain for handling, synthesizes the response, and plays it back.  It continues
    until the user aborts with Ctrl‑C.
    """
    logging.info("Starting push‑to‑talk loop. Press Ctrl+C to exit.")
    try:
        while True:
            # Record audio segment.
            wav_path = record_audio(duration=5)
            logging.info("Recording complete.")

            # Transcribe.
            logging.info("Transcribing audio...")
            try:
                text = transcribe(wav_path)
            finally:
                # Clean up temporary file regardless of success.
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
            logging.info("Transcription result: %s", text)

            # Route request to brain.
            logging.info("Routing request to brain...")
            response_text = handle_request(text)
            logging.info("Brain response: %s", response_text)

            # Synthesize speech.
            logging.info("Synthesizing response audio...")
            audio_data = speak(response_text)
            # `speak` is expected to return raw audio bytes or a path; we handle both.
            if isinstance(audio_data, bytes):
                # Write bytes to a temporary file for playback.
                fd, out_path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                with open(out_path, "wb") as f:
                    f.write(audio_data)
                playback_path = out_path
            else:
                # Assume a file path is returned.
                playback_path = str(audio_data)

            # Play back the synthesized audio.
            logging.info("Playing response audio...")
            try:
                # Use `simpleaudio` for cross‑platform playback.
                import simpleaudio as sa
                wave_obj = sa.WaveObject.from_wave_file(playback_path)
                play_obj = wave_obj.play()
                play_obj.wait_done()
            finally:
                # Remove temporary playback file if we created one.
                if isinstance(audio_data, bytes):
                    try:
                        os.remove(playback_path)
                    except OSError:
                        pass
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received – exiting gracefully.")
    except Exception as e:
        logging.exception("Unexpected error in main loop: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main_loop()
