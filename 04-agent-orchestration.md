# Multi-Agent Orchestration Strategy

## Overview
PLUTO v2 utilizes a Supervisor-Worker multi-agent pattern. The user interacts ONLY with the Supervisor Agent.

## Agent Roles
1. **Supervisor Agent (The Router):** Takes the user prompt, plans the execution steps, delegates tasks to the sub-agents, and synthesizes the final response. 
2. **Coder Agent:** Writes, reviews, and debugs code.
3. **Research Agent:** Has access to web-search tools to gather context.
4. **Automation Agent:** Formats the JSON payloads required to trigger physical actions on the Local Laptop via the WebSocket connection.

## Framework
* Use lightweight tool-calling (via Ollama API) or a framework like CrewAI to handle the routing. 
* All agents share the same 48GB VRAM pool but are instantiated with different system prompts and tool access.