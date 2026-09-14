"""
Brain module for the PLUTO v2 system.
Handles intent routing, LLM reasoning, and request handling.
"""

from typing import Literal
import requests
import logging

# Import necessary modules for report generation and configuration
from core.researcher import search_topic, compile_report
from core import config


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
    """
    A class to handle LLM-based reasoning using a locally-running Ollama server.
    """

    def __init__(self):
        self.model = None
        self._discover_model()

    def _discover_model(self):
        """Discover available models from Ollama."""
        target_model = getattr(config, "LLM_MODEL_NAME", "qwen2.5:3b")
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
            if r.status_code == 200:
                data = r.json()
                available = [m.get("name", "") for m in data.get("models", [])]
                # Check exact or prefix match for target
                for m in available:
                    if target_model in m or m.startswith(target_model.split(":")[0]):
                        self.model = m
                        return
                # Prioritize optimal local models
                for pref in ["qwen2.5:3b", "qwen2.5", "qwen3:8b", "llama3.2", "llama3"]:
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
        """Send prompt to the Ollama model and return the generated text."""
        # Try discovering model if not yet verified
        if not self.model:
            self._discover_model()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        options = {
            "num_ctx": 2048,
            "temperature": 0.6
        }
        if self.model and ("8b" in self.model.lower() or "7b" in self.model.lower()):
            options["num_gpu"] = 22

        payload = {
            "model": self.model or "qwen3:8b",
            "messages": messages,
            "options": options,
            "stream": False
        }

        try:
            r = requests.post(
                "http://127.0.0.1:11434/api/chat",
                json=payload,
                timeout=120
            )
            if r.status_code != 200:
                logging.error(f"Ollama API error {r.status_code}: {r.text[:100]}")
                # Try fallback to first available model
                self._discover_model()
                return "I am currently unable to process this request through the local model."
            
            data = r.json()
            content = data.get("message", {}).get("content", "").strip()
            
            # Clean up <think>...</think> tags if present in reasoning models like Qwen 3
            import re
            cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            return cleaned_content if cleaned_content else content
        except Exception as exc:
            logging.error(f"LLMReasoner error: {exc}")
            return f"I encountered an error communicating with the local language model."



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
