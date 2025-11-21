"""
Advanced search and analytics for calendar events.

Leverages full-text search, JSONB queries, and aggregations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def search_by_attendees(
    attendee_emails: List[str],
    user_id: str = USER_ID,
    match_all: bool = False,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Find events by attendee email addresses.

    Args:
        attendee_emails: List of email addresses to search for
        user_id: User identifier
        match_all: If True, event must have ALL attendees. If False, ANY attendee.
        limit: Maximum results (default 20, max 100)

    Examples:
        - Find events with John: ["john@company.com"]
        - Find events with both Sarah AND Mike: ["sarah@", "mike@"], match_all=True

    Returns:
        List of matching events with attendee details
    """
    pool = await get_db_pool()
    limit = min(limit, 100)

    try:
        async with pool.acquire() as conn:
            if match_all:
                conditions = []
                params = [user_id]
                param_idx = 2

                for email in attendee_emails:
                    conditions.append(f"attendees @> $({param_idx})::jsonb")
                    params.append(f'[{{"email": "{email}"}}]')
                    param_idx += 1

                where_clause = " AND ".join(conditions) if conditions else "TRUE"

                query = f"""
                    SELECT
                        id, title, description, start_time, end_time,
                        location, attendees, status
                    FROM events
                    WHERE user_id = $1 AND {where_clause}
                    ORDER BY start_time ASC
                    LIMIT {limit}
                """
            else:
                query = """
                    SELECT DISTINCT
                        e.id, e.title, e.description, e.start_time, e.end_time,
                        e.location, e.attendees, e.status
                    FROM events e,
                         jsonb_array_elements(e.attendees) AS attendee
                    WHERE e.user_id = $1
                      AND attendee->>'email' = ANY($2)
                    ORDER BY e.start_time ASC
                    LIMIT $3
                """
                params = [user_id, attendee_emails, limit]

            rows = await conn.fetch(query, *params)

            results = []
            for row in rows:
                results.append({
                    "id": str(row["id"]),
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"].isoformat(),
                    "end_time": row["end_time"].isoformat(),
                    "location": row["location"],
                    "attendees": row["attendees"],
                    "status": row["status"]
                })

            logger.info(f"Found {len(results)} events with attendees")
            return results

    except Exception as e:
        logger.error(f"Error searching by attendees: {e}")
        return []


@tool
async def search_by_location(
    location_query: str,
    user_id: str = USER_ID,
    include_conference_links: bool = True,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Find events by location or conference link.

    Args:
        location_query: Location search term (supports partial matches)
        user_id: User identifier
        include_conference_links: Also search conference_link field
        limit: Maximum results (default 20)

    Examples:
        - "Conference Room A" - finds all events in that room
        - "Zoom" - finds all Zoom meetings
        - "Downtown" - finds events at downtown locations

    Returns:
        List of matching events
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            pattern = f"%{location_query}%"

            if include_conference_links:
                query = """
                    SELECT
                        id, title, start_time, end_time, location,
                        conference_link, attendees, status
                    FROM events
                    WHERE user_id = $1
                      AND (location ILIKE $2 OR conference_link ILIKE $2)
                      AND status != 'cancelled'
                    ORDER BY start_time ASC
                    LIMIT $3
                """
            else:
                query = """
                    SELECT
                        id, title, start_time, end_time, location,
                        conference_link, attendees, status
                    FROM events
                    WHERE user_id = $1
                      AND location ILIKE $2
                      AND status != 'cancelled'
                    ORDER BY start_time ASC
                    LIMIT $3
                """

            rows = await conn.fetch(query, user_id, pattern, limit)

            results = []
            for row in rows:
                results.append({
                    "id": str(row["id"]),
                    "title": row["title"],
                    "start_time": row["start_time"].isoformat(),
                    "end_time": row["end_time"].isoformat(),
                    "location": row["location"],
                    "conference_link": row["conference_link"],
                    "attendees_count": len(row["attendees"]) if row["attendees"] else 0,
                    "status": row["status"]
                })

            logger.info(f"Found {len(results)} events matching location '{location_query}'")
            return results

    except Exception as e:
        logger.error(f"Error searching by location: {e}")
        return []


@tool
async def advanced_event_filter(
    user_id: str = USER_ID,
    status: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    has_attendees: Optional[bool] = None,
    has_location: Optional[bool] = None,
    is_all_day: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    location_contains: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Advanced multi-criteria event filtering.

    Supports complex queries with multiple filters.

    Args:
        user_id: User identifier
        status: Filter by status (confirmed, tentative, cancelled)
        tags: Filter by tags (event must have ANY of these tags)
        has_attendees: Filter events with/without attendees
        has_location: Filter events with/without location
        is_all_day: Filter all-day events
        start_date: Events starting after this date (ISO format)
        end_date: Events starting before this date (ISO format)
        location_contains: Location text search
        limit: Maximum results (default 50, max 100)

    Returns:
        List of matching events
    """
    pool = await get_db_pool()
    limit = min(limit, 100)

    try:
        conditions = ["user_id = $1"]
        params = [user_id]
        param_idx = 2

        if status:
            conditions.append(f"status = ANY(${param_idx})")
            params.append(status)
            param_idx += 1

        if tags:
            conditions.append(f"tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        if has_attendees is not None:
            if has_attendees:
                conditions.append("attendees IS NOT NULL AND jsonb_array_length(attendees) > 0")
            else:
                conditions.append("(attendees IS NULL OR jsonb_array_length(attendees) = 0)")

        if has_location is not None:
            if has_location:
                conditions.append("location IS NOT NULL AND location != ''")
            else:
                conditions.append("(location IS NULL OR location = '')")

        if is_all_day is not None:
            conditions.append(f"is_all_day = ${param_idx}")
            params.append(is_all_day)
            param_idx += 1

        if start_date:
            conditions.append(f"start_time >= ${param_idx}")
            params.append(start_date)
            param_idx += 1

        if end_date:
            conditions.append(f"start_time <= ${param_idx}")
            params.append(end_date)
            param_idx += 1

        if location_contains:
            conditions.append(f"location ILIKE ${param_idx}")
            params.append(f"%{location_contains}%")
            param_idx += 1

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                id, title, description, start_time, end_time,
                location, attendees, status, tags, is_all_day
            FROM events
            WHERE {where_clause}
            ORDER BY start_time ASC
            LIMIT ${param_idx}
        """
        params.append(limit)

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            results = []
            for row in rows:
                results.append({
                    "id": str(row["id"]),
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"].isoformat(),
                    "end_time": row["end_time"].isoformat(),
                    "location": row["location"],
                    "attendees_count": len(row["attendees"]) if row["attendees"] else 0,
                    "status": row["status"],
                    "tags": row["tags"],
                    "is_all_day": row["is_all_day"]
                })

            logger.info(f"Advanced filter found {len(results)} events")
            return results

    except Exception as e:
        logger.error(f"Error in advanced event filter: {e}")
        return []


@tool
async def get_event_statistics(
    user_id: str = USER_ID,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about calendar events.

    Args:
        user_id: User identifier
        start_date: Start of analysis period (default: 30 days ago)
        end_date: End of analysis period (default: today)

    Returns:
        Statistics including:
        - Total events and meeting hours
        - Average meeting length
        - Events by status
        - Events by location
        - Busiest day of week
        - Events by tags
    """
    pool = await get_db_pool()

    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now().isoformat()

        async with pool.acquire() as conn:
            totals = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_events,
                    SUM(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600) as total_hours,
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time)) / 60) as avg_minutes
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time <= $3
                  AND status != 'cancelled'
                """,
                user_id, start_date, end_date
            )

            by_status = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time <= $3
                GROUP BY status
                ORDER BY count DESC
                """,
                user_id, start_date, end_date
            )

            by_day = await conn.fetch(
                """
                SELECT
                    TO_CHAR(start_time, 'Day') as day_name,
                    COUNT(*) as count
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time <= $3
                  AND status != 'cancelled'
                GROUP BY TO_CHAR(start_time, 'Day'), EXTRACT(DOW FROM start_time)
                ORDER BY EXTRACT(DOW FROM start_time)
                """,
                user_id, start_date, end_date
            )

            by_location = await conn.fetch(
                """
                SELECT location, COUNT(*) as count
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time <= $3
                  AND status != 'cancelled'
                  AND location IS NOT NULL
                  AND location != ''
                GROUP BY location
                ORDER BY count DESC
                LIMIT 10
                """,
                user_id, start_date, end_date
            )

            result = {
                "period": {
                    "start": start_date,
                    "end": end_date
                },
                "totals": {
                    "total_events": int(totals["total_events"] or 0),
                    "total_hours": round(float(totals["total_hours"] or 0), 1),
                    "avg_meeting_minutes": round(float(totals["avg_minutes"] or 0), 1)
                },
                "by_status": {row["status"]: int(row["count"]) for row in by_status},
                "by_day_of_week": {row["day_name"].strip(): int(row["count"]) for row in by_day},
                "by_location": {row["location"]: int(row["count"]) for row in by_location}
            }

            if result["by_day_of_week"]:
                result["busiest_day"] = max(
                    result["by_day_of_week"],
                    key=result["by_day_of_week"].get
                )
            else:
                result["busiest_day"] = None

            logger.info(f"Generated event statistics: {result['totals']['total_events']} events")
            return result

    except Exception as e:
        logger.error(f"Error getting event statistics: {e}")
        return {"error": str(e)}
