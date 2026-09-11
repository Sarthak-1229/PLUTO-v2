"""Module for audio text-to-speech (TTS) functionality.

Provides a placeholder `speak` function that will eventually synthesize speech
from text using the specified voice. Currently it returns an empty bytes
object.
"""

# This module operates with zero VRAM demand because synthesis is performed
# on the cloud via Microsoft Edge TTS service.

import edge_tts
import asyncio
from io import BytesIO
import os


def speak(text: str, voice: str = "en-US-AriaNeural") -> bytes:
    """Generate speech audio for the given text.

    Args:
        text: The text to synthesize.
        voice: The voice identifier to use for synthesis.

    Returns:
        Bytes representing the audio data.
    """
    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        buf = BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    return asyncio.run(_run())


if __name__ == "__main__":
    # Test the speak function and write output to a file.
    audio_bytes = speak("Test phrase")
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "tts_test.mp3"), "wb") as f:
        f.write(audio_bytes)
