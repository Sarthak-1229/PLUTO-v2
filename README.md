# PLUTO v2 — Local AI Research & Voice Assistant

A voice-enabled AI research assistant that searches the web, answers questions, and generates reports — all running locally on your machine.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Pull the LLM model (one-time)
ollama pull qwen2.5:7b

# 3. Start the server
python -m uvicorn app:app --host 127.0.0.1 --port 8000

# 4. Open browser
open http://127.0.0.1:8000
```

Or use the batch file:
```bash
start_pluto.bat
```

## 📦 Architecture

```
User (Browser)
    │
    ▼
FastAPI Server (:8000)
    │
    ├─ POST /process ──► SelfLearner.answer()
    │                       │
    │                       ├─ is_online()? ──YES──► ResearchEngine.search()
    │                       │                          │
    │                       │                     DuckDuckGo ──►
    │                       │                     Wikipedia ──► KnowledgeBase.store()
    │                       │                     arXiv ──────►
    │                       │                     PubMed ─────►
    │                       │                     GitHub ─────►
    │                       │
    │                       └─ NO ──► KB lookup + LLMReasoner
    │
    ├─ GET /vram ──► VRAM Monitor ──► nvidia-smi / PyTorch
    │
    └─ GET /reports ──► ReportGenerator.list_reports()

LLM Reasoner ──► Ollama (127.0.0.1:11434) ──► qwen2.5:7b
TTS Engine ──► Edge-TTS (cloud API)
STT Engine ──► FasterWhisper (CPU only)
```

## ⚙️ Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `LLM_MODEL_NAME` | `qwen2.5:7b` | Primary LLM (~4.5GB VRAM at Q4) |
| `STT_MODEL_SIZE` | `small` | Whisper model for speech-to-text |
| `FORCE_STT_CPU` | `True` | STT runs on CPU to preserve VRAM for LLM |
| `VRAM_BUDGET_MB` | `6000` | Max GPU memory usage |
| `OFFLINE_MODE` | `False` | Auto-detect internet; set `True` to force offline |

### Ollama Models Directory

The Ollama models have been relocated to `models/ollama/` inside the project. Model weights are **not** tracked in git (see `.gitignore`) since they're large binary files.

To check installed models:
```bash
ollama list
```

To pull the required model:
```bash
ollama pull qwen2.5:7b
```

## 🧪 Testing

Run the test suite:
```bash
python test_pluto_agent.py
```

## 📊 Features

- **Voice Input/Output**: Speak to PLUTO, get audio responses
- **Web Research**: Searches 8 sources (DuckDuckGo, Wikipedia, arXiv, PubMed, GitHub, SEC, News)
- **Knowledge Base**: Persistent storage of learned information
- **Report Generation**: Creates PDF, DOCX, and Markdown reports
- **VRAM Monitoring**: Real-time GPU memory tracking
- **Offline Mode**: Works without internet using local LLM
- **Adaptive Responses**: Short answers for simple questions, detailed for complex ones

## 🔧 Troubleshooting

### Ollama not responding
```bash
# Start Ollama server
ollama serve

# Verify model is loaded
ollama list
```

### Port already in use
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### VRAM OOM errors
- Ensure no other GPU applications are running
- Reduce `num_ctx` in `core/brain.py` if needed
- Consider using `qwen2.5:3b` instead (faster, less VRAM)

## 📁 Project Structure

```
PLUTO v2/
├── app.py                 # FastAPI server & endpoints
├── main.py                # Legacy CLI entry point
├── test_pluto_agent.py    # Test suite
├── requirements.txt       # Python dependencies
├── start_pluto.bat        # Windows startup script
├── .gitignore            # Git ignore rules
│
├── core/                  # Core modules
│   ├── brain.py           # Intent routing & LLM reasoner
│   ├── self_learner.py    # Main AI brain
│   ├── knowledge_base.py  # Persistent knowledge storage
│   ├── researcher.py      # Multi-source search & reports
│   ├── audio_stt.py       # Speech-to-text (CPU)
│   ├── audio_tts.py       # Text-to-speech (Edge-TTS)
│   ├── vram_check.py      # GPU memory monitoring
│   ├── config.py          # Configuration
│   ├── research/          # Research engine
│   │   ├── engine.py      # Main research orchestration
│   │   ├── sources/       # 8 source integrations
│   │   └── extractors/    # Web & PDF extraction
│   └── reports/           # Report generation
│
├── ui/                    # Web interface
│   └── index.html         # Full-featured chat UI
│
├── reports/               # Generated reports
└── ollama_home/           # Ollama configuration
```

## 🎯 Roadmap

- [ ] Voice input integration in UI
- [ ] Dark mode toggle
- [ ] Conversation history persistence
- [ ] Mobile-responsive sidebar
- [ ] Advanced report templates
- [ ] Multi-language support

## 📝 License

Private project — built for personal use.
