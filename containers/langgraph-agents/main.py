"""
FastAPI application for LangGraph multi-agent system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from langchain_core.messages import HumanMessage, AIMessage

from config import settings
from graph.workflow import create_workflow
from graph.state import create_initial_state, MultiAgentState
from utils.logging import setup_logging, get_logger
from utils.db import close_db_pool
from utils.redis_client import close_redis_client
from services.scheduler import setup_scheduler, shutdown_scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import tasks_router, reminders_router, events_router

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])


# Global workflow instance
workflow_app = None

# Global scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting LangGraph multi-agent system")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Model: {settings.ollama_model if settings.llm_provider == 'ollama' else settings.openai_model}")

    global workflow_app, scheduler
    workflow_app = create_workflow()

    # Initialize scheduler
    logger.info("Initializing APScheduler for background jobs")
    scheduler = AsyncIOScheduler()
    setup_scheduler(scheduler)
    scheduler.start()
    logger.info("Scheduler started successfully")

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await shutdown_scheduler()
    await close_db_pool()
    await close_redis_client()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LangGraph Multi-Agent System",
    description="Multi-agent system for food, tasks, and events management",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware with restricted origins
# FIX: Use configured allowed origins instead of wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,  # FIX: Restricted to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # FIX: Specific methods only
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # FIX: Specific headers
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers for task management (replaces n8n workflows 01, 02, 03)
app.include_router(tasks_router)
app.include_router(reminders_router)
app.include_router(events_router)


# ============================================================================
# Request/Response Models
# ============================================================================

class Message(BaseModel):
    """Message model."""
    role: str = Field(..., description="Role (user or assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User identifier")
    workspace: str = Field(default="default", description="Workspace identifier")
    session_id: str = Field(..., description="Session/thread identifier")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    agent: str = Field(..., description="Agent that handled the request")
    session_id: str = Field(..., description="Session identifier")
    turn_count: int = Field(..., description="Conversation turn count")
    timestamp: str = Field(..., description="Response timestamp")


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    user_id: str
    workspace: str
    current_agent: str
    turn_count: int
    created_at: str
    updated_at: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "LangGraph Multi-Agent System",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": settings.llm_provider,
        "agents": ["food_agent", "task_agent", "event_agent"]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "llm_provider": settings.llm_provider,
    }


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")  # Allow 20 chat requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest):
    """
    Send a message to the multi-agent system.

    The system will:
    1. Route to appropriate agent
    2. Execute agent with tools
    3. Detect handoffs if needed
    4. Return response with agent information
    """
    try:
        logger.info(f"Chat request from user {chat_request.user_id}: {chat_request.message[:50]}...")

        # Create config for checkpointing
        config = {
            "configurable": {
                "thread_id": chat_request.session_id,
            }
        }

        # Get or create state
        # Note: LangGraph will load state from checkpointer if it exists
        initial_state = create_initial_state(
            user_id=chat_request.user_id,
            workspace=chat_request.workspace,
            session_id=chat_request.session_id,
            initial_message=chat_request.message
        )

        # Invoke workflow
        result = await workflow_app.ainvoke(
            initial_state,
            config=config
        )

        # Extract response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        if not last_message:
            raise HTTPException(status_code=500, detail="No response from agents")

        response_content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Create response
        return ChatResponse(
            response=response_content,
            agent=result.get("current_agent", "unknown"),
            session_id=chat_request.session_id,
            turn_count=result.get("turn_count", 0),
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error processing chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """
    Get session information.

    Args:
        session_id: Session identifier

    Returns:
        Session information
    """
    try:
        # Get state from checkpointer
        config = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        # Try to get state
        state = await workflow_app.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session not found")

        values = state.values

        return SessionInfo(
            session_id=session_id,
            user_id=values.get("user_id", "unknown"),
            workspace=values.get("workspace", "default"),
            current_agent=values.get("current_agent", "none"),
            turn_count=values.get("turn_count", 0),
            created_at=values.get("created_at", ""),
            updated_at=values.get("updated_at", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and its state.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        from graph.checkpointer import RedisCheckpointSaver

        checkpointer = RedisCheckpointSaver()
        await checkpointer.adelete(session_id)

        return {"message": f"Session {session_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, chat_request: ChatRequest):
    """
    Streaming chat endpoint (future enhancement).

    Currently not implemented but prepared for streaming responses.
    """
    raise HTTPException(
        status_code=501,
        detail="Streaming not yet implemented"
    )


# ============================================================================
# Development/Debug Endpoints
# ============================================================================

@app.get("/config")
async def get_config():
    """Get current configuration (excluding sensitive data)."""
    return {
        "llm_provider": settings.llm_provider,
        "ollama_model": settings.ollama_model if settings.llm_provider == "ollama" else None,
        "openai_model": settings.openai_model if settings.llm_provider == "openai" else None,
        "state_pruning_enabled": settings.state_pruning_enabled,
        "state_max_messages": settings.state_max_messages,
        "log_level": settings.log_level,
    }


@app.get("/scheduler/jobs")
async def get_scheduled_jobs():
    """Get list of all scheduled jobs and their status."""
    from services.scheduler import list_jobs
    return {
        "jobs": list_jobs(),
        "scheduler_running": scheduler.running if scheduler else False
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
