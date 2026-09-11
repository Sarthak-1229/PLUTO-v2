# app.py – FastAPI wrapper around PLUTO core modules with VRAM monitoring

import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ------------------------------------------------------------------
# Core imports
# ------------------------------------------------------------------
from core.brain import handle_request
from core.audio_tts import speak
from core.knowledge_base import get_knowledge_base
from core.self_learner import get_self_learner

app = FastAPI(
    title="PLUTO v2 Assistant UI",
    version="0.3.0",
    docs_url=None,
    redoc_url=None,
)

# ------------------------------------------------------------------
# Request model
# ------------------------------------------------------------------
class Query(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"

# ------------------------------------------------------------------
# Helper: turn raw MP3 bytes into a data-uri for the browser
# ------------------------------------------------------------------
def _bytes_to_data_uri(data: bytes, mime: str = "audio/mpeg") -> str:
    import base64
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ------------------------------------------------------------------
# Primary endpoint
# ------------------------------------------------------------------
@app.post("/process")
async def process(query: Query):
    try:
        # Run the PLUTO brain (with self-learning)
        answer = handle_request(query.text)

        # Synthesize speech (async)
        audio_bytes = await speak(answer, voice=query.voice)
        audio_uri = _bytes_to_data_uri(audio_bytes)

        return {"answer": answer, "audio_uri": audio_uri}
    except Exception as exc:
        logging.exception("Error in /process")
        raise HTTPException(status_code=500, detail=str(exc))

# ------------------------------------------------------------------
# VRAM monitoring endpoint
# ------------------------------------------------------------------
@app.get("/vram")
def get_vram():
    """Return current VRAM usage if available."""
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024 * 1024)
            reserved = torch.cuda.memory_reserved() / (1024 * 1024)
            return {
                "allocated_mb": round(allocated, 2),
                "reserved_mb": round(reserved, 2),
                "budget_mb": 6000,
                "usage_percent": round(allocated / 6000 * 100, 2),
            }
    except Exception as e:
        logging.debug(f"VRAM check failed: {e}")

    return {
        "allocated_mb": 0,
        "reserved_mb": 0,
        "budget_mb": 6000,
        "usage_percent": 0,
    }

# ------------------------------------------------------------------
# Knowledge base endpoints
# ------------------------------------------------------------------
@app.get("/knowledge/stats")
def get_knowledge_stats():
    """Return knowledge base statistics."""
    try:
        kb = get_knowledge_base()
        learner = get_self_learner()
        return {
            "kb_stats": kb.get_stats(),
            "learner_stats": learner.get_learning_stats(),
        }
    except Exception as exc:
        return {"error": str(exc)}

@app.post("/knowledge/train")
def train_on_topic(topic: str):
    """Train the AI on a specific topic."""
    try:
        learner = get_self_learner()
        result = learner.train_on_topic(topic)
        return {"success": True, "result": result}
    except Exception as exc:
        return {"error": str(exc)}

@app.get("/knowledge/search")
def search_knowledge(query: str = ""):
    """Search for relevant stored knowledge."""
    try:
        kb = get_knowledge_base()
        results = kb.get_relevant_knowledge(query or "general", limit=5)
        return {"results": results, "count": len(results)}
    except Exception as exc:
        return {"error": str(exc)}

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ------------------------------------------------------------------
# Serve the static UI
# ------------------------------------------------------------------
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
