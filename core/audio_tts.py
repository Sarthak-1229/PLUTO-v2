"""
Enhanced audio TTS module with better playback handling and caching.
"""

import asyncio
import io
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128)
async def speak(text: str, voice: str = "en-US-AriaNeural") -> bytes:
    """Generate speech audio using Edge-TTS with LRU caching.

    Args:
        text: The text to synthesize.
        voice: The voice identifier (default: en-US-AriaNeural).

    Returns:
        MP3 audio bytes.
    """
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


def get_voice_options() -> list[str]:
    """Return list of available voices."""
    return [
        "en-US-AriaNeural",      # Female, American
        "en-US-GuyNeural",        # Male, American
        "en-GB-SoniaNeural",      # Female, British
        "en-GB-RyanNeural",       # Male, British
        "en-AU-NatashaNeural",    # Female, Australian
        "hi-IN-NeerjaNeural",     # Hindi
        "es-ES-ElviraNeural",     # Spanish
        "fr-FR-DeniseNeural",     # French
        "de-DE-KatjaNeural",      # German
        "ja-JP-NanamiNeural",     # Japanese
    ]
