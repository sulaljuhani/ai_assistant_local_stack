#!/usr/bin/env python3
"""
AI Stack - MCP Server
Model Context Protocol server with 12 tools for database access.

Memory functionality provided by OpenMemory (separate container with built-in MCP support).

Tools:
  Database (12):
    - get_reminders_today, get_reminders_upcoming, search_reminders
    - get_events_today, get_events_upcoming
    - get_tasks_by_status, get_tasks_due_soon
    - search_notes, get_recent_notes
    - get_reminder_categories, get_day_summary, get_week_summary
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields
        if hasattr(record, "tool_name"):
            log_data["tool_name"] = record.tool_name
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger("mcp_server")

# Use JSON formatter for structured logs
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())

logger.info("MCP Server logging initialized")

# ============================================================================
# CONFIGURATION
# ============================================================================

# FIX: Require POSTGRES_PASSWORD to be set, no default password
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
if not POSTGRES_PASSWORD:
    logger.error("POSTGRES_PASSWORD environment variable is not set!")
    raise ValueError(
        "POSTGRES_PASSWORD is required. "
        "Set it in your environment or .env file. "
        "Do not use default passwords in production."
    )

# Validate password strength (basic check)
if len(POSTGRES_PASSWORD) < 12:
    logger.warning(
        f"POSTGRES_PASSWORD is weak (length: {len(POSTGRES_PASSWORD)}). "
        "Use at least 12 characters for production."
    )

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres-ai-stack"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "aistack"),
    "user": os.getenv("POSTGRES_USER", "aistack_user"),
    "password": POSTGRES_PASSWORD,  # FIX: Use validated password
}

DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")

# Note: Memory functionality now provided by OpenMemory container
# OpenMemory has built-in MCP support - no custom memory tools needed here

# ============================================================================
# GLOBAL CONNECTIONS
# ============================================================================

db_pool: Optional[asyncpg.Pool] = None

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool with retry logic."""
    global db_pool

    if db_pool is not None:
        return db_pool

    # Retry logic for database connection
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})")
            db_pool = await asyncpg.create_pool(
                **DB_CONFIG,
                min_size=int(os.getenv("POSTGRES_MIN_POOL_SIZE", "2")),
                max_size=int(os.getenv("POSTGRES_MAX_POOL_SIZE", "10")),
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
            return db_pool

        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("All database connection attempts failed")
                raise ConnectionError(f"Failed to connect to database after {max_retries} attempts: {str(e)}")

    return db_pool

async def cleanup():
    """Clean up connections."""
    global db_pool
    if db_pool:
        logger.info("Closing database connection pool")
        try:
            await db_pool.close()
            logger.info("Database connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing database pool: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_date(dt: Optional[datetime]) -> str:
    """Format date for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d")

# ============================================================================
# DATABASE TOOLS (12)
# ============================================================================

async def get_reminders_today() -> str:
    """Get all reminders scheduled for today."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, remind_at, priority, status, description
            FROM reminders
            WHERE user_id = $1
              AND DATE(remind_at) = CURRENT_DATE
              AND status = 'pending'
            ORDER BY remind_at ASC
        """, UUID(DEFAULT_USER_ID))

        if not rows:
            return "No reminders scheduled for today."

        result = [f"📅 Today's Reminders ({len(rows)})\n"]
        for row in rows:
            priority_emoji = "🔴" if row['priority'] >= 2 else "🟡" if row['priority'] == 1 else "⚪"
            result.append(
                f"{priority_emoji} {format_datetime(row['remind_at'])} - {row['title']}\n"
                f"   {row['description'] or 'No description'}\n"
            )
        return "\n".join(result)

async def get_reminders_upcoming(days: int = 7) -> str:
    """Get reminders in the next N days."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, remind_at, priority, category_id
            FROM reminders
            WHERE user_id = $1
              AND status = 'pending'
              AND remind_at BETWEEN NOW() AND NOW() + INTERVAL '1 day' * $2
            ORDER BY remind_at ASC
        """, UUID(DEFAULT_USER_ID), days)

        if not rows:
            return f"No reminders in the next {days} days."

        result = [f"📆 Upcoming Reminders (next {days} days, {len(rows)} total)\n"]
        for row in rows:
            result.append(f"• {format_datetime(row['remind_at'])} - {row['title']}\n")
        return "\n".join(result)

async def search_reminders(query: str) -> str:
    """Search reminders by text."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, remind_at, status, description
            FROM reminders
            WHERE user_id = $1
              AND (
                  title ILIKE $2
                  OR description ILIKE $2
                  OR to_tsvector('english', title || ' ' || COALESCE(description, '')) @@ plainto_tsquery('english', $3)
              )
            ORDER BY remind_at DESC
            LIMIT 20
        """, UUID(DEFAULT_USER_ID), f"%{query}%", query)

        if not rows:
            return f"No reminders found matching '{query}'."

        result = [f"🔍 Reminders matching '{query}' ({len(rows)})\n"]
        for row in rows:
            status_emoji = "✅" if row['status'] == 'completed' else "⏰" if row['status'] == 'pending' else "❌"
            result.append(
                f"{status_emoji} {row['title']} - {format_datetime(row['remind_at'])}\n"
            )
        return "\n".join(result)

async def get_events_today() -> str:
    """Get all events scheduled for today."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, start_time, end_time, location, description
            FROM events
            WHERE user_id = $1
              AND DATE(start_time) = CURRENT_DATE
              AND status != 'cancelled'
            ORDER BY start_time ASC
        """, UUID(DEFAULT_USER_ID))

        if not rows:
            return "No events scheduled for today."

        result = [f"📅 Today's Events ({len(rows)})\n"]
        for row in rows:
            duration = (row['end_time'] - row['start_time']).total_seconds() / 3600
            result.append(
                f"• {row['start_time'].strftime('%H:%M')} - {row['end_time'].strftime('%H:%M')} "
                f"({duration:.1f}h) - {row['title']}\n"
                f"  📍 {row['location'] or 'No location'}\n"
            )
        return "\n".join(result)

async def get_events_upcoming(days: int = 7) -> str:
    """Get events in the next N days."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, start_time, end_time, location
            FROM events
            WHERE user_id = $1
              AND start_time BETWEEN NOW() AND NOW() + INTERVAL '1 day' * $2
              AND status != 'cancelled'
            ORDER BY start_time ASC
        """, UUID(DEFAULT_USER_ID), days)

        if not rows:
            return f"No events in the next {days} days."

        result = [f"📆 Upcoming Events (next {days} days, {len(rows)} total)\n"]
        current_date = None
        for row in rows:
            event_date = row['start_time'].date()
            if event_date != current_date:
                current_date = event_date
                result.append(f"\n{event_date.strftime('%A, %B %d, %Y')}:\n")
            result.append(
                f"  • {row['start_time'].strftime('%H:%M')} - {row['title']}"
                f" @ {row['location'] or 'TBD'}\n"
            )
        return "\n".join(result)

async def get_tasks_by_status(status: str = "todo") -> str:
    """Get tasks by status (todo, in_progress, done, cancelled)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, due_date, priority, description
            FROM tasks
            WHERE user_id = $1
              AND status = $2
            ORDER BY priority DESC, due_date ASC NULLS LAST
            LIMIT 50
        """, UUID(DEFAULT_USER_ID), status)

        if not rows:
            return f"No tasks with status '{status}'."

        status_emoji = {
            "todo": "📝",
            "in_progress": "🔄",
            "waiting": "⏸️",
            "done": "✅",
            "cancelled": "❌",
        }

        result = [f"{status_emoji.get(status, '📋')} Tasks: {status.upper()} ({len(rows)})\n"]
        for row in rows:
            priority_emoji = "🔴" if row['priority'] >= 3 else "🟡" if row['priority'] >= 2 else "⚪"
            due = f" (Due: {format_date(row['due_date'])})" if row['due_date'] else ""
            result.append(f"{priority_emoji} {row['title']}{due}\n")
        return "\n".join(result)

async def get_tasks_due_soon(days: int = 7) -> str:
    """Get tasks due in the next N days."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, due_date, priority, status
            FROM tasks
            WHERE user_id = $1
              AND status NOT IN ('done', 'cancelled')
              AND due_date IS NOT NULL
              AND due_date BETWEEN NOW() AND NOW() + INTERVAL '1 day' * $2
            ORDER BY due_date ASC, priority DESC
        """, UUID(DEFAULT_USER_ID), days)

        if not rows:
            return f"No tasks due in the next {days} days."

        result = [f"⏰ Tasks Due Soon (next {days} days, {len(rows)} total)\n"]
        for row in rows:
            days_until = (row['due_date'] - datetime.now()).days
            urgency = "🔴 URGENT" if days_until <= 1 else "🟡 Soon" if days_until <= 3 else "⚪ Upcoming"
            result.append(
                f"{urgency} - {row['title']}\n"
                f"  Due: {format_date(row['due_date'])} ({days_until} days)\n"
            )
        return "\n".join(result)

async def search_notes(query: str) -> str:
    """Search notes by content."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, folder, updated_at,
                   ts_rank(to_tsvector('english', title || ' ' || content), plainto_tsquery('english', $2)) as rank
            FROM notes
            WHERE user_id = $1
              AND to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC, updated_at DESC
            LIMIT 20
        """, UUID(DEFAULT_USER_ID), query)

        if not rows:
            return f"No notes found matching '{query}'."

        result = [f"🔍 Notes matching '{query}' ({len(rows)})\n"]
        for row in rows:
            result.append(
                f"📝 {row['title']}\n"
                f"   📂 {row['folder'] or 'Root'} • Updated: {format_datetime(row['updated_at'])}\n"
            )
        return "\n".join(result)

async def get_recent_notes(limit: int = 10) -> str:
    """Get recently modified notes."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, folder, updated_at, file_path
            FROM notes
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2
        """, UUID(DEFAULT_USER_ID), limit)

        if not rows:
            return "No notes found."

        result = [f"📚 Recent Notes ({len(rows)})\n"]
        for row in rows:
            result.append(
                f"📝 {row['title']}\n"
                f"   📂 {row['file_path'] or row['folder'] or 'Root'} • {format_datetime(row['updated_at'])}\n"
            )
        return "\n".join(result)

async def get_reminder_categories() -> str:
    """Get all reminder categories."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.name, c.icon, c.color, COUNT(r.id) as reminder_count
            FROM categories c
            LEFT JOIN reminders r ON c.id = r.category_id AND r.status = 'pending'
            WHERE c.user_id = $1
            GROUP BY c.id, c.name, c.icon, c.color
            ORDER BY c.name
        """, UUID(DEFAULT_USER_ID))

        if not rows:
            return "No categories found."

        result = [f"📁 Categories ({len(rows)})\n"]
        for row in rows:
            result.append(
                f"{row['icon']} {row['name']} ({row['reminder_count']} pending reminders)\n"
            )
        return "\n".join(result)

async def get_day_summary() -> str:
    """Get summary of today's activities."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        summary = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM reminders WHERE user_id = $1 AND DATE(remind_at) = CURRENT_DATE AND status = 'pending') as reminders_today,
                (SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND DATE(due_date) = CURRENT_DATE AND status NOT IN ('done', 'cancelled')) as tasks_due,
                (SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = 'done' AND DATE(completed_at) = CURRENT_DATE) as tasks_completed,
                (SELECT COUNT(*) FROM events WHERE user_id = $1 AND DATE(start_time) = CURRENT_DATE AND status != 'cancelled') as events_today
        """, UUID(DEFAULT_USER_ID))

        result = [
            f"📊 Today's Summary - {datetime.now().strftime('%A, %B %d, %Y')}\n",
            f"\n⏰ Reminders: {summary['reminders_today']}",
            f"\n📝 Tasks Due: {summary['tasks_due']}",
            f"\n✅ Tasks Completed: {summary['tasks_completed']}",
            f"\n📅 Events: {summary['events_today']}\n",
        ]
        return "".join(result)

async def get_week_summary() -> str:
    """Get summary of this week's activities."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        summary = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM reminders WHERE user_id = $1 AND remind_at BETWEEN date_trunc('week', CURRENT_DATE) AND date_trunc('week', CURRENT_DATE) + INTERVAL '7 days' AND status = 'pending') as reminders_week,
                (SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND due_date BETWEEN date_trunc('week', CURRENT_DATE) AND date_trunc('week', CURRENT_DATE) + INTERVAL '7 days' AND status NOT IN ('done', 'cancelled')) as tasks_due_week,
                (SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = 'done' AND completed_at >= date_trunc('week', CURRENT_DATE)) as tasks_completed_week,
                (SELECT COUNT(*) FROM events WHERE user_id = $1 AND start_time BETWEEN date_trunc('week', CURRENT_DATE) AND date_trunc('week', CURRENT_DATE) + INTERVAL '7 days' AND status != 'cancelled') as events_week
        """, UUID(DEFAULT_USER_ID))

        result = [
            f"📊 This Week's Summary\n",
            f"\n⏰ Reminders: {summary['reminders_week']}",
            f"\n📝 Tasks Due: {summary['tasks_due_week']}",
            f"\n✅ Tasks Completed: {summary['tasks_completed_week']}",
            f"\n📅 Events: {summary['events_week']}\n",
        ]
        return "".join(result)

# ============================================================================
# MCP SERVER SETUP
# ============================================================================

# Note: Memory tools removed - use OpenMemory container's built-in MCP support
# This MCP server now only provides database tools (reminders, tasks, events, notes)

# Create MCP server
app = Server("ai-stack-mcp-server")

# Define all tools
TOOLS = [
    # Database tools
    Tool(
        name="get_reminders_today",
        description="Get all reminders scheduled for today",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_reminders_upcoming",
        description="Get reminders in the next N days (default 7)",
        inputSchema={
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Number of days to look ahead", "default": 7}},
            "required": [],
        },
    ),
    Tool(
        name="search_reminders",
        description="Search reminders by text query",
        inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    ),
    Tool(
        name="get_events_today",
        description="Get all events scheduled for today",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_events_upcoming",
        description="Get events in the next N days (default 7)",
        inputSchema={
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Number of days to look ahead", "default": 7}},
            "required": [],
        },
    ),
    Tool(
        name="get_tasks_by_status",
        description="Get tasks by status (todo, in_progress, waiting, done, cancelled)",
        inputSchema={
            "type": "object",
            "properties": {"status": {"type": "string", "description": "Task status", "default": "todo"}},
            "required": [],
        },
    ),
    Tool(
        name="get_tasks_due_soon",
        description="Get tasks due in the next N days (default 7)",
        inputSchema={
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Number of days to look ahead", "default": 7}},
            "required": [],
        },
    ),
    Tool(
        name="search_notes",
        description="Search notes by text query",
        inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    ),
    Tool(
        name="get_recent_notes",
        description="Get recently modified notes",
        inputSchema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Number of notes to return", "default": 10}},
            "required": [],
        },
    ),
    Tool(
        name="get_reminder_categories",
        description="Get all reminder categories with counts",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_day_summary",
        description="Get summary of today's activities",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_week_summary",
        description="Get summary of this week's activities",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool and return results with comprehensive error handling."""
    start_time = datetime.now()

    # Log tool invocation
    log_extra = {"tool_name": name, "user_id": DEFAULT_USER_ID}
    logger.info(f"Tool invoked: {name}", extra=log_extra)

    try:
        # Map tool names to functions
        tool_map = {
            "get_reminders_today": lambda: get_reminders_today(),
            "get_reminders_upcoming": lambda: get_reminders_upcoming(arguments.get("days", 7)),
            "search_reminders": lambda: search_reminders(arguments["query"]),
            "get_events_today": lambda: get_events_today(),
            "get_events_upcoming": lambda: get_events_upcoming(arguments.get("days", 7)),
            "get_tasks_by_status": lambda: get_tasks_by_status(arguments.get("status", "todo")),
            "get_tasks_due_soon": lambda: get_tasks_due_soon(arguments.get("days", 7)),
            "search_notes": lambda: search_notes(arguments["query"]),
            "get_recent_notes": lambda: get_recent_notes(arguments.get("limit", 10)),
            "get_reminder_categories": lambda: get_reminder_categories(),
            "get_day_summary": lambda: get_day_summary(),
            "get_week_summary": lambda: get_week_summary(),
        }

        if name not in tool_map:
            error_msg = f"Unknown tool: {name}. Available tools: {', '.join(tool_map.keys())}"
            logger.warning(error_msg, extra=log_extra)
            return [TextContent(type="text", text=error_msg)]

        # Execute tool
        result = await tool_map[name]()

        # Log success with duration
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        log_extra["duration_ms"] = duration_ms
        logger.info(f"Tool {name} completed successfully in {duration_ms}ms", extra=log_extra)

        return [TextContent(type="text", text=result)]

    except KeyError as e:
        # Missing required argument
        error_msg = f"Missing required argument for {name}: {str(e)}"
        logger.error(error_msg, extra=log_extra, exc_info=True)
        return [TextContent(type="text", text=f"❌ {error_msg}")]

    except asyncpg.PostgresError as e:
        # Database error
        error_msg = f"Database error in {name}: {str(e)}"
        logger.error(error_msg, extra=log_extra, exc_info=True)
        return [TextContent(type="text", text=f"❌ Database error: Unable to retrieve data. The database may be temporarily unavailable. Please try again in a moment.")]

    except ConnectionError as e:
        # Connection error
        error_msg = f"Connection error in {name}: {str(e)}"
        logger.error(error_msg, extra=log_extra, exc_info=True)
        return [TextContent(type="text", text=f"❌ Connection error: Cannot connect to database. Please check that PostgreSQL is running.")]

    except ValueError as e:
        # Invalid input
        error_msg = f"Invalid input for {name}: {str(e)}"
        logger.error(error_msg, extra=log_extra, exc_info=True)
        return [TextContent(type="text", text=f"❌ Invalid input: {str(e)}")]

    except Exception as e:
        # Unexpected error
        error_msg = f"Unexpected error in {name}: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, extra=log_extra, exc_info=True)
        return [TextContent(type="text", text=f"❌ An unexpected error occurred. The error has been logged. Please contact support if this persists.")]

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point with comprehensive logging."""
    logger.info("="*60)
    logger.info("Starting AI Stack MCP Server")
    logger.info("="*60)
    logger.info(f"PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    logger.info(f"User ID: {DEFAULT_USER_ID}")
    logger.info(f"Pool size: {os.getenv('POSTGRES_MIN_POOL_SIZE', '2')}-{os.getenv('POSTGRES_MAX_POOL_SIZE', '10')} connections")
    logger.info("Note: Memory tools provided by OpenMemory container")
    logger.info(f"Available tools: {len(TOOLS)}")
    logger.info("="*60)
    logger.info("Ready to accept connections")

    try:
        # Test database connection on startup
        logger.info("Testing database connection...")
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"Database connected: PostgreSQL {version.split()[1]}")

        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server started successfully")
            await app.run(read_stream, write_stream, app.create_initialization_options())

    except KeyboardInterrupt:
        logger.info("Received shutdown signal (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Fatal error in main(): {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down MCP server...")
        await cleanup()
        logger.info("MCP server shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
