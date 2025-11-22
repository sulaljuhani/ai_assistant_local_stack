import logging
import os
import time
import uuid
from typing import List, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

# Single-user UUID expected by the LangGraph stack
SINGLE_USER_ID = os.getenv(
    "LANGGRAPH_USER_ID",
    "00000000-0000-0000-0000-000000000001",
)

LANGGRAPH_CHAT_URL = os.getenv("LANGGRAPH_CHAT_URL", "http://localhost:8000/chat")
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY", "")
ADAPTER_API_KEY = os.getenv("OPENWEBUI_ADAPTER_API_KEY", "")
REQUEST_TIMEOUT = float(os.getenv("LANGGRAPH_REQUEST_TIMEOUT_SECONDS", "90"))

app = FastAPI(title="Open-WebUI to LangGraph Adapter")
logger = logging.getLogger("openwebui_adapter")
logging.basicConfig(level=logging.INFO)


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    model: str = "langgraph"
    messages: List[Message] = Field(min_items=1)
    stream: bool = False
    temperature: Optional[float] = None


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]


class ModelsData(BaseModel):
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelsData]


async def require_adapter_key(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> None:
    if not ADAPTER_API_KEY:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    provided = authorization.removeprefix("Bearer ")
    if provided != ADAPTER_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _langgraph_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if LANGGRAPH_API_KEY:
        headers["Authorization"] = f"Bearer {LANGGRAPH_API_KEY}"
    return headers


def _normalize_content(langgraph_payload: dict) -> str:
    # Try common keys first; fall back to the whole payload string
    for key in ("reply", "response", "content", "message", "text"):
        if key in langgraph_payload and isinstance(langgraph_payload[key], str):
            return langgraph_payload[key]
    return str(langgraph_payload)


def _extract_user_message(messages: List[Message]) -> str:
    """Extract the last user message from the messages array."""
    # Find the last user message
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    # Fallback: return the last message content
    return messages[-1].content if messages else ""


def _generate_session_id(messages: List[Message]) -> str:
    """Generate a consistent session ID based on conversation context.

    For now, we'll use a simple approach: generate a random UUID per request.
    In production, you might want to track sessions via OpenWebUI's conversation ID
    or use a header/cookie to maintain session continuity.
    """
    # TODO: Extract conversation ID from OpenWebUI if available
    # For now, generate a new session per request (stateless)
    return str(uuid.uuid4())


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, _: None = Depends(require_adapter_key)) -> ChatResponse:
    # Extract the last user message from the messages array
    user_message = _extract_user_message(request.messages)

    # Generate or extract session ID for conversation continuity
    session_id = _generate_session_id(request.messages)

    # Build the payload that LangGraph expects
    adapter_payload = {
        "message": user_message,          # Single string, not array
        "user_id": SINGLE_USER_ID,
        "workspace": "default",
        "session_id": session_id,
    }

    logger.info(f"Forwarding to LangGraph - session: {session_id}, message: {user_message[:50]}...")

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            upstream = await client.post(
                LANGGRAPH_CHAT_URL,
                json=adapter_payload,
                headers=_langgraph_headers(),
            )
    except httpx.HTTPError as exc:  # pragma: no cover - simple error guard
        logger.error("Error calling LangGraph chat endpoint", exc_info=True)
        raise HTTPException(status_code=502, detail="Upstream LangGraph error") from exc

    if upstream.status_code >= 400:
        logger.error("LangGraph returned %s: %s", upstream.status_code, upstream.text)
        raise HTTPException(status_code=502, detail="LangGraph returned an error")

    try:
        upstream_payload = upstream.json()
    except ValueError as exc:  # pragma: no cover - simple error guard
        logger.error("LangGraph response was not JSON: %s", upstream.text)
        raise HTTPException(status_code=502, detail="Invalid LangGraph response") from exc

    # Extract content from LangGraph's ChatResponse format
    content = _normalize_content(upstream_payload)

    logger.info(f"LangGraph response - agent: {upstream_payload.get('agent', 'unknown')}, length: {len(content)}")

    completion = ChatResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        created=int(time.time()),
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
    )
    return completion


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    # Minimal models endpoint so Open-WebUI doesn't fail when listing
    model_id = os.getenv("OPENWEBUI_MODEL_ID", "langgraph")
    return ModelsResponse(data=[ModelsData(id=model_id)])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=False,
    )
