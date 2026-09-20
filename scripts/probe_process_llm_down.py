"""Full-stack probe: with Ollama actually stopped, drive app.py's /process
handler and print the exact JSON the browser would receive.

Confirms (a) reason() raises LLMUnavailableError on a real outage, (b) it
propagates through handle_request/answer, and (c) app.py's error boundary
turns it into an honest {"error": ..., "status": "error"} payload rather than
a 200 with fabricated content.

Usage: python scripts/probe_process_llm_down.py
"""

from __future__ import annotations

import asyncio

import app as fastapi_app
from app import Query


def main() -> None:
    query = Query(text="who is the current CEO of Nvidia")
    result = asyncio.run(fastapi_app.process(query))
    print("=" * 70)
    print("JSON returned by /process with Ollama DOWN:")
    print("=" * 70)
    for key, value in result.items():
        shown = value if len(str(value)) < 300 else str(value)[:300] + "…"
        print(f"  {key!r}: {shown!r}")
    print("=" * 70)
    if result.get("status") == "error" and "answer" not in result:
        print("PASS: honest structured error, no fabricated answer.")
    else:
        print("FAIL: returned an answer payload despite the LLM being down.")


if __name__ == "__main__":
    main()
