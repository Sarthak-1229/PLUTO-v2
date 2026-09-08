# System Architecture State: Project PLUTO v2

## Overview
Project PLUTO v2 is a custom, self-hosted Agentic AI ecosystem. The workload is strictly divided between a heavy cloud inference server and a local hardware client to ensure maximum efficiency and desktop automation capabilities. 

## 1. Cloud GPU Server (The Brain - "PLUTO v2")
*   **Provider:** Jarvislabs.ai (Persistent storage enabled)
*   **Instance Name:** PLUTO v2
*   **Hardware:** 48GB VRAM GPU 
*   **Operating System:** Ubuntu Linux
*   **Cost Constraint:** ~₹85/hour. The server is strictly paused when not actively in a coding session to conserve funds.
*   **Software Stack:** 
    *   Ollama (for model management and swapping)
    *   Python 3.11+ 
    *   FastAPI / WebSockets (for real-time streaming)
*   **AI Models:** Open-source quantized models (e.g., Qwen 2.5 Coder 32B for logic, Ministral 8B for vision).

## 2. Local Client (The Hands & Eyes)
*   **Hardware:** Lenovo LOQ laptop (AMD Ryzen 7 7435HS, NVIDIA RTX 4050 GPU)
*   **Role:** Acts as a thin client. It captures user input, streams it to the cloud, and executes physical OS commands received from the AI.
*   **Software Stack:**
    *   Python 3.11+ virtual environment
    *   `websockets` (for connection to cloud)
    *   `pyautogui` / `pywinauto` / `os` (for system automation)
    *   `opencv-python` (for capturing screen states)

## 3. Current Project Phase: PHASE 1
*   **Status:** Text/UI-based only. 
*   **Hardware Status:** No ESP32-S3 or external microphone hardware is being used yet.
*   **Audio Status:** Voice-to-Text (Faster-Whisper) and Text-to-Speech (Piper) are delayed to Phase 2.
*   **Strict Rule:** ALL automation actions (opening folders, typing, clicking) MUST execute on the local laptop. The cloud server ONLY computes the logic and returns JSON commands.