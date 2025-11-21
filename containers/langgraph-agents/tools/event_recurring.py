"""
Recurring event management tools.

Leverages the existing is_recurring, recurrence_rule, and recurrence_parent_id fields.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


def parse_simple_recurrence(recurrence_pattern: str, count: int = 52) -> List[int]:
    """
    Parse simple recurrence patterns into day offsets.

    Patterns:
    - "daily" -> every day
    - "weekly" -> every 7 days
    - "weekdays" -> Mon-Fri
    - "biweekly" -> every 14 days
    - "monthly" -> every 30 days (approximate)

    Args:
        recurrence_pattern: Simple pattern string
        count: Number of occurrences to generate

    Returns:
        List of day offsets from start date
    """
    pattern = recurrence_pattern.lower()

    if pattern == "daily":
        return list(range(0, count))
    elif pattern == "weekly":
        return [i * 7 for i in range(count)]
    elif pattern == "weekdays":
        # Generate weekday occurrences (skip weekends)
        offsets = []
        day = 0
        while len(offsets) < count:
            # Day 0 is the start, check what day of week it would be
            # For simplicity, we'll include all and let the date calculation handle it
            offsets.append(day)
            day += 1
            # Skip weekends (very simplified - assumes start is a weekday)
            if (day % 7) in [5, 6]:  # Sat, Sun (0-indexed from start)
                day += 2
        return offsets[:count]
    elif pattern == "biweekly":
        return [i * 14 for i in range(count)]
    elif pattern == "monthly":
        return [i * 30 for i in range(count)]  # Approximate
    else:
        # Default to weekly if unknown
        return [i * 7 for i in range(count)]


@tool
async def create_recurring_event(
    title: str,
    start_time: str,
    end_time: str,
    recurrence_pattern: str,
    occurrence_count: int = 10,
    user_id: str = USER_ID,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a recurring event series.

    Simplified recurrence using common patterns.

    Args:
        title: Event title
        start_time: First occurrence start time (ISO format)
        end_time: First occurrence end time (ISO format)
        recurrence_pattern: Pattern (daily, weekly, weekdays, biweekly, monthly)
        occurrence_count: Number of occurrences to create (default 10, max 100)
        user_id: User identifier
        description: Event description
        location: Event location
        attendees: List of attendees

    Examples:
        - "Schedule daily standup for 2 weeks": pattern="daily", count=10
        - "Weekly team meeting for 3 months": pattern="weekly", count=12
        - "Biweekly 1-on-1 for 6 months": pattern="biweekly", count=12

    Returns:
        Success status and created event IDs
    """
    if occurrence_count > 100:
        return {"success": False, "error": "Maximum 100 occurrences allowed"}

    pool = await get_db_pool()

    try:
        # Parse start and end times
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration = end_dt - start_dt

        # Get day offsets based on pattern
        day_offsets = parse_simple_recurrence(recurrence_pattern, occurrence_count)

        async with pool.acquire() as conn:
            # Create parent event (first occurrence)
            parent_event = await conn.fetchrow(
                """
                INSERT INTO events (
                    user_id, title, description, start_time, end_time, location,
                    attendees, is_recurring, recurrence_rule, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8, 'confirmed')
                RETURNING id, title, start_time
                """,
                user_id, title, description, start_time, end_time, location,
                attendees, f"PATTERN:{recurrence_pattern}"
            )

            parent_id = parent_event["id"]
            created = [{
                "id": str(parent_id),
                "title": parent_event["title"],
                "start_time": parent_event["start_time"].isoformat(),
                "is_parent": True
            }]

            # Create child occurrences (skip first as it's the parent)
            for offset in day_offsets[1:]:
                occurrence_start = start_dt + timedelta(days=offset)
                occurrence_end = occurrence_start + duration

                result = await conn.fetchrow(
                    """
                    INSERT INTO events (
                        user_id, title, description, start_time, end_time, location,
                        attendees, is_recurring, recurrence_parent_id, status
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8, 'confirmed')
                    RETURNING id, start_time
                    """,
                    user_id, title, description, occurrence_start, occurrence_end,
                    location, attendees, parent_id
                )

                created.append({
                    "id": str(result["id"]),
                    "start_time": result["start_time"].isoformat(),
                    "is_parent": False
                })

            logger.info(f"Created recurring event series: {len(created)} occurrences")

            return {
                "success": True,
                "parent_event_id": str(parent_id),
                "occurrence_count": len(created),
                "pattern": recurrence_pattern,
                "occurrences": created
            }

    except Exception as e:
        logger.error(f"Error creating recurring event: {e}")
        return {"success": False, "error": str(e)}


@tool
async def update_recurring_series(
    parent_event_id: str,
    user_id: str = USER_ID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    time_delta_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update all events in a recurring series.

    Args:
        parent_event_id: ID of the parent (first) event in the series
        user_id: User identifier
        title: New title for all events (optional)
        description: New description for all events (optional)
        location: New location for all events (optional)
        time_delta_minutes: Shift all events by this many minutes (optional)

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Verify parent event exists and belongs to user
            parent = await conn.fetchrow(
                """
                SELECT id FROM events
                WHERE id = $1 AND user_id = $2 AND is_recurring = TRUE
                  AND recurrence_parent_id IS NULL
                """,
                parent_event_id,
                user_id
            )

            if not parent:
                return {"success": False, "error": "Parent event not found"}

            # Build update query dynamically
            updates = []
            params = [user_id, parent_event_id]
            param_idx = 3

            if title:
                updates.append(f"title = ${param_idx}")
                params.append(title)
                param_idx += 1

            if description:
                updates.append(f"description = ${param_idx}")
                params.append(description)
                param_idx += 1

            if location:
                updates.append(f"location = ${param_idx}")
                params.append(location)
                param_idx += 1

            if time_delta_minutes is not None:
                updates.append(f"start_time = start_time + (${param_idx} || ' minutes')::INTERVAL")
                updates.append(f"end_time = end_time + (${param_idx} || ' minutes')::INTERVAL")
                params.append(time_delta_minutes)
                param_idx += 1

            if not updates:
                return {"success": False, "error": "No updates specified"}

            updates.append("updated_at = NOW()")

            # Update parent and all children
            query = f"""
                UPDATE events
                SET {', '.join(updates)}
                WHERE user_id = $1
                  AND (id = $2 OR recurrence_parent_id = $2)
            """

            result = await conn.execute(query, *params)
            count = int(result.split()[-1]) if result else 0

            logger.info(f"Updated {count} events in recurring series")

            return {
                "success": True,
                "updated_count": count,
                "parent_event_id": parent_event_id
            }

    except Exception as e:
        logger.error(f"Error updating recurring series: {e}")
        return {"success": False, "error": str(e)}


@tool
async def skip_recurring_instance(
    event_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Skip (cancel) one occurrence of a recurring event.

    The event remains in the database but is marked as cancelled.

    Args:
        event_id: ID of the specific occurrence to skip
        user_id: User identifier

    Returns:
        Success status
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE events
                SET status = 'cancelled', updated_at = NOW()
                WHERE id = $1 AND user_id = $2 AND is_recurring = TRUE
                """,
                event_id,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            if count == 0:
                return {"success": False, "error": "Event not found or not recurring"}

            logger.info(f"Skipped recurring event instance: {event_id}")

            return {
                "success": True,
                "event_id": event_id,
                "message": "Occurrence cancelled (other occurrences unaffected)"
            }

    except Exception as e:
        logger.error(f"Error skipping recurring instance: {e}")
        return {"success": False, "error": str(e)}


@tool
async def delete_recurring_series(
    parent_event_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Delete all events in a recurring series.

    WARNING: This permanently deletes all occurrences. Consider cancelling instead.

    Args:
        parent_event_id: ID of the parent (first) event in the series
        user_id: User identifier

    Returns:
        Success status and count deleted
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Delete parent and all children (CASCADE handles children via foreign key)
            result = await conn.execute(
                """
                DELETE FROM events
                WHERE user_id = $1
                  AND (id = $2 OR recurrence_parent_id = $2)
                """,
                user_id,
                parent_event_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.warning(f"Deleted recurring series: {count} events")

            return {
                "success": True,
                "deleted_count": count,
                "parent_event_id": parent_event_id,
                "warning": "All occurrences permanently deleted"
            }

    except Exception as e:
        logger.error(f"Error deleting recurring series: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_recurring_series(
    parent_event_id: str,
    user_id: str = USER_ID,
    include_cancelled: bool = False
) -> List[Dict[str, Any]]:
    """
    Get all instances of a recurring event series.

    Args:
        parent_event_id: ID of the parent (first) event in the series
        user_id: User identifier
        include_cancelled: Include cancelled occurrences (default False)

    Returns:
        List of all occurrences in the series
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            status_filter = "" if include_cancelled else "AND status != 'cancelled'"

            # Get parent and all children
            events = await conn.fetch(
                f"""
                SELECT
                    id, title, description, start_time, end_time,
                    location, status, attendees,
                    (recurrence_parent_id IS NULL) as is_parent
                FROM events
                WHERE user_id = $1
                  AND (id = $2 OR recurrence_parent_id = $2)
                  {status_filter}
                ORDER BY start_time ASC
                """,
                user_id,
                parent_event_id
            )

            result = []
            for event in events:
                result.append({
                    "id": str(event["id"]),
                    "title": event["title"],
                    "description": event["description"],
                    "start_time": event["start_time"].isoformat(),
                    "end_time": event["end_time"].isoformat(),
                    "location": event["location"],
                    "status": event["status"],
                    "attendees": event["attendees"],
                    "is_parent": event["is_parent"]
                })

            logger.info(f"Retrieved {len(result)} occurrences from recurring series")
            return result

    except Exception as e:
        logger.error(f"Error getting recurring series: {e}")
        return []
