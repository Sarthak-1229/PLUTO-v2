<div align="center">

# 🪐 PLUTO v2

**A fully local, voice-enabled AI research assistant** — searches the web, reasons with a local LLM, speaks its answers, and compiles cited reports. Runs entirely on a 6 GB laptop GPU.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-qwen2.5%3A7b-black?logo=ollama&logoColor=white)
![STT](https://img.shields.io/badge/STT-faster--whisper-FFB000)
![TTS](https://img.shields.io/badge/TTS-edge--tts-0078D4)
![License](https://img.shields.io/badge/License-Personal-lightgrey)

</div>

---

## Overview

PLUTO v2 is a self-contained assistant designed for a **hardware-constrained** setup (RTX 4050, 6 GB VRAM). It deliberately keeps heavy work off the GPU: the LLM (`qwen2.5:7b` via Ollama) owns the VRAM budget, speech-to-text runs on CPU, and text-to-speech uses a cloud voice API — so the whole stack fits without out-of-memory conflicts.

It answers conversational questions, performs multi-source web research, and generates saved reports — by text or by voice, online or offline.

## ✨ Features

- **🎙️ Voice Mode** — hands-free speech in and audio out via the browser's Web Speech API + edge-tts. Gracefully grays out when offline.
- **🔎 Multi-source research** — DuckDuckGo, Wikipedia, arXiv, PubMed, GitHub, SEC, and News, synthesized into a single answer.
- **📄 Report generation** — long-form research compiled to Markdown (with PDF/DOCX export) and saved to `reports/`.
- **🧮 Rich rendering** — Markdown + LaTeX/KaTeX math, rendered cleanly with no raw-TeX leakage.
- **⚡ Snappy TTS** — text is shown immediately; audio is synthesized separately so speech latency never blocks the answer.
- **📴 Offline mode** — falls back to the local LLM + knowledge base and honestly labels local-only answers.
- **🧠 Adaptive responses** — query intent (smalltalk / simple / research / creative) sets the generation budget, with anti-repetition on every path.
- **📊 VRAM monitoring** — live GPU usage via `nvidia-smi` / PyTorch, surfaced in the UI.

## 🏗️ Architecture

```
User (Browser UI  ·  ui/index.html)
   │  text / voice
   ▼
FastAPI server  (127.0.0.1:8000)
   ├─ POST /process ──► brain.handle_request()
   │                       │  intent routing
   │                       ├─ "quick answer about X"  ─► conversational LLM
   │                       └─ "create a report on X"  ─► ResearchEngine
   │                                                        │
   │                             DuckDuckGo · Wikipedia · arXiv · PubMed
   │                             GitHub · SEC · News  ──► KnowledgeBase (persisted)
   │
   ├─ POST /speak  ──► edge-tts ──► base64 audio (fetched after text renders)
   ├─ GET  /vram   ──► nvidia-smi / PyTorch
   ├─ GET  /status ──► online/offline + model + KB size
   └─ GET  /reports──► generated Markdown / PDF / DOCX
   │
   ├─ LLM reasoning ─► Ollama (127.0.0.1:11434) ─► qwen2.5:7b   [GPU]
   ├─ Speech-to-text ─► faster-whisper (small)                  [CPU]
   └─ Text-to-speech ─► edge-tts                                [cloud]
```

## 🚀 Quick Start

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com), and a CUDA GPU (optional but recommended).

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull the LLM (one-time, ~4.5 GB)
ollama pull qwen2.5:7b

# 4. Start the server
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000**. On Windows you can also just run `start_pluto.bat`.

## ⚙️ Configuration

All settings live in [`core/config.py`](core/config.py):

| Setting | Default | Description |
|---|---|---|
| `LLM_MODEL_NAME` | `qwen2.5:7b` | Primary LLM (~4.5 GB VRAM at Q4) |
| `STT_MODEL_SIZE` | `small` | faster-whisper model size |
| `FORCE_STT_CPU` | `True` | Keep STT on CPU to protect the VRAM budget |
| `VRAM_BUDGET_MB` | `6000` | Target GPU memory ceiling |
| `TTS_VOICE` | `en-US-AriaNeural` | Default edge-tts voice |
| `OFFLINE_MODE` | `False` | `False` auto-detects internet; `True` forces local-only |
| `MAX_SEARCH_RESULTS` | `5` | Results pulled per research source |

## 💬 Usage

Type or speak a request. Intent is routed automatically:

- **Quick answers** — *"Give me a quick answer about black holes"* → a short conversational reply from the local LLM.
- **Research reports** — *"Create a report on renewable energy"* → multi-source web research, synthesized into a Markdown report saved under `reports/`.
- **Voice Mode** — click **Voice Mode** to talk hands-free; PLUTO transcribes, answers, speaks the reply, and resumes listening. The control disables itself while offline (speech recognition needs connectivity).

## 🧪 Testing & Verification

```bash
# Python unit / integration tests
python test_pluto_agent.py
python test_fixes.py

# End-to-end browser verification (real Chromium via Playwright)
npm install
node scripts/browser_verify.js      # server must be running on :8000
```

`scripts/browser_verify.js` drives a real Chromium instance against the live UI and asserts, with a screenshot per check saved to `scripts/verification_screenshots/`:

| Check | Asserts |
|---|---|
| LaTeX rendering | KaTeX renders quadratic + trig math with **zero** raw-TeX leakage |
| Repetition | Generated content has no substantial line repeated 3+ times |
| TTS split | Answer text lands in the DOM **before** the audio pill |
| Voice Mode | Web Speech API present, toggle engages, offline gray-out works |

> Note: headless Chromium has no speech backend, so the suite verifies the Voice Mode **state machine and UI**, not live transcription — this is documented honestly in the script.

## 📁 Project Structure

```
PLUTO v2/
├── app.py                  # FastAPI server & endpoints
├── main.py                 # Legacy CLI entry point
├── requirements.txt        # Python dependencies
├── start_pluto.bat         # Windows startup script
│
├── core/
│   ├── brain.py            # Intent routing & LLM prompt orchestration
│   ├── self_learner.py     # Answer pipeline + online/offline logic
│   ├── knowledge_base.py   # Persistent knowledge storage
│   ├── researcher.py       # Research entry point
│   ├── audio_stt.py        # Speech-to-text (faster-whisper, CPU)
│   ├── audio_tts.py        # Text-to-speech (edge-tts)
│   ├── vram_check.py       # GPU memory monitoring
│   ├── config.py           # Configuration
│   ├── research/           # Research engine + source & extractor plugins
│   └── reports/            # Report generation (Markdown / PDF / DOCX)
│
├── ui/index.html           # Single-page chat & voice interface
├── reports/                # Generated reports
└── scripts/                # Verification tooling + screenshots
```

## 🔧 Troubleshooting

**Ollama not responding** — start it with `ollama serve`, confirm the model with `ollama list`.

**Port already in use** — `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`.

**VRAM out-of-memory** — close other GPU apps, lower `num_ctx` in `core/brain.py`, or switch to a lighter model (`ollama pull qwen2.5:3b`).

## 🎯 Design Notes

- **VRAM first.** The 6 GB budget is the binding constraint: the LLM gets the GPU, STT is pinned to CPU, and TTS is offloaded to a cloud voice — no heavy local models.
- **Text is never blocked by audio.** `/process` returns text only; `/speak` synthesizes separately, so a slow or failing TTS never delays the visible answer.
- **Honest offline behavior.** Local-only answers are labeled as such rather than pretending to have searched the web.

## 🗺️ Roadmap

- [x] Voice input/output in the browser UI
- [x] LaTeX/KaTeX math rendering
- [x] Offline-aware answering
- [ ] Conversation history persistence
- [ ] Advanced report templates
- [ ] Multi-language support

## 📝 License

Private project — built for personal use.


