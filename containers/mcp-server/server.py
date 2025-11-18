#!/usr/bin/env python3
"""
AI Stack - MCP Server
Model Context Protocol server with 17 tools for database and memory access.

Tools:
  Database (12):
    - get_reminders_today, get_reminders_upcoming, search_reminders
    - get_events_today, get_events_upcoming
    - get_tasks_by_status, get_tasks_due_soon
    - search_notes, get_recent_notes
    - get_reminder_categories, get_day_summary, get_week_summary

  Memory (5):
    - search_memories, get_recent_memories, get_conversation_context
    - get_memory_by_id, get_related_memories
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

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

QDRANT_CONFIG = {
    "host": os.getenv("QDRANT_HOST", "qdrant-ai-stack"),
    "port": int(os.getenv("QDRANT_PORT", "6333")),
}

OLLAMA_CONFIG = {
    "host": os.getenv("OLLAMA_HOST", "ollama-ai-stack"),
    "port": int(os.getenv("OLLAMA_PORT", "11434")),
    "base_url": f"http://{os.getenv('OLLAMA_HOST', 'ollama-ai-stack')}:{os.getenv('OLLAMA_PORT', '11434')}",
}

DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")

# ============================================================================
# GLOBAL CONNECTIONS
# ============================================================================

db_pool: Optional[asyncpg.Pool] = None
qdrant_client: Optional[QdrantClient] = None
http_client: Optional[httpx.AsyncClient] = None

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
    return db_pool

def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(
            host=QDRANT_CONFIG["host"],
            port=QDRANT_CONFIG["port"],
        )
    return qdrant_client

async def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for Ollama."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
    return http_client

async def cleanup():
    """Clean up connections."""
    global db_pool, qdrant_client, http_client
    if db_pool:
        await db_pool.close()
    if http_client:
        await http_client.aclose()

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

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Ollama."""
    client = await get_http_client()
    try:
        response = await client.post(
            f"{OLLAMA_CONFIG['base_url']}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except Exception as e:
        print(f"Error generating embedding: {e}", file=sys.stderr)
        return []

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
# MEMORY TOOLS (5)
# ============================================================================

async def search_memories(query: str, sector: Optional[str] = None, limit: int = 10) -> str:
    """Search memories using vector similarity."""
    # Generate embedding for query
    query_embedding = await generate_embedding(query)
    if not query_embedding:
        return "Error: Could not generate embedding for query."

    # Search Qdrant
    qdrant = get_qdrant_client()
    search_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=DEFAULT_USER_ID))
        ]
    )

    if sector:
        search_filter.must.append(
            FieldCondition(key="sector", match=MatchValue(value=sector))
        )

    try:
        search_results = qdrant.search(
            collection_name="memories",
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=0.5,
        )
    except Exception as e:
        return f"Error searching Qdrant: {e}"

    if not search_results:
        return f"No memories found matching '{query}'" + (f" in sector '{sector}'" if sector else "")

    # Get full memory details from PostgreSQL
    memory_ids = [hit.id.split("_")[0] for hit in search_results]  # Extract memory_id from qdrant_point_id

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT m.id, m.content, m.salience_score, m.created_at, m.source,
                   ARRAY_AGG(ms.sector) as sectors
            FROM memories m
            JOIN memory_sectors ms ON m.id = ms.memory_id
            WHERE m.id = ANY($1::uuid[])
            GROUP BY m.id, m.content, m.salience_score, m.created_at, m.source
            ORDER BY m.salience_score DESC
        """, memory_ids)

    result = [f"🧠 Memories matching '{query}' ({len(rows)})\n"]
    for i, row in enumerate(rows, 1):
        sectors_str = ", ".join(row['sectors'])
        result.append(
            f"\n{i}. [{row['source']}] Salience: {row['salience_score']:.2f}\n"
            f"   Sectors: {sectors_str}\n"
            f"   {row['content'][:200]}{'...' if len(row['content']) > 200 else ''}\n"
            f"   Created: {format_datetime(row['created_at'])}\n"
        )
    return "".join(result)

async def get_recent_memories(limit: int = 10, sector: Optional[str] = None) -> str:
    """Get recently created memories."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if sector:
            rows = await conn.fetch("""
                SELECT m.id, m.content, m.salience_score, m.created_at, m.source,
                       ARRAY_AGG(ms.sector) as sectors
                FROM memories m
                JOIN memory_sectors ms ON m.id = ms.memory_id
                WHERE m.user_id = $1 AND m.is_archived = FALSE
                  AND EXISTS (SELECT 1 FROM memory_sectors ms2 WHERE ms2.memory_id = m.id AND ms2.sector = $3)
                GROUP BY m.id, m.content, m.salience_score, m.created_at, m.source
                ORDER BY m.created_at DESC
                LIMIT $2
            """, UUID(DEFAULT_USER_ID), limit, sector)
        else:
            rows = await conn.fetch("""
                SELECT m.id, m.content, m.salience_score, m.created_at, m.source,
                       ARRAY_AGG(ms.sector) as sectors
                FROM memories m
                JOIN memory_sectors ms ON m.id = ms.memory_id
                WHERE m.user_id = $1 AND m.is_archived = FALSE
                GROUP BY m.id, m.content, m.salience_score, m.created_at, m.source
                ORDER BY m.created_at DESC
                LIMIT $2
            """, UUID(DEFAULT_USER_ID), limit)

        if not rows:
            return "No recent memories found."

        sector_filter = f" ({sector})" if sector else ""
        result = [f"🧠 Recent Memories{sector_filter} ({len(rows)})\n"]
        for i, row in enumerate(rows, 1):
            sectors_str = ", ".join(row['sectors'])
            result.append(
                f"\n{i}. [{row['source']}] Salience: {row['salience_score']:.2f}\n"
                f"   Sectors: {sectors_str}\n"
                f"   {row['content'][:150]}{'...' if len(row['content']) > 150 else ''}\n"
                f"   {format_datetime(row['created_at'])}\n"
            )
        return "".join(result)

async def get_conversation_context(conversation_id: str) -> str:
    """Get all memories from a specific conversation."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get conversation details
        conv = await conn.fetchrow("""
            SELECT title, source, started_at, message_count
            FROM conversations
            WHERE id = $1
        """, UUID(conversation_id))

        if not conv:
            return f"Conversation not found: {conversation_id}"

        # Get memories
        rows = await conn.fetch("""
            SELECT m.content, m.created_at, ARRAY_AGG(ms.sector) as sectors
            FROM memories m
            JOIN memory_sectors ms ON m.id = ms.memory_id
            WHERE m.conversation_id = $1
              AND m.is_archived = FALSE
            GROUP BY m.id, m.content, m.created_at
            ORDER BY m.created_at ASC
        """, UUID(conversation_id))

        if not rows:
            return f"No memories found for conversation: {conv['title']}"

        result = [
            f"💬 Conversation: {conv['title']}\n",
            f"Source: {conv['source']} • Started: {format_datetime(conv['started_at'])}\n",
            f"Messages: {conv['message_count']} • Memories: {len(rows)}\n\n",
        ]

        for i, row in enumerate(rows, 1):
            sectors_str = ", ".join(row['sectors'])
            result.append(
                f"{i}. [{sectors_str}]\n"
                f"   {row['content'][:200]}{'...' if len(row['content']) > 200 else ''}\n\n"
            )
        return "".join(result)

async def get_memory_by_id(memory_id: str) -> str:
    """Get full details of a specific memory."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT m.id, m.content, m.content_summary, m.memory_type, m.source,
                   m.salience_score, m.access_count, m.last_accessed_at,
                   m.created_at, m.conversation_id,
                   ARRAY_AGG(ms.sector) as sectors,
                   c.title as conversation_title
            FROM memories m
            JOIN memory_sectors ms ON m.id = ms.memory_id
            LEFT JOIN conversations c ON m.conversation_id = c.id
            WHERE m.id = $1
            GROUP BY m.id, m.content, m.content_summary, m.memory_type, m.source,
                     m.salience_score, m.access_count, m.last_accessed_at,
                     m.created_at, m.conversation_id, c.title
        """, UUID(memory_id))

        if not row:
            return f"Memory not found: {memory_id}"

        # Update access count
        await conn.execute("""
            UPDATE memories
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
            WHERE id = $1
        """, UUID(memory_id))

        sectors_str = ", ".join(row['sectors'])
        result = [
            f"🧠 Memory Details\n\n",
            f"ID: {row['id']}\n",
            f"Type: {row['memory_type']} • Source: {row['source']}\n",
            f"Sectors: {sectors_str}\n",
            f"Salience: {row['salience_score']:.2f} • Access count: {row['access_count']}\n",
            f"Created: {format_datetime(row['created_at'])}\n",
        ]

        if row['conversation_title']:
            result.append(f"Conversation: {row['conversation_title']}\n")

        result.append(f"\nContent:\n{row['content']}\n")

        if row['content_summary']:
            result.append(f"\nSummary:\n{row['content_summary']}\n")

        return "".join(result)

async def get_related_memories(memory_id: str, max_depth: int = 2) -> str:
    """Get memories related to a specific memory via links."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM get_related_memories($1, $2)
        """, UUID(memory_id), max_depth)

        if not rows:
            return f"No related memories found for: {memory_id}"

        result = [f"🔗 Related Memories ({len(rows)})\n"]
        current_depth = 0
        for row in rows:
            if row['depth'] != current_depth:
                current_depth = row['depth']
                result.append(f"\nDepth {current_depth}:\n")

            result.append(
                f"  • [{row['link_type']}] Strength: {row['link_strength']:.2f}\n"
                f"    {row['content'][:150]}{'...' if len(row['content']) > 150 else ''}\n"
            )
        return "".join(result)

# ============================================================================
# MCP SERVER SETUP
# ============================================================================

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

    # Memory tools
    Tool(
        name="search_memories",
        description="Search memories using semantic similarity",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "sector": {"type": "string", "description": "Optional sector filter (semantic, episodic, procedural, emotional, reflective)"},
                "limit": {"type": "integer", "description": "Number of results", "default": 10},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_recent_memories",
        description="Get recently created memories",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of memories", "default": 10},
                "sector": {"type": "string", "description": "Optional sector filter"},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_conversation_context",
        description="Get all memories from a specific conversation",
        inputSchema={
            "type": "object",
            "properties": {"conversation_id": {"type": "string", "description": "Conversation UUID"}},
            "required": ["conversation_id"],
        },
    ),
    Tool(
        name="get_memory_by_id",
        description="Get full details of a specific memory",
        inputSchema={
            "type": "object",
            "properties": {"memory_id": {"type": "string", "description": "Memory UUID"}},
            "required": ["memory_id"],
        },
    ),
    Tool(
        name="get_related_memories",
        description="Get memories related via links",
        inputSchema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory UUID"},
                "max_depth": {"type": "integer", "description": "Maximum link depth", "default": 2},
            },
            "required": ["memory_id"],
        },
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
            "search_memories": lambda: search_memories(
                arguments["query"],
                arguments.get("sector"),
                arguments.get("limit", 10)
            ),
            "get_recent_memories": lambda: get_recent_memories(
                arguments.get("limit", 10),
                arguments.get("sector")
            ),
            "get_conversation_context": lambda: get_conversation_context(arguments["conversation_id"]),
            "get_memory_by_id": lambda: get_memory_by_id(arguments["memory_id"]),
            "get_related_memories": lambda: get_related_memories(
                arguments["memory_id"],
                arguments.get("max_depth", 2)
            ),
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
    print(f"Qdrant: {QDRANT_CONFIG['host']}:{QDRANT_CONFIG['port']}", file=sys.stderr)
    print(f"Ollama: {OLLAMA_CONFIG['base_url']}", file=sys.stderr)
    print("Ready to accept connections.", file=sys.stderr)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
