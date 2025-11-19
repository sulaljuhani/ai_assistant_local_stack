#!/usr/bin/env python3
"""
Pydantic AI Agent Service - Intelligent middleware for AI Stack

This service provides conversational AI agents that:
- Evaluate user requests for completeness
- Ask clarifying questions
- Validate data before execution
- Use tools (n8n webhooks, database) to complete actions
- Maintain conversation context

Architecture:
    AnythingLLM → Agent Service → Tools (n8n/DB) → PostgreSQL
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from dateutil import parser as date_parser

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pydantic_agent")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres-ai-stack"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "aistack"),
    "user": os.getenv("POSTGRES_USER", "aistack_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
}

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678/webhook")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ollama:llama3.2:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama-ai-stack:11434")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")

# ============================================================================
# GLOBAL STATE
# ============================================================================

db_pool: Optional[asyncpg.Pool] = None
conversation_store: Dict[str, List[Any]] = {}  # Stores conversation history

# ============================================================================
# DEPENDENCIES
# ============================================================================

class AgentDependencies:
    """Dependencies injected into agent tools at runtime."""

    def __init__(self, db_pool: asyncpg.Pool, user_id: str = DEFAULT_USER_ID):
        self.db_pool = db_pool
        self.user_id = user_id
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def query(self, sql: str, *args):
        """Execute a SELECT query."""
        async with self.db_pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def execute(self, sql: str, *args):
        """Execute an INSERT/UPDATE/DELETE query."""
        async with self.db_pool.acquire() as conn:
            return await conn.execute(sql, *args)

    async def call_n8n(self, endpoint: str, data: dict) -> dict:
        """Call an n8n webhook endpoint."""
        url = f"{N8N_BASE_URL}/{endpoint}"
        try:
            response = await self.http_client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"n8n webhook error: {e}")
            raise

    async def close(self):
        """Cleanup resources."""
        await self.http_client.aclose()

# ============================================================================
# PYDANTIC AI AGENT
# ============================================================================

# Initialize the conversational agent
task_agent = Agent(
    OLLAMA_MODEL,
    system_prompt='''You are a helpful, intelligent personal assistant for a local AI stack.

Your role:
1. Understand user intent from natural language requests
2. Check if you have ALL necessary information to complete the request
3. Ask clarifying questions if anything is unclear, missing, or ambiguous
4. Make intelligent suggestions to improve requests (better dates, priorities, reminders)
5. ONLY call tools when you have complete, validated information
6. Confirm what you did after completing actions
7. Maintain conversational context - reference previous messages when relevant

Be conversational, friendly, and helpful. It's better to ask than to assume.

When dealing with dates/times:
- Ask for clarification on ambiguous dates (e.g., "next Friday")
- Suggest reasonable defaults when dates are missing
- Always confirm the final date/time with the user

When creating tasks/reminders:
- Tasks should have: title, due date, priority
- Suggest reminders for important tasks
- Ask about details if description would be helpful

You have access to:
- Task management (create, update, search, get details)
- Reminder creation
- Food logging
- Daily summaries
- Note searching

Current date/time: {datetime.now().isoformat()}
''',
    deps_type=AgentDependencies,
)

# ============================================================================
# AGENT TOOLS
# ============================================================================

@task_agent.tool
async def create_task(
    ctx: RunContext[AgentDependencies],
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    priority: str = "medium",
    status: str = "pending",
) -> str:
    """
    Create a new task.

    Args:
        title: Task title (required, clear and specific)
        description: Detailed description of the task
        due_date: When task is due (ISO date format or natural language like "tomorrow", "next Friday")
        priority: Task priority - must be "low", "medium", or "high"
        status: Task status - default "pending"

    Returns:
        Confirmation message with task details
    """
    # Validate priority
    if priority not in ["low", "medium", "high"]:
        return f"Error: Priority must be 'low', 'medium', or 'high', got '{priority}'"

    # Parse due date if provided
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = date_parser.parse(due_date).isoformat()
        except Exception as e:
            return f"Error: Could not parse due date '{due_date}'. Please provide a valid date."

    # Call n8n webhook to create task
    try:
        result = await ctx.deps.call_n8n("create-task", {
            "title": title,
            "description": description,
            "due_date": parsed_due_date,
            "priority": priority,
            "status": status,
            "user_id": ctx.deps.user_id
        })

        task_id = result.get("id", "unknown")
        logger.info(f"Created task: {task_id} - {title}")

        return f"✓ Task created: '{title}' (Priority: {priority}, Due: {due_date or 'not set'})"

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return f"Error creating task: {str(e)}"


@task_agent.tool
async def create_reminder(
    ctx: RunContext[AgentDependencies],
    title: str,
    remind_at: str,
    priority: str = "medium",
    category: str = "General"
) -> str:
    """
    Create a reminder.

    Args:
        title: Reminder title/description
        remind_at: When to be reminded (ISO datetime or natural language)
        priority: Reminder priority - "low", "medium", or "high"
        category: Reminder category (default: General)

    Returns:
        Confirmation message
    """
    # Validate priority
    if priority not in ["low", "medium", "high"]:
        return f"Error: Priority must be 'low', 'medium', or 'high'"

    # Parse reminder time
    try:
        parsed_time = date_parser.parse(remind_at).isoformat()
    except Exception as e:
        return f"Error: Could not parse time '{remind_at}'. Please provide a valid date/time."

    try:
        result = await ctx.deps.call_n8n("create-reminder", {
            "title": title,
            "remind_at": parsed_time,
            "priority": priority,
            "category": category,
            "user_id": ctx.deps.user_id
        })

        logger.info(f"Created reminder: {title} at {remind_at}")
        return f"✓ Reminder created: '{title}' at {remind_at}"

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        return f"Error creating reminder: {str(e)}"


@task_agent.tool
async def search_tasks(
    ctx: RunContext[AgentDependencies],
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_soon: bool = False,
    limit: int = 20
) -> str:
    """
    Search for tasks with optional filters.

    Args:
        status: Filter by status (pending, in_progress, completed)
        priority: Filter by priority (low, medium, high)
        due_soon: Only show tasks due within 7 days
        limit: Maximum number of tasks to return

    Returns:
        Formatted list of tasks
    """
    try:
        # Build query based on filters
        conditions = [f"user_id = '{ctx.deps.user_id}'"]

        if status:
            conditions.append(f"status = '{status}'")
        if priority:
            conditions.append(f"priority = '{priority}'")
        if due_soon:
            conditions.append("due_date <= CURRENT_DATE + INTERVAL '7 days'")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT id, title, description, due_date, priority, status
            FROM tasks
            WHERE {where_clause}
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                due_date NULLS LAST
            LIMIT {limit}
        """

        tasks = await ctx.deps.query(query)

        if not tasks:
            return "No tasks found matching your criteria."

        # Format tasks for display
        result = f"Found {len(tasks)} task(s):\n\n"
        for i, task in enumerate(tasks, 1):
            due = task['due_date'].strftime('%Y-%m-%d') if task['due_date'] else 'No due date'
            result += f"{i}. [{task['priority'].upper()}] {task['title']}\n"
            result += f"   Due: {due} | Status: {task['status']}\n"
            if task['description']:
                result += f"   {task['description']}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"Error searching tasks: {e}")
        return f"Error searching tasks: {str(e)}"


@task_agent.tool
async def get_tasks_today(ctx: RunContext[AgentDependencies]) -> str:
    """
    Get all tasks due today.

    Returns:
        Formatted list of today's tasks
    """
    try:
        query = """
            SELECT id, title, description, priority, status
            FROM tasks
            WHERE user_id = $1
              AND due_date::date = CURRENT_DATE
              AND status != 'completed'
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END
        """

        tasks = await ctx.deps.query(query, ctx.deps.user_id)

        if not tasks:
            return "No tasks due today! 🎉"

        result = f"Tasks due today ({len(tasks)}):\n\n"
        for i, task in enumerate(tasks, 1):
            result += f"{i}. [{task['priority'].upper()}] {task['title']}\n"
            if task['description']:
                result += f"   {task['description']}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"Error getting today's tasks: {e}")
        return f"Error getting tasks: {str(e)}"


@task_agent.tool
async def get_events_today(ctx: RunContext[AgentDependencies]) -> str:
    """
    Get today's calendar events.

    Returns:
        Formatted list of today's events
    """
    try:
        query = """
            SELECT id, title, start_time, end_time, location
            FROM events
            WHERE user_id = $1
              AND start_time::date = CURRENT_DATE
            ORDER BY start_time
        """

        events = await ctx.deps.query(query, ctx.deps.user_id)

        if not events:
            return "No events scheduled for today."

        result = f"Today's events ({len(events)}):\n\n"
        for i, event in enumerate(events, 1):
            start = event['start_time'].strftime('%H:%M')
            end = event['end_time'].strftime('%H:%M') if event['end_time'] else '?'
            location = f" @ {event['location']}" if event['location'] else ""
            result += f"{i}. {start}-{end}: {event['title']}{location}\n"

        return result

    except Exception as e:
        logger.error(f"Error getting today's events: {e}")
        return f"Error getting events: {str(e)}"


@task_agent.tool
async def update_task(
    ctx: RunContext[AgentDependencies],
    task_identifier: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    Update an existing task.

    Args:
        task_identifier: Task ID or title to identify the task
        title: New title
        description: New description
        due_date: New due date
        priority: New priority (low/medium/high)
        status: New status (pending/in_progress/completed)

    Returns:
        Confirmation message
    """
    try:
        # First, find the task
        query = """
            SELECT id, title FROM tasks
            WHERE user_id = $1 AND (id::text = $2 OR title ILIKE $3)
            LIMIT 1
        """
        task = await ctx.deps.query(query, ctx.deps.user_id, task_identifier, f"%{task_identifier}%")

        if not task:
            return f"Could not find task matching '{task_identifier}'"

        task_id = task[0]['id']
        task_title = task[0]['title']

        # Build update query
        updates = []
        params = []
        param_count = 1

        if title:
            updates.append(f"title = ${param_count}")
            params.append(title)
            param_count += 1

        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1

        if due_date:
            parsed_date = date_parser.parse(due_date).isoformat()
            updates.append(f"due_date = ${param_count}")
            params.append(parsed_date)
            param_count += 1

        if priority:
            if priority not in ["low", "medium", "high"]:
                return f"Error: Priority must be low/medium/high"
            updates.append(f"priority = ${param_count}")
            params.append(priority)
            param_count += 1

        if status:
            if status not in ["pending", "in_progress", "completed"]:
                return f"Error: Status must be pending/in_progress/completed"
            updates.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        if not updates:
            return "No updates specified"

        updates.append(f"updated_at = NOW()")
        params.append(task_id)

        update_query = f"""
            UPDATE tasks
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """

        await ctx.deps.execute(update_query, *params)

        logger.info(f"Updated task {task_id}: {updates}")
        return f"✓ Updated task '{task_title}'"

    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return f"Error updating task: {str(e)}"


@task_agent.tool
async def log_food(
    ctx: RunContext[AgentDependencies],
    food_name: str,
    meal_type: str,
    rating: int,
    made_myself: bool = False,
    notes: Optional[str] = None,
    tags: Optional[str] = None
) -> str:
    """
    Log a food/meal entry.

    Args:
        food_name: Name of the food/meal
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        rating: Rating from 1-5
        made_myself: Whether you made it yourself (True) or bought it (False)
        notes: Additional notes about the meal
        tags: Comma-separated tags (e.g., "italian,pasta,vegetarian")

    Returns:
        Confirmation message
    """
    # Validate meal type
    valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
    if meal_type.lower() not in valid_meal_types:
        return f"Error: meal_type must be one of: {', '.join(valid_meal_types)}"

    # Validate rating
    if rating < 1 or rating > 5:
        return "Error: rating must be between 1 and 5"

    try:
        # Call n8n webhook (which handles embedding and Qdrant storage)
        result = await ctx.deps.call_n8n("log-food", {
            "food_name": food_name,
            "meal_type": meal_type.lower(),
            "rating": rating,
            "made_myself": made_myself,
            "notes": notes or "",
            "tags": tags or "",
            "user_id": ctx.deps.user_id
        })

        logger.info(f"Logged food: {food_name} ({meal_type}, {rating}/5)")

        source = "homemade" if made_myself else "bought"
        return f"✓ Logged: {food_name} ({meal_type}, {rating}/5, {source})"

    except Exception as e:
        logger.error(f"Error logging food: {e}")
        return f"Error logging food: {str(e)}"

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    global db_pool

    # Startup
    logger.info("Starting Pydantic AI Agent Service...")
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("Database pool created")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

app = FastAPI(
    title="Pydantic AI Agent Service",
    description="Intelligent conversational agent for AI Stack",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# API MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    conversation_id: str = Field(default="default", description="Conversation ID for context")
    user_id: str = Field(default=DEFAULT_USER_ID, description="User ID")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Agent response")
    conversation_id: str = Field(..., description="Conversation ID")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "pydantic-ai-agent",
        "status": "running",
        "model": OLLAMA_MODEL,
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    db_status = "connected" if db_pool else "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "model": OLLAMA_MODEL,
        "n8n_base_url": N8N_BASE_URL,
        "conversations_active": len(conversation_store)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - handles all user requests through the agent.

    The agent will:
    1. Understand the user's intent
    2. Ask clarifying questions if needed
    3. Validate information before taking action
    4. Use appropriate tools to complete the request
    5. Maintain conversation context
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Get or initialize conversation history
        conv_id = request.conversation_id
        if conv_id not in conversation_store:
            conversation_store[conv_id] = []
            logger.info(f"Started new conversation: {conv_id}")

        # Create dependencies
        deps = AgentDependencies(db_pool, request.user_id)

        # Run agent with conversation context
        result = await task_agent.run(
            request.message,
            message_history=conversation_store[conv_id],
            deps=deps
        )

        # Update conversation history
        conversation_store[conv_id] = result.new_messages()

        # Cleanup
        await deps.close()

        logger.info(f"[{conv_id}] User: {request.message[:50]}...")
        logger.info(f"[{conv_id}] Agent: {result.data[:50]}...")

        return ChatResponse(
            response=result.data,
            conversation_id=conv_id
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history for a specific conversation ID."""
    if conversation_id in conversation_store:
        del conversation_store[conversation_id]
        logger.info(f"Cleared conversation: {conversation_id}")
        return {"status": "cleared", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/conversations")
async def list_conversations():
    """List all active conversations."""
    return {
        "conversations": list(conversation_store.keys()),
        "count": len(conversation_store)
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
