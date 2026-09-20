"""Probe: what does SelfLearner.answer() return when the LLM call fails
mid-research? Simulates an Ollama outage by forcing reason() to fail, then
inspects the (answer, source) tuple the user would actually receive.

Usage: python scripts/probe_llm_failure.py
"""

from __future__ import annotations

from core.self_learner import get_self_learner
from core import brain


def main() -> None:
    learner = get_self_learner()

    # Pick a query that classifies as research AND has KB candidates, so the
    # KB-synthesis path (the one flagged for the fallback antipattern) runs.
    query = "who is the current CEO of Nvidia"
    print(f"Query: {query!r}")
    print(f"Classified as: {learner.classify_query(query)}")
    kb_hits = learner.kb.get_relevant_knowledge(query, limit=3)
    print(f"KB candidates: {len(kb_hits)}")
    if kb_hits:
        raw = kb_hits[0].get('content', kb_hits[0].get('excerpt', ''))
        print(f"Raw KB[0] content (first 200 chars): {raw[:200]!r}")
    print("-" * 70)

    # Simulate the LLM being down: force every reason() call to fail the way
    # a real Ollama outage does.
    def broken_reason(self, *args, **kwargs):
        raise ConnectionError("simulated Ollama outage (connection refused)")

    original = brain.LLMReasoner.reason
    brain.LLMReasoner.reason = broken_reason
    try:
        answer, source = learner.answer(query)
    except Exception as exc:
        print(f"answer() RAISED: {type(exc).__name__}: {exc}")
        brain.LLMReasoner.reason = original
        return
    finally:
        brain.LLMReasoner.reason = original

    print("answer() RETURNED (no exception):")
    print(f"  answer_source = {source!r}")
    print(f"  answer text   = {answer!r}")


if __name__ == "__main__":
    main()
