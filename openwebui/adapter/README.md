# Open-WebUI Adapter Service

This FastAPI service exposes an OpenAI-compatible `POST /v1/chat/completions` endpoint and forwards requests to the LangGraph chat endpoint. Point Open-WebUI at this service as a custom model/provider.

## Configure
Set environment variables before running:
- `LANGGRAPH_CHAT_URL` – LangGraph chat endpoint (e.g., `http://langgraph-agents:8000/chat` when running in the compose network, or `http://localhost:8000/chat` if running on the host).
- `LANGGRAPH_API_KEY` – optional bearer for the LangGraph API.
- `LANGGRAPH_USER_ID` – defaults to the single-user UUID `00000000-0000-0000-0000-000000000001`.
- `OPENWEBUI_ADAPTER_API_KEY` – bearer token that Open-WebUI must send as `Authorization: Bearer <token>`.
- `LANGGRAPH_REQUEST_TIMEOUT_SECONDS` – optional timeout (default 30).
- `PORT` – optional adapter port (default 8090).

## Run locally
```bash
cd /mnt/user/appdata/ai_stack/openwebui/adapter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LANGGRAPH_CHAT_URL=http://localhost:8000/chat
export OPENWEBUI_ADAPTER_API_KEY=your_adapter_key
PORT=8090 python main.py
```

## Connect Open-WebUI
In Open-WebUI Admin → Models → Add Custom Model/Provider:
- Base URL: `http://<adapter-host>:8090`
- Endpoint: `/v1/chat/completions`
- Authorization header: `Bearer your_adapter_key`
- Model name: set to any label (e.g., `langgraph`)

## Notes
- The adapter currently returns a single, non-streaming completion. Add SSE streaming later if desired.
- It normalizes common LangGraph response shapes by picking the first available key among `reply`, `response`, `content`, `message`, `text`.
- Errors are surfaced as HTTP 502 with minimal detail; check adapter logs for specifics.
