"""Instrumented FastAPI instance used only by scripts/audit.py."""

from __future__ import annotations

import argparse
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

import uvicorn

import app as fastapi_app
from core import audio_tts, brain, knowledge_base, researcher
from core.research import engine as research_engine
from core.self_learner import SelfLearner


STATE_PATH = Path(os.environ["PLUTO_AUDIT_STATE_PATH"])
STATE: dict = {}
ORIGINALS: dict[str, tuple[object, str]] = {}


def reset_state() -> None:
    STATE.clear()
    STATE.update(
        {
            "intent": None,
            "path_taken": "unknown",
            "query_type": None,
            "kb_candidates": 0,
            "llm_call_count": 0,
            "stages": {},
        }
    )


def append_stage(name: str, started: float) -> None:
    STATE["stages"].setdefault(name, []).append(time.perf_counter() - started)


@contextmanager
def timed_stage(name: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        append_stage(name, started)


def write_state() -> None:
    temporary = STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp")
    temporary.write_text(json.dumps(STATE, indent=2), encoding="utf-8")
    temporary.replace(STATE_PATH)


def patch_function(module: object, name: str, key: str, wrapper):
    original = getattr(module, name)
    ORIGINALS[key] = (module, original)
    setattr(module, name, wrapper)


def install_instrumentation() -> None:
    original_handle_request = fastapi_app.handle_request

    def handle_request(text: str) -> str:
        reset_state()
        try:
            with timed_stage("request_handling"):
                intent = brain.route_intent(text)
                STATE["intent"] = intent
                if intent == "report":
                    STATE["path_taken"] = "report"
                return original_handle_request(text)
        finally:
            write_state()

    patch_function(fastapi_app, "handle_request", "app.handle_request", handle_request)

    original_speak = fastapi_app.speak

    async def speak(text: str, voice: str = "en-US-AriaNeural") -> bytes:
        try:
            with timed_stage("tts"):
                return await original_speak(text, voice=voice)
        finally:
            write_state()

    patch_function(fastapi_app, "speak", "app.speak", speak)

    original_reason = brain.LLMReasoner.reason

    def reason(self, *args, **kwargs):
        # Pass through all args/kwargs (incl. keyword-only num_ctx) unchanged so
        # the wrapper never breaks the real call signature.
        with timed_stage("llm_generation"):
            STATE["llm_call_count"] += 1
            return original_reason(self, *args, **kwargs)

    brain.LLMReasoner.reason = reason
    ORIGINALS["brain.LLMReasoner.reason"] = (brain.LLMReasoner, "reason")

    original_classify = SelfLearner.classify_query

    def classify_query(self, text: str):
        with timed_stage("classification"):
            query_type = original_classify(self, text)
        STATE["query_type"] = query_type
        if STATE["intent"] != "report" and query_type in {"smalltalk", "simple"}:
            STATE["path_taken"] = query_type
        return query_type

    SelfLearner.classify_query = classify_query
    ORIGINALS["SelfLearner.classify_query"] = (SelfLearner, "classify_query")

    original_get_relevant = knowledge_base.KnowledgeBase.get_relevant_knowledge

    def get_relevant_knowledge(self, query: str, limit: int = 3):
        with timed_stage("kb_lookup"):
            results = original_get_relevant(self, query, limit)
        STATE["kb_candidates"] = len(results)
        if STATE.get("query_type") == "research" and results:
            STATE["path_taken"] = "knowledge_base_cache"
        return results

    knowledge_base.KnowledgeBase.get_relevant_knowledge = get_relevant_knowledge
    ORIGINALS["KnowledgeBase.get_relevant_knowledge"] = (
        knowledge_base.KnowledgeBase,
        "get_relevant_knowledge",
    )

    original_online = SelfLearner._answer_online

    def answer_online(self, query: str) -> str:
        with timed_stage("web_research"):
            result = original_online(self, query)
        if STATE.get("query_type") == "research":
            STATE["path_taken"] = "web_research"
        return result

    SelfLearner._answer_online = answer_online
    ORIGINALS["SelfLearner._answer_online"] = (SelfLearner, "_answer_online")

    original_kb_answer = SelfLearner._answer_from_knowledge

    def answer_from_knowledge(self, query: str, knowledge):
        STATE["path_taken"] = "knowledge_base_cache"
        with timed_stage("kb_answer_generation"):
            return original_kb_answer(self, query, knowledge)

    SelfLearner._answer_from_knowledge = answer_from_knowledge
    ORIGINALS["SelfLearner._answer_from_knowledge"] = (
        SelfLearner,
        "_answer_from_knowledge",
    )

    original_llm_answer = SelfLearner._answer_from_llm

    def answer_from_llm(self, query: str) -> str:
        if STATE.get("query_type") == "research":
            STATE["path_taken"] = "local_model"
        with timed_stage("local_model_fallback"):
            return original_llm_answer(self, query)

    SelfLearner._answer_from_llm = answer_from_llm
    ORIGINALS["SelfLearner._answer_from_llm"] = (SelfLearner, "_answer_from_llm")

    original_search = research_engine.ResearchEngine.search

    def search(self, query: str, max_results: int = 10, depth: str = "standard"):
        with timed_stage("research_engine_search"):
            return original_search(self, query, max_results=max_results, depth=depth)

    research_engine.ResearchEngine.search = search
    ORIGINALS["ResearchEngine.search"] = (research_engine.ResearchEngine, "search")

    original_search_topic = researcher.search_topic

    def search_topic(query: str, max_results: int = 6):
        with timed_stage("report_source_search"):
            return original_search_topic(query, max_results=max_results)

    researcher.search_topic = search_topic
    ORIGINALS["researcher.search_topic"] = (researcher, "search_topic")

    original_compile_report = researcher.compile_report

    def compile_report(topic: str, results: list[dict], export_all: bool = True) -> dict:
        with timed_stage("report_generation"):
            return original_compile_report(topic, results, export_all=export_all)

    researcher.compile_report = compile_report
    ORIGINALS["researcher.compile_report"] = (researcher, "compile_report")


def restore_instrumentation() -> None:
    for key in reversed(list(ORIGINALS)):
        module, original = ORIGINALS[key]
        name = key.split(".")[-1]
        setattr(module, name, original)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    install_instrumentation()
    try:
        uvicorn.run(fastapi_app.app, host=args.host, port=args.port, log_level="warning")
    finally:
        restore_instrumentation()


if __name__ == "__main__":
    main()
