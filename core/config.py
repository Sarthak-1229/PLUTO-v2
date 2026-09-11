"""
Configuration module for PLUTO v2.
Defines constants and settings used across the application.
"""

# VRAM budget in MB for model loading
VRAM_BUDGET_MB = 6000

# Speech-to-text model size
STT_MODEL_SIZE = "small"

# Language model name for local inference
LLM_MODEL_NAME = "llama3.2:3b"

# Directory for storing reports
REPORTS_DIR = "reports"

# Flag to enable LLM-based summarization
USE_LLM_SUMMARY = True

# Note: Any model loading must respect VRAM_BUDGET_MB