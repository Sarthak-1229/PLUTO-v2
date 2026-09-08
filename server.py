"""
server.py — PLUTO v2 Cloud Brain

Runs on the Jarvislabs GPU instance. Boots the Ollama connection, exposes a
FastAPI WebSocket listener on port 8765 for the Local Client (laptop), and
routes every incoming prompt through a Supervisor-Worker multi-agent chain.

STRICT RULE (see 01-architecture-state.md, Phase 1):
    This server NEVER executes OS-level actions itself. The Automation Agent
    only ever *produces* a structured JSON command — the Local Client is
    solely responsible for execution (opening folders, typing, clicking).

WebSocket message schema (LOCKED)
----------------------------------
Client -> Server (see 02-websocket-protocol.md):
    {"sender": "client", "type": "text_prompt", "content": "<user text>"}

Server -> Client:
    Text-bearing messages (text_response, error) carry a "content" string:
        {"sender": "server", "type": "text_response", "agent": "coder",
         "content": "<text>"}
    Action-bearing messages (automation_command) carry an "action" object:
        {"sender": "server", "type": "automation_command", "agent": "automation",
         "action": {"action": "create_folder",
                     "params": {"path": "~/Desktop/test_project"},
                     "description": "Create a folder named test_project"}}

Requirements:
    pip install fastapi "uvicorn[standard]" httpx ddgs
    Ollama must already be running locally (default http://localhost:11434)
    with MODEL_LOGIC pulled, e.g.: `ollama pull qwen2.5-coder:32b`

Run:
    python3 server.py
"""

import asyncio
import json
import logging
import os

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# `duckduckgo_search` was renamed to `ddgs`. Support either install so this
# script keeps working regardless of which package name someone has pulled.
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # deprecated name, still functional

# --------------------------------------------------------------------------- #
# Configuration (env-overridable for production deployments)
# --------------------------------------------------------------------------- #

WS_HOST = os.getenv("PLUTO_WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("PLUTO_WS_PORT", "8765"))  # per 02-websocket-protocol.md

OLLAMA_HOST = os.getenv("PLUTO_OLLAMA_HOST", "http://localhost:11434")

# Model assignment per 01-architecture-state.md
MODEL_LOGIC = os.getenv("PLUTO_MODEL_LOGIC", "qwen2.5-coder:32b")
MODEL_VISION = os.getenv("PLUTO_MODEL_VISION", "ministral-8b")  # Reserved for Phase 2

SEARCH_MAX_RESULTS = int(os.getenv("PLUTO_SEARCH_MAX_RESULTS", "5"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("pluto.server")


# --------------------------------------------------------------------------- #
# Ollama client
# --------------------------------------------------------------------------- #

class OllamaClient:
    """Thin async wrapper around the local Ollama REST API."""

    def __init__(self, base_url: str = OLLAMA_HOST):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=180.0)

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        try:
            resp = await self._client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except httpx.HTTPError as e:
            log.error(f"Ollama request failed for model '{model}': {e}")
            return f"[ERROR] Could not reach Ollama model '{model}': {e}"

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except httpx.HTTPError as e:
            log.error(f"Could not reach Ollama at {self.base_url}: {e}")
            return []

    async def close(self):
        await self._client.aclose()


ollama = OllamaClient()


# --------------------------------------------------------------------------- #
# Worker Agents
# --------------------------------------------------------------------------- #

class CoderAgent:
    """Writes, reviews, and debugs code. (04-agent-orchestration.md)"""

    SYSTEM_PROMPT = (
        "You are the Coder Agent inside PLUTO v2. You write, review, and "
        "debug code. Respond with clear, correct code and brief, practical "
        "explanations. Do not perform any file-system or OS actions yourself."
    )

    def __init__(self, client: OllamaClient):
        self.ollama = client

    async def run(self, prompt: str) -> str:
        return await self.ollama.chat(MODEL_LOGIC, self.SYSTEM_PROMPT, prompt)


class ResearchAgent:
    """
    Has live web-search tool access via DuckDuckGo (04-agent-orchestration.md),
    using the zero-API-key `ddgs` package. Search runs in a worker thread
    since DDGS is a blocking/sync client, keeping the asyncio event loop free.
    """

    SYSTEM_PROMPT = (
        "You are the Research Agent inside PLUTO v2. You have been given "
        "live web search results below. Synthesize a concise, accurate "
        "answer using them, and reference which result number(s) you drew "
        "from. If the results don't actually answer the question, say so "
        "plainly instead of guessing."
    )

    def __init__(self, client: OllamaClient, max_results: int = SEARCH_MAX_RESULTS):
        self.ollama = client
        self.max_results = max_results

    def _blocking_search(self, query: str) -> list[dict]:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=self.max_results))

    async def _search(self, query: str) -> list[dict]:
        try:
            return await asyncio.to_thread(self._blocking_search, query)
        except Exception as e:
            log.error(f"DuckDuckGo search failed for query {query!r}: {e}")
            return []

    async def run(self, prompt: str) -> str:
        results = await self._search(prompt)

        if not results:
            fallback_prompt = (
                f"{prompt}\n\n(Note: live web search returned no results or "
                "failed. Answer from internal knowledge and explicitly tell "
                "the user the answer may be out of date.)"
            )
            return await self.ollama.chat(MODEL_LOGIC, self.SYSTEM_PROMPT, fallback_prompt)

        context_lines = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")
            href = r.get("href", "")
            context_lines.append(f"[{i}] {title}\n{body}\nSource: {href}")
        context_block = "\n\n".join(context_lines)

        augmented_prompt = (
            f"User question: {prompt}\n\n"
            f"Live search results:\n{context_block}\n\n"
            "Using the above, answer the user's question."
        )
        return await self.ollama.chat(MODEL_LOGIC, self.SYSTEM_PROMPT, augmented_prompt)


class AutomationAgent:
    """
    Formats JSON action payloads for the Local Client to execute.
    NEVER executes anything itself — see the strict rule at the top of
    this file and in 01-architecture-state.md.
    """

    SYSTEM_PROMPT = (
        "You are the Automation Agent inside PLUTO v2. Convert the user's "
        "request into a SINGLE JSON object describing a desktop action, and "
        "reply with ONLY that JSON object — no prose, no markdown fences.\n\n"
        "Schema:\n"
        '{"action": "<create_folder|create_file|open_app|type_text|click|other>", '
        '"params": { ...action-specific fields... }, '
        '"description": "<one-line human-readable summary>"}\n\n'
        "Example:\n"
        '{"action": "create_folder", "params": {"path": "~/Desktop/test_project"}, '
        '"description": "Create a folder named test_project on the desktop"}'
    )

    def __init__(self, client: OllamaClient):
        self.ollama = client

    async def run(self, prompt: str) -> dict:
        raw = await self.ollama.chat(MODEL_LOGIC, self.SYSTEM_PROMPT, prompt)

        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
            if "action" not in parsed:
                raise ValueError("response JSON missing required 'action' key")
            parsed.setdefault("params", {})
            parsed.setdefault("description", "")
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"Automation Agent produced invalid JSON ({e}). Raw: {raw!r}")
            return {
                "action": "error",
                "params": {},
                "description": "Automation Agent could not produce a valid command.",
            }


# --------------------------------------------------------------------------- #
# Supervisor Agent (Router)
# --------------------------------------------------------------------------- #

class Supervisor:
    """
    Takes the user prompt, classifies intent, delegates to the right worker,
    and synthesizes the final response sent back over the WebSocket using
    the locked server->client schema.
    """

    ROUTES = ("coder", "research", "automation", "direct")

    ROUTING_SYSTEM_PROMPT = (
        "You are a routing classifier for a multi-agent system. Given the "
        "user's request, reply with ONLY one lowercase word from this exact "
        "set, nothing else: coder, research, automation, direct.\n\n"
        "- coder: writing, reviewing, explaining, or debugging code\n"
        "- research: needs current or external information lookup\n"
        "- automation: requires a physical action on the user's computer "
        "(opening apps, creating files/folders, clicking, typing, etc.)\n"
        "- direct: general conversation or anything not covered above"
    )

    DIRECT_SYSTEM_PROMPT = (
        "You are PLUTO, a helpful personal AI assistant. Respond "
        "conversationally and concisely."
    )

    def __init__(self, client: OllamaClient):
        self.ollama = client
        self.coder = CoderAgent(client)
        self.research = ResearchAgent(client)
        self.automation = AutomationAgent(client)

    async def classify(self, prompt: str) -> str:
        raw = await self.ollama.chat(MODEL_LOGIC, self.ROUTING_SYSTEM_PROMPT, prompt)
        first_word = raw.strip().lower().split()[0] if raw.strip() else "direct"
        route = "".join(ch for ch in first_word if ch.isalpha())
        return route if route in self.ROUTES else "direct"

    @staticmethod
    def _text_message(agent: str, content: str, msg_type: str = "text_response") -> dict:
        return {"sender": "server", "type": msg_type, "agent": agent, "content": content}

    @staticmethod
    def _action_message(agent: str, action: dict) -> dict:
        return {"sender": "server", "type": "automation_command", "agent": agent, "action": action}

    async def handle(self, prompt: str) -> dict:
        if not prompt or not prompt.strip():
            return self._text_message("supervisor", "Empty prompt received.", msg_type="error")

        route = await self.classify(prompt)
        log.info(f"Supervisor routed prompt -> '{route}'")

        if route == "coder":
            content = await self.coder.run(prompt)
            return self._text_message("coder", content)

        if route == "research":
            content = await self.research.run(prompt)
            return self._text_message("research", content)

        if route == "automation":
            action = await self.automation.run(prompt)
            return self._action_message("automation", action)

        content = await self.ollama.chat(MODEL_LOGIC, self.DIRECT_SYSTEM_PROMPT, prompt)
        return self._text_message("supervisor", content)


supervisor = Supervisor(ollama)


# --------------------------------------------------------------------------- #
# FastAPI app + WebSocket endpoint
# --------------------------------------------------------------------------- #

app = FastAPI(title="PLUTO v2 Cloud Brain")


@app.on_event("startup")
async def startup_event():
    log.info("PLUTO v2 server starting up...")
    models = await ollama.list_models()
    if not models:
        log.warning(
            "Could not list Ollama models. Is Ollama running on "
            f"{OLLAMA_HOST}? (see 03-server-boot-sequence.md)"
        )
    elif not any(MODEL_LOGIC in m for m in models):
        log.warning(
            f"Required model '{MODEL_LOGIC}' not found in Ollama. "
            f"Available: {models}. Run: ollama pull {MODEL_LOGIC}"
        )
    else:
        log.info(f"Ollama ready. Models available: {models}")


@app.on_event("shutdown")
async def shutdown_event():
    await ollama.close()


@app.get("/health")
async def health():
    return {"status": "ok", "server": "PLUTO v2"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_addr = websocket.client.host if websocket.client else "unknown"
    log.info(f"Local Client connected from {client_addr}")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps(
                    Supervisor._text_message("supervisor", "Invalid JSON received.", msg_type="error")
                ))
                continue

            if message.get("sender") != "client" or message.get("type") != "text_prompt":
                await websocket.send_text(json.dumps(
                    Supervisor._text_message(
                        "supervisor", f"Unsupported or malformed message: {message}", msg_type="error"
                    )
                ))
                continue

            user_prompt = message.get("content", "")
            log.info(f"Received prompt: {user_prompt!r}")

            try:
                response = await supervisor.handle(user_prompt)
            except Exception:
                log.exception("Supervisor failed to handle prompt")
                response = Supervisor._text_message(
                    "supervisor", "Internal error while processing your request.", msg_type="error"
                )

            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        log.info(f"Local Client disconnected: {client_addr}")
    except Exception:
        log.exception("Unexpected error in WebSocket loop")
        await websocket.close()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    log.info(f"Starting PLUTO v2 Cloud Brain on ws://{WS_HOST}:{WS_PORT}/ws")
    uvicorn.run(app, host=WS_HOST, port=WS_PORT)
