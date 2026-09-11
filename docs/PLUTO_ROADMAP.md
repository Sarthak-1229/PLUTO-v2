
# Project PLUTO v2: Master Roadmap

## Phase 1: The Communicator & Researcher (CURRENT)

* **Goal:** Establish a human-like voice interaction loop and basic autonomous research capabilities.
* **Features:**
  * Voice command recognition (Wake word + STT using `faster-whisper`).
  * Verbal responses (TTS using `edge-tts`).
  * Intent Routing: AI detects whether to give a short conversational answer or trigger a deep-dive research task.
  * Research Agent: Scrapes the internet for a given topic and compiles a structured Markdown/PDF report.
* **Constraints:** Must run entirely on a 6GB VRAM local laptop.

## Phase 2: The Multi-Agent Desktop Operator

* **Goal:** Expand capabilities beyond voice and text into actual desktop actions.
* **Features:**
  * Coder Agent: AI that can write and execute code in isolated environments.
  * OS Operator: Integration with `pyautogui` or `pywinauto` to open folders, manage files, and navigate the user's PC autonomously.
  * Inter-agent communication (Supervisor agent hands tasks to Sub-agents).

## Phase 3: The Cloud Brain (JarvisLabs)

* **Goal:** Migrate the "Brain" of Pluto off the 6GB laptop onto a heavy GPU cloud provider (JarvisLabs, GridShare, Dataoorts).
* **Features:**
  * Renting 24GB-48GB VRAM instances.
  * Running massive, highly capable open-source models (e.g., Qwen 2.5 32B, Llama 3 70B).
  * Fine-tuning local open-source models specifically on the user's workflow data.
  * Local laptop acts only as a "thin client" streaming audio to the cloud.

## Phase 4: The Physical Robot (Hardware Integration)

* **Goal:** Bring Pluto into the physical world.
* **Features:**
  * Hardware desktop buddy using ESP32-S3 microcontrollers.
  * Camera module for computer vision (AI reads the user's facial expressions and physical gestures).
  * Expressive outputs (robotic movements, LED matrices for eyes/emotions).
  * Complete JARVIS-style environmental awareness.
