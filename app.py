# app.py – FastAPI wrapper around PLUTO core modules

import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ------------------------------------------------------------------
# Core imports – same logic used by main.py
# ------------------------------------------------------------------
from core.brain import handle_request
from core.audio_tts import speak  # async now

app = FastAPI(
    title="PLUTO v2 Assistant UI",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

# ------------------------------------------------------------------
# Request model (JSON body from front-end)
# ------------------------------------------------------------------
class Query(BaseModel):
    text: str

# ------------------------------------------------------------------
# Helper: turn raw MP3 bytes into a data-uri for the browser
# ------------------------------------------------------------------
def _bytes_to_data_uri(data: bytes, mime: str = "audio/mpeg") -> str:
    import base64
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ------------------------------------------------------------------
# Primary endpoint – receives a text query, runs PLUTO logic, returns
# plain-text answer + audio data-uri.
# ------------------------------------------------------------------
@app.post("/process")
async def process(query: Query):
    try:
        # Run the PLUTO brain (routing, LLM, reporter)
        answer = handle_request(query.text)
        # Synthesize speech (async Edge-TTS returns MP3 bytes)
        audio_bytes = await speak(answer)
        audio_uri = _bytes_to_data_uri(audio_bytes)
        return {"answer": answer, "audio_uri": audio_uri}
    except Exception as exc:
        logging.exception("Error in /process")
        raise HTTPException(status_code=500, detail=str(exc))

# ------------------------------------------------------------------
# Simple health-check – useful while Ollama is still pulling the model
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ------------------------------------------------------------------
# Serve the static UI (index.html, optional favicon, etc.)
# ------------------------------------------------------------------
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
