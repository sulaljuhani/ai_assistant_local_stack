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
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres-ai-stack"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "aistack"),
    "user": os.getenv("POSTGRES_USER", "aistack_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
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
    """Get or create database connection pool."""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
    return db_pool

async def cleanup():
    """Clean up connections."""
    global db_pool
    if db_pool:
        await db_pool.close()

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
    """Execute a tool and return results."""
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
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        result = await tool_map[name]()
        return [TextContent(type="text", text=result)]

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    print("Starting AI Stack MCP Server...", file=sys.stderr)
    print(f"PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}", file=sys.stderr)
    print("Note: Memory tools now provided by OpenMemory container", file=sys.stderr)
    print("Ready to accept connections.", file=sys.stderr)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
