"""Benchmark the research-source fan-out: sequential vs concurrent.

Measures the real ResearchEngine sources on a live query so the parallelization
change (core/research/engine.py) can be reported with before/after numbers.

Usage: python scripts/bench_research.py "your query here"
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.research.engine import ResearchEngine, PER_SOURCE_TIMEOUT

QUERY = sys.argv[1] if len(sys.argv) > 1 else "quantum error correction breakthroughs 2026"
# Exercise the full expert source set so the fan-out is meaningful.
SOURCES = ["duckduckgo", "wikipedia", "arxiv", "pubmed", "news", "github"]
MAX_RESULTS = 6


def main() -> None:
    engine = ResearchEngine()
    active = [s for s in SOURCES if s in engine.sources]

    # --- Sequential (old behavior): one source at a time ---
    seq_start = time.perf_counter()
    per_source = {}
    seq_docs = 0
    for name in active:
        t0 = time.perf_counter()
        try:
            docs = engine.sources[name].search(QUERY, MAX_RESULTS)
            per_source[name] = (time.perf_counter() - t0, len(docs))
            seq_docs += len(docs)
        except Exception as exc:
            per_source[name] = (time.perf_counter() - t0, f"error: {exc}")
    seq_total = time.perf_counter() - seq_start

    # --- Concurrent (new behavior): thread pool with per-source timeout ---
    par_start = time.perf_counter()
    par_docs = 0
    with ThreadPoolExecutor(max_workers=len(active)) as executor:
        futures = {executor.submit(engine.sources[n].search, QUERY, MAX_RESULTS): n for n in active}
        try:
            for fut in as_completed(futures, timeout=PER_SOURCE_TIMEOUT + 2):
                try:
                    par_docs += len(fut.result(timeout=PER_SOURCE_TIMEOUT))
                except Exception:
                    pass
        except TimeoutError:
            pass
    par_total = time.perf_counter() - par_start

    print(f"Query: {QUERY!r}")
    print(f"Sources: {active}")
    print(f"PER_SOURCE_TIMEOUT = {PER_SOURCE_TIMEOUT}s\n")
    print("Per-source (sequential timing):")
    for name, (dt, n) in per_source.items():
        print(f"  {name:12s} {dt:6.2f}s  docs={n}")
    print()
    print(f"SEQUENTIAL total: {seq_total:6.2f}s  (sum of all sources, {seq_docs} docs)")
    print(f"CONCURRENT total: {par_total:6.2f}s  ({par_docs} docs)")
    if par_total > 0:
        print(f"Speedup:          {seq_total / par_total:.2f}x")


if __name__ == "__main__":
    main()
