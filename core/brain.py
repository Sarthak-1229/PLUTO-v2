"""
Brain module for the PLUTO v2 system.
Handles intent routing, LLM reasoning, and request handling.
"""

from typing import Literal
import logging
import re

# Import necessary modules for report generation and configuration
from core.researcher import search_topic, compile_report
from core import config

logger = logging.getLogger(__name__)


def route_intent(text: str) -> Literal['chat', 'report']:
    """
    Route the input text to either 'chat' or 'report' intent.

    Args:
        text: The input text to analyze.

    Returns:
        Literal['chat', 'report']: The determined intent.
    """
    lowered = text.lower()
    if any(phrase in lowered for phrase in ['give me a quick answer about', 'quick answer']):
        return 'chat'
    if any(phrase in lowered for phrase in ['create a report on', 'write a report about']):
        return 'report'
    return 'chat'


class LLMReasoner:
    """A class to handle LLM-based reasoning using a locally-running Ollama server."""

    def __init__(self):
        self.model = None
        self._discover_model()
        self._conversation_history = []  # Cap at 4 turns (8 messages)
        self._max_history = 8  # 4 user + 4 assistant messages

    def _discover_model(self):
        """Discover available models from Ollama using the ollama Python package."""
        target_model = config.LLM_MODEL_NAME
        try:
            import ollama
            client = ollama.Client(host='http://127.0.0.1:11434')
            resp = client.list()
            available = [m.model for m in resp.models]
            # Check exact or prefix match for target
            for m in available:
                if target_model in m or m.startswith(target_model.split(":")[0]):
                    self.model = m
                    return
            # Prioritize optimal local models
            for pref in ["qwen2.5", "qwen3", "llama3.2", "llama3"]:
                for m in available:
                    if pref in m:
                        self.model = m
                        return
            # If target not found, pick first available model
            if available:
                self.model = available[0]
                return
        except Exception as exc:
            logging.warning(f"Ollama server check: {exc}")
        self.model = target_model

    def reason(self, prompt: str, system_prompt: str = None) -> str:
        """Send prompt to the Ollama model using the ollama Python package."""
        # Try discovering model if not yet verified
        if not self.model:
            self._discover_model()

        try:
            import ollama
            client = ollama.Client(host='http://127.0.0.1:11434')

            # Build messages with capped conversation history
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add capped conversation history (last 4 turns)
            messages.extend(self._conversation_history[-self._max_history:])

            # Add current user prompt
            messages.append({"role": "user", "content": prompt})

            # Log VRAM before call
            vram_info = self._log_vram("before")

            response = client.chat(
                model=self.model or config.LLM_MODEL_NAME,
                messages=messages,
                options={
                    "num_ctx": 2048,
                    "temperature": 0.6,
                },
                keep_alive=300,  # Keep model loaded for 5 minutes for faster follow-up
            )

            content = response.message.content.strip()

            # Clean up  tags if present in reasoning models like Qwen 3
            cleaned_content = re.sub(r'', '', content, flags=re.DOTALL).strip()
            result = cleaned_content if cleaned_content else content

            # Update conversation history
            self._conversation_history.append({"role": "user", "content": prompt})
            self._conversation_history.append({"role": "assistant", "content": result})

            # Keep history capped
            if len(self._conversation_history) > self._max_history:
                self._conversation_history = self._conversation_history[-self._max_history:]

            # Log VRAM after call
            self._log_vram("after", vram_info)

            return result

        except ollama.ResponseError as exc:
            logging.error(f"Ollama API error: {exc}")
            # Try fallback to first available model
            self._discover_model()
            if self.model:
                return f"I am currently unable to process this request through the local model ({self.model}). Please ensure Ollama is running with `ollama serve`."
            return "I am currently unable to process this request through the local model."
        except ollama.RequestError as exc:
            logging.error(f"Ollama request error: {exc}")
            return "I am currently unable to process this request. Please ensure Ollama is running with `ollama serve` and the model is pulled with `ollama pull qwen2.5:7b`."
        except Exception as exc:
            logging.error(f"LLMReasoner error: {exc}")
            return "I encountered an error communicating with the local language model."

    def _log_vram(self, stage: str, prev_info: dict = None) -> dict:
        """Log VRAM usage before/after LLM calls."""
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024 * 1024)
                reserved = torch.cuda.memory_reserved() / (1024 * 1024)
                total, free = torch.cuda.mem_get_info()
                free_mb = free / (1024 * 1024)
                info = {
                    "allocated_mb": round(allocated, 2),
                    "reserved_mb": round(reserved, 2),
                    "free_mb": round(free_mb, 2),
                    "total_mb": round(total / (1024 * 1024), 2),
                }
                logger.info(f"VRAM {stage}: {info['allocated_mb']:.1f} MB allocated, {info['free_mb']:.1f} MB free")

                # Warn if free VRAM is low
                if info['free_mb'] < 5000:
                    logger.warning(f"Low VRAM warning: only {info['free_mb']:.0f} MB free")

                return info
        except Exception as e:
            logger.debug(f"VRAM logging failed: {e}")

        return {}



def _extract_topic(text: str) -> str:
    """Extract the report topic from a request string.

    Looks for known trigger phrases and returns the remaining text trimmed.
    """
    lowered = text.lower()
    trigger_phrases = [
        'create a report on ',
        'write a report about ',
        'create a report about ',
        'write a report on ',
        'please create a report on ',
        'please write a report about ',
        'please create a report about ',
        'please write a report on ',
    ]
    for phrase in trigger_phrases:
        if phrase in lowered:
            start = lowered.find(phrase) + len(phrase)
            # Preserve original casing for the topic
            return text[start:].strip()
    # Fallback: return the whole text if no trigger found
    return text.strip()


def handle_request(text: str) -> str:
    """
    Handle an incoming request by routing intent and reasoning.

    Uses the self-learning system to search the internet when needed
    and improve answers over time.

    Args:
        text: The request text.

    Returns:
        str: The response to the request.
    """
    from core.self_learner import get_self_learner

    intent = route_intent(text)
    learner = get_self_learner()

    if intent == 'chat':
        # Always search the internet for answers (like Claude/ChatGPT)
        return learner.answer(text)

    elif intent == 'report':
        topic = _extract_topic(text)
        # Perform search and compile report
        results = search_topic(topic)
        paths = compile_report(topic, results)
        md_path = paths.get("markdown", "")
        
        # Generate summary if configured
        summary = "Report compiled successfully."
        if config.USE_LLM_SUMMARY and md_path:
            try:
                from pathlib import Path
                md_content = Path(md_path).read_text(encoding='utf-8', errors='ignore')
                reasoner = LLMReasoner()
                summary = reasoner.reason(f"Summarize the key findings of this report in 2 concise sentences:\n\n{md_content[:2000]}")
            except Exception as e:
                logging.warning(f"Failed to generate LLM summary: {e}")
                summary = f"Comprehensive research completed on {topic}."

        # Build response string with formats info
        files_info = []
        if "markdown" in paths: files_info.append("Markdown (.md)")
        if "pdf" in paths: files_info.append("PDF (.pdf)")
        if "docx" in paths: files_info.append("Word (.docx)")
        
        return f"Report on '{topic}' generated successfully in {', '.join(files_info)}. Summary: {summary}"
    else:
        return "Unable to determine intent."


if __name__ == "__main__":
    # Demonstrate both routing branches
    demo_requests = [
        "Give me a quick answer about the weather.",
        "Please create a report on quarterly sales."
    ]
    for req in demo_requests:
        result = handle_request(req)
        print(f"Request: {req}\nResult: {result}\n")
