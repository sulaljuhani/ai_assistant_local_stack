"""
Bulk operations for calendar events.

Enables efficient batch operations on multiple events at once.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def bulk_create_events(
    events: List[Dict[str, Any]],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Create multiple calendar events at once.

    Useful for scheduling multiple meetings, blocking time, or creating event series.

    Args:
        events: List of event dicts with title, start_time, end_time, description, location
        user_id: User identifier

    Example:
        events = [
            {"title": "Team Meeting", "start_time": "2025-01-15 09:00", "end_time": "2025-01-15 10:00"},
            {"title": "Client Call", "start_time": "2025-01-15 14:00", "end_time": "2025-01-15 15:00"},
        ]

    Returns:
        Success status and created event IDs
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            created = []

            for event_data in events:
                title = event_data.get("title")
                start_time = event_data.get("start_time")
                end_time = event_data.get("end_time")

                if not title or not start_time or not end_time:
                    continue

                description = event_data.get("description")
                location = event_data.get("location")
                attendees = event_data.get("attendees")
                tags = event_data.get("tags", [])
                status = event_data.get("status", "confirmed")
                conference_link = event_data.get("conference_link")

                result = await conn.fetchrow(
                    """
                    INSERT INTO events (
                        user_id, title, description, start_time, end_time,
                        location, attendees, tags, status, conference_link
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id, title, start_time, end_time
                    """,
                    user_id, title, description, start_time, end_time,
                    location, attendees, tags, status, conference_link
                )

                created.append({
                    "id": str(result["id"]),
                    "title": result["title"],
                    "start_time": result["start_time"].isoformat(),
                    "end_time": result["end_time"].isoformat()
                })

            logger.info(f"Bulk created {len(created)} events")

            return {
                "success": True,
                "created_count": len(created),
                "events": created
            }

    except Exception as e:
        logger.error(f"Error bulk creating events: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_update_event_status(
    event_ids: List[str],
    new_status: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Update status for multiple events at once.

    Useful for canceling meetings when sick, confirming multiple events, etc.

    Args:
        event_ids: List of event IDs
        new_status: New status (confirmed, tentative, cancelled)
        user_id: User identifier

    Returns:
        Success status and count updated
    """
    if new_status not in ["confirmed", "tentative", "cancelled"]:
        return {"success": False, "error": "Status must be confirmed, tentative, or cancelled"}

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE events
                SET status = $1, updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                new_status,
                event_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.info(f"Bulk updated {count} events to status '{new_status}'")

            return {
                "success": True,
                "updated_count": count,
                "new_status": new_status
            }

    except Exception as e:
        logger.error(f"Error bulk updating event status: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_reschedule_events(
    event_ids: List[str],
    time_delta_minutes: int,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Shift multiple events by a time delta.

    Useful for moving meetings when schedule changes.

    Args:
        event_ids: List of event IDs
        time_delta_minutes: Minutes to shift (positive = later, negative = earlier)
        user_id: User identifier

    Examples:
        - Move events 1 hour later: time_delta_minutes=60
        - Move events 1 day earlier: time_delta_minutes=-1440

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE events
                SET
                    start_time = start_time + ($1 || ' minutes')::INTERVAL,
                    end_time = end_time + ($1 || ' minutes')::INTERVAL,
                    updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                time_delta_minutes,
                event_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            direction = "later" if time_delta_minutes > 0 else "earlier"
            hours = abs(time_delta_minutes) / 60

            logger.info(f"Bulk rescheduled {count} events {hours} hours {direction}")

            return {
                "success": True,
                "updated_count": count,
                "time_delta_minutes": time_delta_minutes,
                "time_delta_display": f"{hours} hours {direction}"
            }

    except Exception as e:
        logger.error(f"Error bulk rescheduling events: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_add_attendees(
    event_ids: List[str],
    attendees: List[Dict[str, str]],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Add attendees to multiple events at once.

    Useful for adding team members to multiple meetings.

    Args:
        event_ids: List of event IDs
        attendees: List of attendee dicts with email, name, status
        user_id: User identifier

    Example:
        attendees = [
            {"email": "sarah@company.com", "name": "Sarah", "status": "needs-action"},
            {"email": "mike@company.com", "name": "Mike", "status": "needs-action"}
        ]

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Update each event to add attendees
            count = 0
            for event_id in event_ids:
                # Get current attendees
                current = await conn.fetchval(
                    "SELECT attendees FROM events WHERE id = $1 AND user_id = $2",
                    event_id,
                    user_id
                )

                # Merge attendees (avoid duplicates by email)
                current_attendees = current or []
                existing_emails = {a.get("email") for a in current_attendees if isinstance(a, dict)}

                merged_attendees = list(current_attendees)
                for attendee in attendees:
                    if attendee.get("email") not in existing_emails:
                        merged_attendees.append(attendee)

                # Update event
                result = await conn.execute(
                    """
                    UPDATE events
                    SET attendees = $1, updated_at = NOW()
                    WHERE id = $2 AND user_id = $3
                    """,
                    merged_attendees,
                    event_id,
                    user_id
                )

                if result:
                    count += 1

            logger.info(f"Bulk added attendees to {count} events")

            return {
                "success": True,
                "updated_count": count,
                "attendees_added": len(attendees)
            }

    except Exception as e:
        logger.error(f"Error bulk adding attendees: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_delete_events(
    event_ids: List[str],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Delete multiple events at once.

    WARNING: This permanently deletes events. Consider using bulk_update_event_status
    with status='cancelled' instead.

    Args:
        event_ids: List of event IDs to delete
        user_id: User identifier

    Returns:
        Success status and count deleted
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM events WHERE id = ANY($1) AND user_id = $2",
                event_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.warning(f"Bulk deleted {count} events")

            return {
                "success": True,
                "deleted_count": count,
                "warning": "Events permanently deleted"
            }

    except Exception as e:
        logger.error(f"Error bulk deleting events: {e}")
        return {"success": False, "error": str(e)}
