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

# ------------------------------------------------------------------
# Recording / silence-detection tuning (configurable).
#   MAX_RECORDING_SECONDS       – hard ceiling; recording always stops here.
#   SILENCE_CONSECUTIVE_SECONDS – stop early after this much continuous quiet
#                                 (only once speech has actually been heard).
#   SILENCE_THRESHOLD           – normalized RMS (0..1) below which a 100ms
#                                 block counts as "silence".
# These were previously referenced but never defined here (NameError at
# runtime); defined locally so main.py is self-contained.
# ------------------------------------------------------------------
MAX_RECORDING_SECONDS = 15
SILENCE_CONSECUTIVE_SECONDS = 1.5
SILENCE_THRESHOLD = 0.02  # normalized RMS; speech typically >> this

# Simple cross‑platform audio recording.
# We use the `sounddevice` library which works on Windows, macOS and Linux.
# It records to a NumPy array which we then write to a temporary WAV file using
# `scipy.io.wavfile`.  If the library is missing we fall back to a helpful error.

def record_audio(sample_rate: int = 16000, block_seconds: float = 0.1) -> str:
    """Record from the microphone until silence or the max-duration ceiling.

    Streams audio in short blocks and computes the RMS of each block. Recording
    stops when EITHER:
      - ``MAX_RECORDING_SECONDS`` of audio has been captured (hard ceiling), OR
      - ``SILENCE_CONSECUTIVE_SECONDS`` of continuous near-silence is observed
        *after* speech has actually been detected (so the initial pause before
        the user starts talking never triggers an early cut-off).

    Timing is driven by the audio device (``stream.read`` blocks until a block
    is available), not wall-clock sleeps, so the captured buffer is always the
    real recorded audio — unlike the previous implementation, which sampled an
    unfilled region of a pre-allocated buffer.

    Args:
        sample_rate: Capture sample rate (Hz).
        block_seconds: Analysis block size in seconds (RMS is computed per block).

    Returns:
        Path to a temporary WAV file containing the trimmed recording.
    """
    logging.info(
        "Recording (max %ss, auto-stop after %.1fs of silence)...",
        MAX_RECORDING_SECONDS, SILENCE_CONSECUTIVE_SECONDS,
    )
    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io.wavfile import write as wav_write
    except ImportError as e:
        logging.error(
            "Audio recording dependencies missing. Install `sounddevice`, `numpy`, and `scipy`."
        )
        raise e

    block_size = max(1, int(sample_rate * block_seconds))
    max_blocks = int(MAX_RECORDING_SECONDS / block_seconds)
    silence_blocks_needed = int(SILENCE_CONSECUTIVE_SECONDS / block_seconds)

    frames = []
    silence_run = 0
    heard_speech = False
    stop_reason = "max duration"

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16",
                        blocksize=block_size) as stream:
        for _ in range(max_blocks):
            block, _overflowed = stream.read(block_size)
            frames.append(block.copy())

            # RMS of this block, normalized to 0..1 for a 16-bit signal.
            block_float = block.astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(block_float ** 2))) if block_float.size else 0.0

            if rms >= SILENCE_THRESHOLD:
                heard_speech = True
                silence_run = 0
            else:
                silence_run += 1

            # Only allow a silence-triggered stop once we've heard real speech,
            # so leading silence can't end the recording immediately.
            if heard_speech and silence_run >= silence_blocks_needed:
                stop_reason = f"{SILENCE_CONSECUTIVE_SECONDS}s silence"
                break

    if frames:
        recording = np.concatenate(frames, axis=0)
    else:
        recording = np.zeros((0, 1), dtype="int16")

    duration_s = len(recording) / sample_rate
    logging.info("Recording stopped (%s) — %.1fs captured.", stop_reason, duration_s)

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
            # Record audio segment (silence-terminated, capped at max duration).
            wav_path = record_audio()
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

            # Log raw transcription immediately
            logging.info(f"TRANSCRIPTION: '{text}'")

            if not text or len(text.strip()) < 2:
                logging.warning("Empty or very short transcription, skipping")
                continue

            # Route request to brain.
            logging.info("Routing request to brain...")
            response_text = handle_request(text)
            logging.info("Brain response: %s", response_text)

            # Synthesize speech.
            logging.info("Synthesizing response audio...")
            audio_data = speak(response_text)
            # `speak` is expected to return raw audio bytes or a path; we handle both.
            if isinstance(audio_data, bytes):
                # Write MP3 bytes to a temporary file and open with the default system player.
                fd, out_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                with open(out_path, "wb") as f:
                    f.write(audio_data)
                # Open the file using the default associated application (Windows).
                os.startfile(out_path)
                playback_path = out_path
            else:
                # Assume a file path is returned.
                playback_path = str(audio_data)

            # Play back the synthesized audio.
            logging.info("Playing response audio...")
            try:
                # For MP3 files we rely on the system default player.
                if playback_path.lower().endswith('.mp3'):
                    # os.startfile already launched the file above; optionally wait a short moment.
                    time.sleep(2)
                else:
                    import simpleaudio as sa
                    wave_obj = sa.WaveObject.from_wave_file(playback_path)
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
            finally:
                # Remove temporary playback file if we created one and it's a WAV.
                if isinstance(audio_data, bytes) and not playback_path.lower().endswith('.mp3'):
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
