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
        self.model = getattr(config, "LLM_MODEL_NAME", "llama3.2:3b")
        # Simple health check – ping the Ollama server.
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            r.raise_for_status()
        except Exception as exc:
            logging.warning(f"Ollama not reachable ({exc}); LLMReasoner will use placeholder response.")
            self.model = None

    def reason(self, prompt: str) -> str:
        """Send *prompt* to the Ollama model and return the generated text.

        Uses streaming=True to avoid JSON parsing errors with large responses.
        Falls back to a placeholder response if Ollama is unavailable.
        """
        if not self.model:
            return f"[LLM placeholder response to: {prompt}]"
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False  # Non-streaming response – simpler to parse
            }
            r = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json=payload,
                timeout=60
            )
            r.raise_for_status()
            data = r.json()
            # Return the accumulated response text
            return data.get("response", "").strip()
        except Exception as exc:
            logging.error(f"LLMReasoner error: {exc}")
            return f"[LLM error response to: {prompt}]"


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
        # Learn about the topic first
        if learner.should_learn(topic):
            learner.learn_and_answer(topic)
        # Perform search and compile report
        results = search_topic(topic)
        md_path = compile_report(topic, results)
        # Generate summary if configured
        if config.USE_LLM_SUMMARY:
            reasoner = LLMReasoner()
            summary = reasoner.reason('Summarize the following report: ' + md_path)
        else:
            summary = "Summary not generated."
        return f"Report on {topic} saved at {md_path}. Summary: {summary}"
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
