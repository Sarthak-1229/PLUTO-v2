"""
Brain module for the PLUTO v2 system.
Handles intent routing, LLM reasoning, and request handling.
"""

from typing import Literal

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
    A class to handle LLM-based reasoning.
    """

    def reason(self, prompt: str) -> str:
        """
        Reason over the given prompt using an LLM.

        Args:
            prompt: The prompt to reason over.

        Returns:
            str: The reasoned output.
        """
        # Placeholder implementation – in a real system this would call the LLM.
        return f"[LLM response to: {prompt}]"


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

    Args:
        text: The request text.

    Returns:
        str: The response to the request.
    """
    intent = route_intent(text)
    if intent == 'chat':
        reasoner = LLMReasoner()
        return reasoner.reason(text)
    elif intent == 'report':
        topic = _extract_topic(text)
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
