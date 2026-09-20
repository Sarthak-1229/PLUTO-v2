"""Run the Phase A audit against an instrumented copy of the live FastAPI app.

The audit starts PLUTO on an isolated port, sends real HTTP requests through
POST /process, records nested stage timings and route selection, compares the
knowledge-base file before and after each request, and writes audit_report.md.

The product server is not modified or required to be running.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API = "http://127.0.0.1:8000/process"
TEST_CASES = [
    ("Smalltalk greeting", "hi"),
    ("Simple math", "what is 15% of 340"),
    ("Current-event research", "who is the current CEO of Nvidia"),
    ("Repeated research", "who is the current CEO of Nvidia"),
    ("Ambiguous explanatory question", "explain how binary search works"),
    ("Vagueness-prone question", "tell me about machine learning"),
]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def kb_entry_count() -> int:
    path = PROJECT_ROOT / "knowledge_db.json"
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as file:
        return len(json.load(file).get("entries", []))


def wait_for_server(base_url: str, process: subprocess.Popen, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = "server did not respond"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"audit server exited early with code {process.returncode}")
        try:
            response = requests.get(f"{base_url}/status", timeout=2)
            if response.status_code == 200:
                return
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise TimeoutError(f"audit server did not become ready: {last_error}")


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def send_query(api_url: str, query: str, timeout: float = 120.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.post(api_url, json={"text": query}, timeout=timeout)
        payload = response.json()
        return {
            "http_status": response.status_code,
            "wall_clock_seconds": time.perf_counter() - started,
            "answer": payload.get("answer", ""),
            "audio_uri_present": bool(payload.get("audio_uri")),
            "audio_uri_bytes": len(payload.get("audio_uri", "")),
            "payload": payload,
            "error": None,
        }
    except Exception as exc:
        return {
            "http_status": None,
            "wall_clock_seconds": time.perf_counter() - started,
            "answer": "",
            "audio_uri_present": False,
            "audio_uri_bytes": 0,
            "payload": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def format_seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}s"


def format_stage_breakdown(stages: dict[str, list[float]]) -> str:
    if not stages:
        return "n/a"
    parts = []
    for name, samples in stages.items():
        total = sum(samples)
        if len(samples) == 1:
            parts.append(f"{name}={total:.3f}s")
        else:
            parts.append(f"{name}={total:.3f}s ({len(samples)} calls)")
    return "; ".join(parts)


def audit_ui() -> dict[str, Any]:
    """Statically inspect the served UI; browser interaction is reported separately."""
    ui_path = PROJECT_ROOT / "ui" / "index.html"
    served_ui = PROJECT_ROOT / "ui"
    other_candidates = [
        PROJECT_ROOT / "stitch_pluto_ai_agent_interface" / "code.html",
        PROJECT_ROOT / "ui" / "test_mathjax.html",
    ]
    content = ui_path.read_text(encoding="utf-8", errors="ignore") if ui_path.exists() else ""
    controls = {
        "Voice Mode": "toggleVoiceInput" in content,
        "Knowledge Bank": "knowledge" in content.lower() and "Knowledge" in content,
        "Research Reports": "report" in content.lower() and "Report" in content,
        "Settings": "saveVoiceSetting" in content or "Settings" in content,
        "Chat/send": "handleSend" in content,
    }
    return {
        "served_directory": str(served_ui.relative_to(PROJECT_ROOT)),
        "primary_file": str(ui_path.relative_to(PROJECT_ROOT)),
        "other_candidates": [str(path.relative_to(PROJECT_ROOT)) for path in other_candidates],
        "controls_found_in_markup": controls,
        "browser_interaction": "Not automated in this harness; Phase A includes static control verification and live API checks.",
    }


def write_report(results: list[dict[str, Any]], ui_audit: dict[str, Any], output: Path) -> None:
    lines = [
        "# PLUTO v2 Phase A Audit Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Method",
        "",
        "- Sent real HTTP requests through `POST /process` on an isolated, instrumented FastAPI process.",
        "- Timed the actual request path, including classification, KB lookup, web research, LLM calls, report generation, and TTS when reached.",
        "- Counted entries in `knowledge_db.json` before and after every request.",
        "- Preserved complete raw response text below.",
        "- STT is not part of `POST /process`; browser voice input uses the Web Speech API and is therefore reported as not applicable to this endpoint.",
        "",
        "## Request Battery",
        "",
    ]

    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"### {index}. {result['description']}",
                "",
                f"- Query: `{result['query']}`",
                f"- HTTP status: {result['http_status']}",
                f"- Total wall clock: {result['wall_clock_seconds']:.3f}s",
                f"- Path taken: {result['path_taken']}",
                f"- Query classifier: {result['query_type']}",
                f"- Intent: {result['intent']}",
                f"- LLM calls: {result['llm_call_count']}",
                f"- KB candidates: {result['kb_candidates']}",
                f"- KB entries before/after: {result['kb_before']} / {result['kb_after']} (delta {result['kb_delta']:+d})",
                f"- Stage timings: {format_stage_breakdown(result['stages'])}",
                f"- TTS audio generated: {'yes' if result['audio_uri_present'] else 'no'}",
            ]
        )
        if result["error"]:
            lines.append(f"- Error: {result['error']}")
        lines.extend(["", "Raw response:", "", "```text", result["answer"] or "<empty>", "```", ""])

    lines.extend(["## UI Audit", ""])
    lines.append(f"- Live/served UI directory: `{ui_audit['served_directory']}`")
    lines.append(f"- Primary file: `{ui_audit['primary_file']}`")
    lines.append("- Other UI candidates: " + ", ".join(f"`{path}`" for path in ui_audit["other_candidates"]))
    for name, found in ui_audit["controls_found_in_markup"].items():
        lines.append(f"- `{name}` markup/handler found: {'yes' if found else 'no'}")
    lines.append(f"- Browser interaction: {ui_audit['browser_interaction']}")
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=DEFAULT_API, help="Unused for the isolated run; retained for CLI compatibility")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "audit_report.md"))
    parser.add_argument("--port", type=int, default=0, help="0 chooses a free local port")
    parser.add_argument("--keep-server", action="store_true")
    args = parser.parse_args()

    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    api_url = f"{base_url}/process"
    state_dir = Path(tempfile.mkdtemp(prefix="pluto-audit-"))
    state_path = state_dir / "state.json"
    log_path = state_dir / "server.log"
    environment = os.environ.copy()
    pythonpath = [str(PROJECT_ROOT), r"E:\AI_Workspace\python_env\user_base\Python314\site-packages"]
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    environment["PLUTO_AUDIT_STATE_PATH"] = str(state_path)

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "audit_server.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    results: list[dict[str, Any]] = []

    try:
        wait_for_server(base_url, process)
        for description, query in TEST_CASES:
            before = kb_entry_count()
            response = send_query(api_url, query)
            after = kb_entry_count()
            state = read_state(state_path)
            results.append(
                {
                    "description": description,
                    "query": query,
                    **response,
                    "path_taken": state.get("path_taken", "unknown"),
                    "query_type": state.get("query_type"),
                    "intent": state.get("intent"),
                    "llm_call_count": state.get("llm_call_count", 0),
                    "kb_candidates": state.get("kb_candidates", 0),
                    "stages": state.get("stages", {}),
                    "kb_before": before,
                    "kb_after": after,
                    "kb_delta": after - before,
                }
            )
    finally:
        log_file.close()
        if not args.keep_server:
            stop_server(process)

    write_report(results, audit_ui(), Path(args.output))
    print(f"Audit report written to {Path(args.output)}")
    if args.keep_server:
        print(f"Instrumented audit server kept running at {base_url} (PID {process.pid})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
