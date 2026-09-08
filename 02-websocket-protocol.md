# WebSocket Communication Protocol

## Overview
This document defines the strict JSON payload structures used for bidirectional communication between the Local Client (Laptop) and the Cloud Server (GPU). 

*   **Port:** 8765 (Default WebSocket Port)
*   **Format:** JSON strings.

---

## 1. Client to Server (Upstream)
When the local laptop sends a message or context to the cloud AI.

**Standard Text Query:**
```json
{
  "sender": "client",
  "type": "text_prompt",
  "content": "Create a new folder named 'test_project' on my desktop."
}