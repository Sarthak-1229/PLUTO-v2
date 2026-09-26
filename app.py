# app.py – FastAPI wrapper around PLUTO core modules

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
    """Process a user query and return the text answer + source, WITHOUT audio.

    TTS is intentionally decoupled: synthesis takes 1.5-17s and would otherwise
    block the text from appearing. The client renders this text immediately and
    fetches audio separately via POST /speak.
    """
    try:
        # Run the PLUTO brain (with self-learning & local Ollama)
        result = handle_request(query.text)
        # handle_request returns (answer, answer_source)
        if isinstance(result, tuple):
            answer, answer_source = result
        else:
            # Backward compatibility
            answer = result
            answer_source = "local_model"

        return {"answer": answer, "answer_source": answer_source}
    except Exception as exc:
        logging.exception("Error in /process")
        return {"error": f"Processing failed: {str(exc)}", "status": "error"}


class SpeakRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"


@app.post("/speak")
async def synthesize_speech(req: SpeakRequest):
    """Synthesize speech for already-generated text and return it as a data URI.

    Thin wrapper over audio_tts.speak() — no new synthesis logic. Called by the
    client after it has already rendered the text, so a slow or failing TTS
    never delays the visible answer.
    """
    text = (req.text or "").strip()
    if not text:
        return {"audio_uri": ""}
    try:
        audio_bytes = await speak(text, voice=req.voice)
        audio_uri = _bytes_to_data_uri(audio_bytes) if audio_bytes else ""
        return {"audio_uri": audio_uri}
    except Exception as tts_err:
        logging.warning(f"TTS synthesis unavailable (likely offline): {tts_err}")
        return {"audio_uri": "", "error": "tts_unavailable"}

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
# Voice & Configuration endpoints
# ------------------------------------------------------------------
@app.get("/voices")
def get_voices():
    """Return available TTS voices."""
    try:
        from core.audio_tts import get_voice_options
        return {"voices": get_voice_options()}
    except Exception as e:
        return {"voices": ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]}

@app.get("/reports")
def list_reports():
    """List all compiled research reports."""
    from pathlib import Path
    import os
    reports_dir = Path("reports")
    items = []
    if reports_dir.exists():
        for f in reports_dir.glob("*.md"):
            if f.name == ".gitkeep":
                continue
            try:
                stat = f.stat()
                snippet = f.read_text(encoding="utf-8", errors="ignore")[:250]
                items.append({
                    "filename": f.name,
                    "title": f.stem.replace("-", " ").title(),
                    "size_bytes": stat.st_size,
                    "updated_at": stat.st_mtime,
                    "snippet": snippet
                })
            except Exception:
                pass
    items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return {"reports": items}

@app.get("/reports/{filename}")
def get_report_content(filename: str):
    """Get the full content of a specific report."""
    from pathlib import Path
    report_file = Path("reports") / filename
    if not report_file.exists() or not report_file.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        content = report_file.read_text(encoding="utf-8", errors="ignore")
        return {"filename": filename, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/reports/download/{filename}")
def download_report(filename: str):
    """Download a report file (pdf, docx, or md)."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    report_file = Path("reports") / filename
    if not report_file.exists() or not report_file.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path=str(report_file.resolve()), filename=filename)
# ------------------------------------------------------------------
# Health & Status check
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

