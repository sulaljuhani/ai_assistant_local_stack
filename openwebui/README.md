# Open-WebUI Integration Plan

This folder holds all code and notes for using Open-WebUI (http://192.168.0.12:8084/) as the frontend for the LangGraph agents.

## Goal
Expose the LangGraph agent API behind an OpenAI-compatible endpoint so Open-WebUI can talk to it as a custom model/provider. Keep everything local and reuse existing FastAPI + LangGraph services.

## Approach
- Add a thin FastAPI adapter that accepts `POST /v1/chat/completions` (OpenAI style) and forwards to the LangGraph conversation endpoint.
- Keep the adapter stateless; rely on the existing single-user `user_id` (00000000-0000-0000-0000-000000000001) that the stack already uses.
- Configure Open-WebUI to point at the adapter URL and use its API key header.

## Steps
1) Verify the upstream chat endpoint you want to call (e.g., `http://langgraph-agents:8000/chat` inside Docker network or `http://localhost:8000/chat` on host) and an API key/header if used.
2) Set environment for the adapter:
   - `LANGGRAPH_CHAT_URL` – full URL to the LangGraph chat endpoint.
   - `LANGGRAPH_API_KEY` – optional, passed as `Authorization: Bearer <key>`.
   - `OPENWEBUI_ADAPTER_API_KEY` – key the adapter will expect from Open-WebUI requests.
3) Run the adapter service (see `adapter/main.py`) near the LangGraph stack, exposing `http://<host>:8080/v1/chat/completions` (or another port if you choose).
4) In Open-WebUI Admin → Models → Add Custom Model/Provider, point it to the adapter URL, set the API key header, and make it the default for your workspace.
5) Test in Open-WebUI: send a short chat, watch `langgraph-agents` logs and adapter logs to confirm routing, memory, and tool calls work as expected.

## Notes
- The adapter returns a minimal OpenAI-style response (no streaming yet). Add streaming later if you want SSE token-by-token.
- Keep errors generic to the client; detailed logs are in the adapter.
- This stays fully local—no external calls beyond your LangGraph API.

## Docker Compose service
- Service name: `openwebui-adapter`
- Network address (inside compose network): `http://openwebui-adapter:8080/v1/chat/completions`
- Default exposed port: `${OPENWEBUI_ADAPTER_PORT:-8090}` on the host (change `OPENWEBUI_ADAPTER_PORT` in `.env` if 8090 is taken)
