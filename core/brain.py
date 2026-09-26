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


class LLMUnavailableError(RuntimeError):
    """Raised when the local LLM (Ollama) cannot produce an answer.

    Callers must let this propagate so the API surfaces an honest error
    instead of silently substituting unrelated fallback content (e.g. raw
    knowledge-base rows) dressed up as a real answer.
    """


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

    def reason(self, prompt: str, system_prompt: str = None, *, num_ctx: int = None,
               num_predict: int = None, repeat_penalty: float = 1.3,
               repeat_last_n: int = 128) -> str:
        """Send prompt to the Ollama model using the ollama Python package.

        Every call sets an anti-repetition penalty (repeat_penalty) and window
        (repeat_last_n) — these are the real Ollama option names — to prevent the
        degenerate verbatim-repetition loops that unbounded generation can fall
        into. Callers should also pass an explicit num_predict ceiling sized to
        the task so a runaway can't generate indefinitely before being clamped.
        """
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

            # Use provided num_ctx or default
            context_size = num_ctx if num_ctx is not None else 2048

            # Cap output length independently of the context window. num_ctx is
            # how much the model can *read*; num_predict is how much it may
            # *write*. Research synthesis passes ~300 here so answers stay tight
            # (≈250-350 tokens) without shrinking the context it reasons over.
            #
            # repeat_penalty / repeat_last_n are set on EVERY call (not just
            # research): they penalize re-emitting tokens seen in the last
            # `repeat_last_n` positions, which is the direct fix for the
            # degenerate "Let's get started! 🚀"×200 loops. num_predict is the
            # backstop ceiling so even if a loop starts it can't run unbounded.
            options = {
                "num_ctx": context_size,
                "temperature": 0.6,
                "repeat_penalty": repeat_penalty,
                "repeat_last_n": repeat_last_n,
            }
            if num_predict is not None:
                options["num_predict"] = num_predict

            response = client.chat(
                model=self.model or config.LLM_MODEL_NAME,
                messages=messages,
                options=options,
                keep_alive=300,  # Keep model loaded for 5 minutes for faster follow-up
            )

            content = response.message.content.strip()

            # Strip <think>...</think> reasoning blocks emitted by reasoning
            # models like Qwen 3, keeping only the final answer text.
            cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            result = cleaned_content if cleaned_content else content

            # Update conversation history
            self._conversation_history.append({"role": "user", "content": prompt})
            self._conversation_history.append({"role": "assistant", "content": result})

            # Keep history capped
            if len(self._conversation_history) > self._max_history:
                self._conversation_history = self._conversation_history[-self._max_history:]

            return result

        except ollama.ResponseError as exc:
            logging.error(f"Ollama API error: {exc}")
            # Try recovering by rediscovering an available model, but do NOT
            # return a human-looking sentence: a failure must raise so callers
            # can't mistake it for a real answer.
            self._discover_model()
            raise LLMUnavailableError(
                f"Ollama API error: {exc}. Ensure Ollama is running (`ollama serve`) "
                f"and the model is pulled (`ollama pull {config.LLM_MODEL_NAME}`)."
            ) from exc
        except ollama.RequestError as exc:
            logging.error(f"Ollama request error: {exc}")
            raise LLMUnavailableError(
                f"Ollama request error: {exc}. Ensure Ollama is running "
                f"(`ollama serve`) and the model is pulled "
                f"(`ollama pull {config.LLM_MODEL_NAME}`)."
            ) from exc
        except LLMUnavailableError:
            raise
        except Exception as exc:
            logging.error(f"LLMReasoner error: {exc}")
            raise LLMUnavailableError(
                f"Error communicating with the local language model: {exc}"
            ) from exc


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


def handle_request(text: str) -> tuple[str, str]:
    """
    Handle an incoming request by routing intent and reasoning.

    Uses the self-learning system to search the internet when needed
    and improve answers over time.

    Args:
        text: The request text.

    Returns:
        tuple: (response_text, answer_source) where answer_source is one of:
            "local_model", "web_research", "knowledge_base_cache"
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
                summary = reasoner.reason(
                    f"Summarize the key findings of this report in 2 concise sentences:\n\n{md_content[:2000]}",
                    num_ctx=2048, num_predict=200,
                )
            except Exception as e:
                logging.warning(f"Failed to generate LLM summary: {e}")
                summary = f"Comprehensive research completed on {topic}."

        # Build response string with formats info
        files_info = []
        if "markdown" in paths: files_info.append("Markdown (.md)")
        if "pdf" in paths: files_info.append("PDF (.pdf)")
        if "docx" in paths: files_info.append("Word (.docx)")

        return f"Report on '{topic}' generated successfully in {', '.join(files_info)}. Summary: {summary}", "web_research"
    else:
        return "Unable to determine intent.", "local_model"


if __name__ == "__main__":
    # Demonstrate both routing branches
    demo_requests = [
        "Give me a quick answer about the weather.",
        "Please create a report on quarterly sales."
    ]
    for req in demo_requests:
        result = handle_request(req)
        print(f"Request: {req}\nResult: {result}\n")
