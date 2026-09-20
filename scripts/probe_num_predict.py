"""Item-1 probe: measure the effect of the num_predict=300 output cap on the
research-synthesis path for "tell me about machine learning".

Runs the SAME KB-synthesis prompt twice against the live LLM:
  (A) uncapped (num_predict=None)  — old behavior
  (B) capped   (num_predict=300)   — new behavior
and reports latency, output token estimate, and whether concrete specifics
(named algorithms, a worked example, actual numbers) survive the shorter length.

Usage: python scripts/probe_num_predict.py
"""

from __future__ import annotations

import re
import time

from core.self_learner import get_self_learner, RESEARCH_NUM_CTX, RESEARCH_NUM_PREDICT

QUERY = "tell me about machine learning"

# Specificity signals we expect a grounded answer to contain.
ALGORITHMS = ["linear regression", "logistic regression", "svm", "support vector",
              "random forest", "gradient boosting", "neural network", "k-means",
              "decision tree", "naive bayes", "knn", "k-nearest"]
METRICS = ["accuracy", "precision", "recall", "f1"]


def specifics(text: str) -> dict:
    low = text.lower()
    algos = sorted({a for a in ALGORITHMS if a in low})
    metrics = sorted({m for m in METRICS if m in low})
    has_number = bool(re.search(r"\d", text))
    has_example = "example" in low or "e.g." in low or "for instance" in low
    return {
        "named_algorithms": algos,
        "named_metrics": metrics,
        "contains_number": has_number,
        "has_worked_example": has_example,
    }


def run(learner, num_predict):
    kb = learner.kb.get_relevant_knowledge(QUERY, limit=3)
    # Build the exact same prompt _answer_from_knowledge uses.
    context_parts = []
    for i, entry in enumerate(kb, 1):
        title = entry.get('title', 'Untitled')
        content = entry.get('content', entry.get('excerpt', ''))
        url = entry.get('url', '')
        if content:
            context_parts.append(f"[Source {i}: {title}]({url})\n{content[:500]}")
    context = "\n\n---\n\n".join(context_parts)
    system_prompt = (
        "You are PLUTO, an intelligent, helpful AI assistant. Answer using the "
        "knowledge provided. Keep it under ~250 words. Lead with the concrete "
        "specifics — name the actual algorithms/methods/entities, give one "
        "worked example with a real number, and cite real dates or figures. "
        "Do NOT open with a long generic definition or filler; put the "
        "specifics first because the answer length is capped."
    )
    user_prompt = f"Knowledge:\n{context}\n\nQuestion: {QUERY}\n\nAnswer:"

    t0 = time.perf_counter()
    ans = learner.llm.reason(user_prompt, system_prompt=system_prompt,
                             num_ctx=RESEARCH_NUM_CTX, num_predict=num_predict)
    dt = time.perf_counter() - t0
    return ans, dt


def report(label, ans, dt):
    words = len(ans.split())
    approx_tokens = round(words / 0.75)  # ~1.33 tokens/word rough estimate
    spec = specifics(ans)
    print(f"\n{'='*70}\n{label}\n{'='*70}")
    print(f"  latency:            {dt:6.2f}s")
    print(f"  chars / words:      {len(ans)} / {words}  (~{approx_tokens} tokens)")
    print(f"  named algorithms:   {spec['named_algorithms']}")
    print(f"  named metrics:      {spec['named_metrics']}")
    print(f"  contains a number:  {spec['contains_number']}")
    print(f"  has worked example: {spec['has_worked_example']}")
    print(f"  --- answer text ---\n{ans}\n")


def main() -> None:
    learner = get_self_learner()
    print(f"RESEARCH_NUM_CTX={RESEARCH_NUM_CTX}  RESEARCH_NUM_PREDICT={RESEARCH_NUM_PREDICT}")

    # (A) uncapped — old behavior
    ans_a, dt_a = run(learner, num_predict=None)
    report("A) UNCAPPED (num_predict=None) — old behavior", ans_a, dt_a)

    # (B) capped — new behavior
    ans_b, dt_b = run(learner, num_predict=RESEARCH_NUM_PREDICT)
    report(f"B) CAPPED (num_predict={RESEARCH_NUM_PREDICT}) — new behavior", ans_b, dt_b)

    print(f"{'='*70}")
    if dt_a > 0:
        print(f"Latency: {dt_a:.2f}s -> {dt_b:.2f}s  ({dt_a/dt_b:.2f}x faster)" if dt_b > 0 else "n/a")


if __name__ == "__main__":
    main()
