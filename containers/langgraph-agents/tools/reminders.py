"""
Reminder tools for creation, search, and updates.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dateutil import parser as date_parser
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger
from .database import normalize_due_date, validate_limit

logger = get_logger(__name__)

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
VALID_STATUSES = {"pending", "fired", "completed", "snoozed", "cancelled"}
PRIORITY_MAP = {
    "low": 0,
    "medium": 1,
    "normal": 1,
    "high": 2,
    "urgent": 3,
}


def _normalize_priority(priority: Optional[str | int]) -> int:
    """Convert priority input into a clamped integer (0-3)."""
    if priority is None:
        return 1

    try:
        if isinstance(priority, str):
            prio_lower = priority.lower()
            if prio_lower in PRIORITY_MAP:
                return PRIORITY_MAP[prio_lower]
            if priority.isdigit():
                return max(0, min(3, int(priority)))
        return max(0, min(3, int(priority)))
    except Exception:
        return 1


def _normalize_remind_at(remind_at: Optional[str | datetime]) -> Optional[datetime]:
    """Parse remind_at input into a timezone-naive datetime."""
    if remind_at is None:
        return None

    if isinstance(remind_at, datetime):
        return remind_at.replace(tzinfo=None)

    parsed = normalize_due_date(remind_at)
    if parsed:
        return parsed.replace(tzinfo=None)

    try:
        parsed = date_parser.parse(str(remind_at), fuzzy=True)
        return parsed.replace(tzinfo=None)
    except Exception as e:
        logger.warning(f"Could not parse remind_at '{remind_at}': {e}")
        return None


def _normalize_recurrence(recurrence: Optional[str]) -> Optional[str]:
    """Normalize recurrence text."""
    if not recurrence:
        return None
    recurrence_lower = recurrence.lower()
    if recurrence_lower in {"none", "no", "off"}:
        return None
    return recurrence_lower


@tool
async def search_reminders(
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str | int] = None,
    category: Optional[str] = None,
    include_completed: bool = True,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search reminders with optional filters.

    Args:
        user_id: User identifier
        status: Reminder status filter (pending, fired, completed, snoozed, cancelled)
        priority: Priority filter (0-3 or low/medium/high/urgent)
        category: Category name filter
        include_completed: Include completed reminders when no status is provided
        limit: Maximum results (max 100)
    """
    validate_limit(limit)

    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    priority_int = _normalize_priority(priority) if priority is not None else None

    where_clauses = ["r.user_id = $1"]
    params = [user_id]
    param_count = 1

    if status:
        param_count += 1
        params.append(status)
        where_clauses.append(f"r.status = ${param_count}")
    elif not include_completed:
        where_clauses.append("r.status <> 'completed'")

    if priority_int is not None:
        param_count += 1
        params.append(priority_int)
        where_clauses.append(f"r.priority = ${param_count}")

    if category:
        param_count += 1
        params.append(category)
        where_clauses.append(f"c.name = ${param_count}")

    param_count += 1
    params.append(limit)

    query = f"""
        SELECT
            r.id, r.title, r.description, r.remind_at, r.priority,
            r.recurrence_rule, r.status, r.completed_at,
            r.created_at, r.updated_at,
            c.name as category
        FROM reminders r
        LEFT JOIN categories c ON r.category_id = c.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY r.remind_at ASC
        LIMIT ${param_count}
    """

    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            logger.info(f"Found {len(rows)} reminders")
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error searching reminders: {e}", exc_info=True)
        raise


@tool
async def create_reminder(
    title: str,
    remind_at: str,
    user_id: str = DEFAULT_USER_ID,
    description: Optional[str] = None,
    priority: Optional[str | int] = 1,
    category: Optional[str] = None,
    recurrence: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new reminder.

    Args:
        title: Reminder title
        remind_at: When to fire (natural language or ISO datetime)
        user_id: User identifier
        description: Optional description
        priority: Priority (0-3 or low/medium/high/urgent)
        category: Category name (created if missing)
        recurrence: Recurrence rule (daily/weekly/monthly/yearly)
        tags: Optional list of tags
    """
    if not title or not title.strip():
        raise ValueError("title is required")

    parsed_remind_at = _normalize_remind_at(remind_at)
    if not parsed_remind_at:
        raise ValueError("remind_at is required and must be a valid date/time")

    priority_int = _normalize_priority(priority)
    recurrence_rule = _normalize_recurrence(recurrence)

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            category_id = None
            if category:
                category_row = await conn.fetchrow(
                    """
                    SELECT id FROM categories
                    WHERE name = $1 AND type = 'reminder' AND user_id = $2
                    """,
                    category,
                    user_id,
                )
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (id, user_id, name, type, color)
                        VALUES (gen_random_uuid(), $1, $2, 'reminder', '#F59E0B')
                        RETURNING id
                        """,
                        user_id,
                        category,
                    )
                category_id = category_row["id"]

            row = await conn.fetchrow(
                """
                INSERT INTO reminders (
                    user_id,
                    title,
                    description,
                    remind_at,
                    priority,
                    category_id,
                    is_recurring,
                    recurrence_rule,
                    status,
                    tags,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9, NOW(), NOW())
                RETURNING
                    id, title, description, remind_at, priority,
                    recurrence_rule, status, completed_at,
                    created_at, updated_at, category_id, tags
                """,
                user_id,
                title.strip(),
                description,
                parsed_remind_at,
                priority_int,
                category_id,
                bool(recurrence_rule),
                recurrence_rule,
                tags or [],
            )

            logger.info(f"Created reminder {row['id']} at {row['remind_at']}")

            return {
                "id": str(row["id"]),
                "title": row["title"],
                "description": row["description"],
                "remind_at": row["remind_at"],
                "priority": row["priority"],
                "category_id": str(row["category_id"]) if row["category_id"] else None,
                "recurrence": row["recurrence_rule"] or "none",
                "status": row["status"],
                "tags": row["tags"],
                "completed_at": row["completed_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    except Exception as e:
        logger.error(f"Error creating reminder: {e}", exc_info=True)
        raise


@tool
async def update_reminder(
    reminder_id: str,
    user_id: str = DEFAULT_USER_ID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    remind_at: Optional[str] = None,
    priority: Optional[str | int] = None,
    category: Optional[str] = None,
    recurrence: Optional[str] = None,
    is_completed: Optional[bool] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update an existing reminder. Only provided fields are updated.
    """
    if not reminder_id:
        raise ValueError("reminder_id is required")

    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    updates = []
    params = [reminder_id, user_id]
    param_count = 2

    if title is not None:
        param_count += 1
        params.append(title)
        updates.append(f"title = ${param_count}")

    if description is not None:
        param_count += 1
        params.append(description)
        updates.append(f"description = ${param_count}")

    if remind_at is not None:
        parsed = _normalize_remind_at(remind_at)
        if not parsed:
            raise ValueError("remind_at must be a valid date/time")
        param_count += 1
        params.append(parsed)
        updates.append(f"remind_at = ${param_count}")

    if priority is not None:
        param_count += 1
        params.append(_normalize_priority(priority))
        updates.append(f"priority = ${param_count}")

    if recurrence is not None:
        recurrence_rule = _normalize_recurrence(recurrence)
        param_count += 1
        params.append(recurrence_rule)
        updates.append(f"recurrence_rule = ${param_count}")
        updates.append("is_recurring = TRUE" if recurrence_rule else "is_recurring = FALSE")

    if is_completed is not None:
        param_count += 1
        status_value = "completed" if is_completed else "pending"
        params.append(status_value)
        updates.append(f"status = ${param_count}")
        if is_completed:
            updates.append("completed_at = NOW()")

    if status is not None and is_completed is None:
        param_count += 1
        params.append(status)
        updates.append(f"status = ${param_count}")
        if status == "completed":
            updates.append("completed_at = NOW()")

    if category is not None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            category_row = await conn.fetchrow(
                "SELECT id FROM categories WHERE name = $1 AND type = 'reminder'",
                category
            )
            if not category_row:
                category_row = await conn.fetchrow(
                    """
                    INSERT INTO categories (name, type, color)
                    VALUES ($1, 'reminder', '#F59E0B')
                    RETURNING id
                    """,
                    category
                )
            category_id = category_row["id"]
            param_count += 1
            params.append(category_id)
            updates.append(f"category_id = ${param_count}")
    else:
        pool = await get_db_pool()

    if tags is not None:
        param_count += 1
        params.append(tags)
        updates.append(f"tags = ${param_count}")

    if not updates:
        raise ValueError("No fields to update")

    updates.append("updated_at = NOW()")

    query = f"""
        UPDATE reminders
        SET {', '.join(updates)}
        WHERE id = $1 AND user_id = $2
        RETURNING
            id, title, description, remind_at, priority,
            recurrence_rule, status, completed_at,
            created_at, updated_at, category_id, tags
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if not row:
                raise ValueError("Reminder not found or unauthorized")

            logger.info(f"Updated reminder {reminder_id}")
            return {
                "id": str(row["id"]),
                "title": row["title"],
                "description": row["description"],
                "remind_at": row["remind_at"],
                "priority": row["priority"],
                "category_id": str(row["category_id"]) if row["category_id"] else None,
                "recurrence": row["recurrence_rule"] or "none",
                "status": row["status"],
                "tags": row["tags"],
                "completed_at": row["completed_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
    except Exception as e:
        logger.error(f"Error updating reminder {reminder_id}: {e}", exc_info=True)
        raise


@tool
async def complete_reminder(
    reminder_id: str,
    user_id: str = DEFAULT_USER_ID
) -> Dict[str, Any]:
    """Mark a reminder as completed."""
    return await update_reminder(reminder_id=reminder_id, user_id=user_id, is_completed=True)


@tool
async def get_reminders_today(
    user_id: str = DEFAULT_USER_ID,
    include_completed: bool = False
) -> List[Dict[str, Any]]:
    """Get reminders scheduled for today."""
    status_filter = "" if include_completed else "AND r.status <> 'completed'"
    pool = await get_db_pool()

    query = f"""
        SELECT
            r.id, r.title, r.description, r.remind_at, r.priority,
            r.recurrence_rule, r.status, r.completed_at,
            r.created_at, r.updated_at,
            c.name as category
        FROM reminders r
        LEFT JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = $1
          AND DATE(r.remind_at) = CURRENT_DATE
          {status_filter}
        ORDER BY r.remind_at ASC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            logger.info(f"Found {len(rows)} reminders for today")
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching today's reminders: {e}", exc_info=True)
        raise


@tool
async def get_reminders_due_soon(
    user_id: str = DEFAULT_USER_ID,
    minutes_ahead: int = 1440,
    include_completed: bool = False,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get reminders due within the next N minutes.
    """
    if minutes_ahead < 1 or minutes_ahead > 10080:
        raise ValueError("minutes_ahead must be between 1 and 10080")

    validate_limit(limit)

    status_clause = "" if include_completed else "AND r.status <> 'completed'"

    pool = await get_db_pool()

    query = f"""
        SELECT
            r.id, r.title, r.description, r.remind_at, r.priority,
            r.recurrence_rule, r.status, r.completed_at,
            r.created_at, r.updated_at,
            c.name as category
        FROM reminders r
        LEFT JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = $1
          {status_clause}
          AND r.remind_at <= NOW() + INTERVAL '1 minute' * $2
          AND r.remind_at >= NOW()
        ORDER BY r.remind_at ASC
        LIMIT $3
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, minutes_ahead, limit)
            logger.info(f"Found {len(rows)} upcoming reminders")
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching upcoming reminders: {e}", exc_info=True)
        raise
