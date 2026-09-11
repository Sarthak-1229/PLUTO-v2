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
    """Return current VRAM usage from multiple sources."""
    result = {
        "pytorch_mb": 0,
        "ollama_mb": 0,
        "total_mb": 0,
        "budget_mb": 6000,
        "usage_percent": 0,
    }

    # 1. Check PyTorch CUDA memory
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024 * 1024)
            reserved = torch.cuda.memory_reserved() / (1024 * 1024)
            result["pytorch_mb"] = round(allocated, 2)
    except Exception:
        pass

    # 2. Check Ollama GPU memory (primary source)
    try:
        import requests
        ollama_resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if ollama_resp.status_code == 200:
            data = ollama_resp.json()
            total_ollama_mb = 0
            for model in data.get("models", []):
                # Size is in bytes, convert to MB
                size_bytes = model.get("size", 0)
                total_ollama_mb += size_bytes / (1024 * 1024)
            result["ollama_mb"] = round(total_ollama_mb, 2)
    except Exception:
        pass

    # 3. Try nvidia-smi for actual GPU usage (most accurate)
    try:
        import subprocess
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        if output:
            lines = output.split('\n')
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 2:
                    used_mb = int(parts[0].strip())
                    total_mb = int(parts[1].strip())
                    result["nvidia_used_mb"] = used_mb
                    result["nvidia_total_mb"] = total_mb
                    result["total_mb"] = used_mb
                    result["usage_percent"] = round(used_mb / total_mb * 100, 2) if total_mb > 0 else 0
                    break
    except Exception:
        # If nvidia-smi not available, use PyTorch + Ollama sum
        result["total_mb"] = round(result["pytorch_mb"] + result["ollama_mb"], 2)
        result["usage_percent"] = round(result["total_mb"] / result["budget_mb"] * 100, 2)

    return result

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
@app.get("/status")
def get_status():
    """Return system status including online/offline state."""
    try:
        from core.self_learner import get_self_learner
        learner = get_self_learner()
        is_online = learner.is_online()

        return {
            "status": "ok",
            "online": is_online,
            "model": getattr(learner.llm, 'model', 'unknown'),
            "knowledge_entries": learner.kb.get_stats().get('total_entries', 0),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ------------------------------------------------------------------
# Serve the static UI
# ------------------------------------------------------------------
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
