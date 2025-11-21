# Event Tools Implementation Plan - Complete Guide for LLM

## Overview

This document provides complete instructions for implementing 18 new event management tools across 4 categories. This continues the pattern established with task tools integration.

**Context**: We just added 21 new task tools. Now we're adding 18 event tools following the same patterns.

---

## Current Progress Status

### ✅ Completed (2 of 4 files)

1. **`tools/event_bulk_operations.py`** - 5 tools ✅ DONE
   - bulk_create_events
   - bulk_update_event_status
   - bulk_reschedule_events
   - bulk_add_attendees
   - bulk_delete_events

2. **`tools/event_recurring.py`** - 5 tools ✅ DONE
   - create_recurring_event
   - update_recurring_series
   - skip_recurring_instance
   - delete_recurring_series
   - get_recurring_series

### ⏳ Remaining (2 of 4 files)

3. **`tools/event_advanced_search.py`** - 4 tools ⏳ TODO
   - search_by_attendees
   - search_by_location
   - advanced_event_filter
   - get_event_statistics

4. **`tools/event_scheduling.py`** - 4 tools ⏳ TODO
   - find_available_slots
   - suggest_meeting_times
   - bulk_check_conflicts
   - get_busy_free_times

### Integration Steps (All Pending)

5. Update `tools/__init__.py` with imports
6. Update `agents/event_agent.py` with new tools
7. Update `prompts/event_agent.txt` with documentation
8. Test imports
9. Create integration summary

---

## Database Schema Reference

### Events Table (from `/mnt/user/appdata/ai_stack/migrations/004_add_events.sql`)

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    category_id UUID REFERENCES categories(id),

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    url TEXT,

    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    is_all_day BOOLEAN DEFAULT FALSE,

    -- Recurrence (ALREADY USED BY event_recurring.py)
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,
    recurrence_end_date TIMESTAMP,
    recurrence_parent_id UUID REFERENCES events(id),

    -- Google Calendar integration (not used yet)
    google_calendar_id TEXT,
    google_event_id TEXT UNIQUE,
    google_sync_at TIMESTAMP,
    google_sync_token TEXT,

    -- Attendees (TO BE USED)
    attendees JSONB,  -- [{"email": "...", "name": "...", "status": "accepted"}, ...]
    organizer TEXT,

    -- Reminders
    reminders INTEGER[] DEFAULT ARRAY[15],

    -- Status (ALREADY USED BY bulk_operations)
    status TEXT DEFAULT 'confirmed',  -- confirmed, tentative, cancelled

    -- Metadata (TO BE USED)
    tags TEXT[],
    metadata JSONB,
    conference_link TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes available
CREATE INDEX idx_events_user ON events(user_id);
CREATE INDEX idx_events_start_time ON events(start_time);
CREATE INDEX idx_events_end_time ON events(end_time);
CREATE INDEX idx_events_tags ON events USING GIN(tags);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_time_range ON events(start_time, end_time);

-- Full-text search index
CREATE INDEX idx_events_text_search ON events USING GIN(
    to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, ''))
);
```

**Key Points**:
- `attendees JSONB` is available but not indexed - may need GIN index for performance
- `tags TEXT[]` already has GIN index
- Full-text search index already exists
- Time range queries optimized with composite index

---

## Part 1: event_advanced_search.py - Implementation Details

**File**: `/mnt/user/appdata/ai_stack/containers/langgraph-agents/tools/event_advanced_search.py`

### Code Template Structure

```python
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

# Tool implementations below...
```

### Tool 1: search_by_attendees

**Purpose**: Find events by participant email addresses

**SQL Pattern**:
```sql
-- Check if attendees JSONB contains specific emails
-- Use JSONB @> operator for containment
SELECT * FROM events
WHERE user_id = $1
  AND attendees @> '[{"email": "john@company.com"}]'::jsonb
```

**Implementation**:
```python
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

    try:
        async with pool.acquire() as conn:
            if match_all:
                # Must have ALL attendees - use multiple @> checks with AND
                # Build WHERE clause dynamically
                conditions = []
                params = [user_id]
                param_idx = 2

                for email in attendee_emails:
                    conditions.append(f"attendees @> $({param_idx})::jsonb")
                    params.append(f'[{{"email": "{email}"}}]')
                    param_idx += 1

                where_clause = " AND ".join(conditions)

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
                # ANY attendee - use OR logic
                # Use jsonb_array_elements to expand attendees array
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
```

### Tool 2: search_by_location

**Purpose**: Find events by location or conference link

**SQL Pattern**:
```sql
-- Use ILIKE for case-insensitive pattern matching
SELECT * FROM events
WHERE user_id = $1
  AND (location ILIKE '%zoom%' OR conference_link ILIKE '%zoom%')
```

**Implementation**:
```python
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
```

### Tool 3: advanced_event_filter

**Purpose**: Multi-criteria filtering (like advanced_task_filter)

**Implementation Pattern**: Dynamic query building

```python
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

    try:
        # Build dynamic query
        conditions = ["user_id = $1"]
        params = [user_id]
        param_idx = 2

        if status:
            conditions.append(f"status = ANY(${param_idx})")
            params.append(status)
            param_idx += 1

        if tags:
            # Event must have at least one of the specified tags
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
```

### Tool 4: get_event_statistics

**Purpose**: Calendar analytics and metrics

**SQL Pattern**: Use aggregations, GROUP BY, and date functions

```python
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
        # Default to last 30 days if not specified
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now().isoformat()

        async with pool.acquire() as conn:
            # Total events and hours
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

            # By status
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

            # By day of week
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

            # By location (top 10)
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

            # Compile results
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

            # Find busiest day
            if result["by_day_of_week"]:
                result["busiest_day"] = max(result["by_day_of_week"], key=result["by_day_of_week"].get)
            else:
                result["busiest_day"] = None

            logger.info(f"Generated event statistics: {result['totals']['total_events']} events")
            return result

    except Exception as e:
        logger.error(f"Error getting event statistics: {e}")
        return {"error": str(e)}
```

---

## Part 2: event_scheduling.py - Implementation Details

**File**: `/mnt/user/appdata/ai_stack/containers/langgraph-agents/tools/event_scheduling.py`

### Code Template Structure

```python
"""
Scheduling helper tools for finding available time slots.

Provides smart scheduling assistance and conflict checking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"

# Helper function for business hours
def is_business_hours(dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
    """Check if datetime is within business hours."""
    return start_hour <= dt.hour < end_hour and dt.weekday() < 5  # Mon-Fri

# Tool implementations below...
```

### Tool 1: find_available_slots

**Purpose**: Find free time slots in calendar

**Algorithm**:
1. Get all events in the date range
2. Generate all possible time slots (e.g., every 30 min from 9am-5pm)
3. Filter out slots that overlap with events
4. Return available slots

**Implementation**:
```python
@tool
async def find_available_slots(
    start_date: str,
    end_date: str,
    duration_minutes: int,
    user_id: str = USER_ID,
    business_hours_only: bool = True,
    business_start_hour: int = 9,
    business_end_hour: int = 17
) -> List[Dict[str, str]]:
    """
    Find available time slots in the calendar.

    Args:
        start_date: Start of search period (ISO format)
        end_date: End of search period (ISO format)
        duration_minutes: Required slot duration in minutes
        user_id: User identifier
        business_hours_only: Only search during business hours (default True)
        business_start_hour: Business day start (default 9)
        business_end_hour: Business day end (default 17)

    Returns:
        List of available time slots with start and end times
    """
    pool = await get_db_pool()

    try:
        # Get all events in the period
        async with pool.acquire() as conn:
            events = await conn.fetch(
                """
                SELECT start_time, end_time
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time < $3
                  AND status != 'cancelled'
                ORDER BY start_time
                """,
                user_id, start_date, end_date
            )

        # Convert to datetime objects
        busy_slots = []
        for event in events:
            busy_slots.append({
                "start": event["start_time"],
                "end": event["end_time"]
            })

        # Generate available slots
        available = []
        current = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        slot_duration = timedelta(minutes=duration_minutes)

        while current + slot_duration <= end:
            # Check business hours if required
            if business_hours_only:
                if not (business_start_hour <= current.hour < business_end_hour and current.weekday() < 5):
                    current += timedelta(minutes=30)  # Skip in 30-min increments
                    continue

            # Check if slot overlaps with any busy period
            slot_end = current + slot_duration
            is_available = True

            for busy in busy_slots:
                # Check for overlap
                if not (slot_end <= busy["start"] or current >= busy["end"]):
                    is_available = False
                    break

            if is_available:
                available.append({
                    "start": current.isoformat(),
                    "end": slot_end.isoformat()
                })

            # Move to next slot (30-min increments)
            current += timedelta(minutes=30)

        logger.info(f"Found {len(available)} available slots")
        return available

    except Exception as e:
        logger.error(f"Error finding available slots: {e}")
        return []
```

### Tool 2: suggest_meeting_times

**Purpose**: AI-powered meeting time suggestions

**Implementation**: Wrapper around find_available_slots with preferences

```python
@tool
async def suggest_meeting_times(
    duration_minutes: int,
    user_id: str = USER_ID,
    days_ahead: int = 7,
    preferred_time: str = "morning",
    max_suggestions: int = 5
) -> List[Dict[str, Any]]:
    """
    Suggest optimal meeting times based on calendar availability.

    Args:
        duration_minutes: Meeting duration in minutes
        user_id: User identifier
        days_ahead: How many days to look ahead (default 7)
        preferred_time: Preference (morning, afternoon, anytime)
        max_suggestions: Maximum suggestions to return

    Returns:
        List of suggested time slots with reasoning
    """
    # Get available slots
    start_date = datetime.now().isoformat()
    end_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()

    # Find all available slots
    available_slots = await find_available_slots(
        start_date=start_date,
        end_date=end_date,
        duration_minutes=duration_minutes,
        user_id=user_id,
        business_hours_only=True
    )

    if not available_slots:
        return []

    # Score and filter based on preferences
    scored_slots = []

    for slot in available_slots:
        slot_start = datetime.fromisoformat(slot["start"])
        hour = slot_start.hour
        score = 0
        reasons = []

        # Preference scoring
        if preferred_time == "morning" and 9 <= hour < 12:
            score += 10
            reasons.append("Morning slot as preferred")
        elif preferred_time == "afternoon" and 13 <= hour < 17:
            score += 10
            reasons.append("Afternoon slot as preferred")

        # Avoid very early or very late
        if hour < 9 or hour >= 16:
            score -= 5
            reasons.append("Outside prime hours")

        # Prefer Tuesday-Thursday
        if slot_start.weekday() in [1, 2, 3]:  # Tue, Wed, Thu
            score += 5
            reasons.append("Mid-week timing")

        # Prefer slots not back-to-back (have buffer)
        # This would require checking surrounding events (simplified here)

        scored_slots.append({
            "start": slot["start"],
            "end": slot["end"],
            "score": score,
            "day_of_week": slot_start.strftime("%A"),
            "time_of_day": "morning" if hour < 12 else "afternoon",
            "reasons": reasons
        })

    # Sort by score and return top suggestions
    scored_slots.sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"Generated {len(scored_slots[:max_suggestions])} meeting suggestions")
    return scored_slots[:max_suggestions]
```

### Tool 3: bulk_check_conflicts

**Purpose**: Check multiple potential time slots for conflicts

**Implementation**:
```python
@tool
async def bulk_check_conflicts(
    proposed_slots: List[Dict[str, str]],
    user_id: str = USER_ID
) -> List[Dict[str, Any]]:
    """
    Check multiple proposed time slots for conflicts.

    Useful for meeting polls or finding which times work.

    Args:
        proposed_slots: List of slots with start and end times
        user_id: User identifier

    Example:
        proposed_slots = [
            {"start": "2025-01-15 09:00", "end": "2025-01-15 10:00"},
            {"start": "2025-01-15 14:00", "end": "2025-01-15 15:00"},
        ]

    Returns:
        List of results showing availability and conflicts for each slot
    """
    pool = await get_db_pool()

    try:
        results = []

        async with pool.acquire() as conn:
            for idx, slot in enumerate(proposed_slots):
                start_time = slot["start"]
                end_time = slot["end"]

                # Check for conflicts
                conflicts = await conn.fetch(
                    """
                    SELECT id, title, start_time, end_time
                    FROM events
                    WHERE user_id = $1
                      AND status != 'cancelled'
                      AND (
                          (start_time <= $2 AND end_time > $2)
                          OR (start_time < $3 AND end_time >= $3)
                          OR (start_time >= $2 AND end_time <= $3)
                      )
                    """,
                    user_id, start_time, end_time
                )

                conflict_list = []
                for conflict in conflicts:
                    conflict_list.append({
                        "id": str(conflict["id"]),
                        "title": conflict["title"],
                        "start": conflict["start_time"].isoformat(),
                        "end": conflict["end_time"].isoformat()
                    })

                results.append({
                    "slot_index": idx,
                    "proposed_start": start_time,
                    "proposed_end": end_time,
                    "available": len(conflict_list) == 0,
                    "conflict_count": len(conflict_list),
                    "conflicts": conflict_list
                })

        available_count = sum(1 for r in results if r["available"])
        logger.info(f"Checked {len(results)} slots: {available_count} available")

        return results

    except Exception as e:
        logger.error(f"Error checking bulk conflicts: {e}")
        return []
```

### Tool 4: get_busy_free_times

**Purpose**: Get busy/free blocks for a date range (free/busy report)

**Implementation**:
```python
@tool
async def get_busy_free_times(
    start_date: str,
    end_date: str,
    user_id: str = USER_ID,
    granularity_minutes: int = 30
) -> Dict[str, List[Dict[str, str]]]:
    """
    Get busy and free time blocks for a date range.

    Similar to Google Calendar's free/busy view.

    Args:
        start_date: Start of period (ISO format)
        end_date: End of period (ISO format)
        user_id: User identifier
        granularity_minutes: Time block size (default 30)

    Returns:
        Dict with 'busy' and 'free' arrays of time blocks
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get all non-cancelled events in period
            events = await conn.fetch(
                """
                SELECT start_time, end_time, title
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND end_time <= $3
                  AND status != 'cancelled'
                ORDER BY start_time
                """,
                user_id, start_date, end_date
            )

        busy_blocks = []
        for event in events:
            busy_blocks.append({
                "start": event["start_time"].isoformat(),
                "end": event["end_time"].isoformat(),
                "title": event["title"]
            })

        # Calculate free blocks (gaps between busy blocks)
        free_blocks = []

        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        if not busy_blocks:
            # Entire period is free
            free_blocks.append({
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            })
        else:
            # Free before first event
            first_event_start = datetime.fromisoformat(busy_blocks[0]["start"])
            if start_dt < first_event_start:
                free_blocks.append({
                    "start": start_dt.isoformat(),
                    "end": first_event_start.isoformat()
                })

            # Free between events
            for i in range(len(busy_blocks) - 1):
                current_end = datetime.fromisoformat(busy_blocks[i]["end"])
                next_start = datetime.fromisoformat(busy_blocks[i + 1]["start"])

                if current_end < next_start:
                    free_blocks.append({
                        "start": current_end.isoformat(),
                        "end": next_start.isoformat()
                    })

            # Free after last event
            last_event_end = datetime.fromisoformat(busy_blocks[-1]["end"])
            if last_event_end < end_dt:
                free_blocks.append({
                    "start": last_event_end.isoformat(),
                    "end": end_dt.isoformat()
                })

        result = {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "busy": busy_blocks,
            "free": free_blocks,
            "summary": {
                "total_busy_blocks": len(busy_blocks),
                "total_free_blocks": len(free_blocks)
            }
        }

        logger.info(f"Generated busy/free report: {len(busy_blocks)} busy, {len(free_blocks)} free")
        return result

    except Exception as e:
        logger.error(f"Error getting busy/free times: {e}")
        return {"error": str(e), "busy": [], "free": []}
```

---

## Part 3: Integration Steps

### Step 1: Update tools/__init__.py

**Location**: `/mnt/user/appdata/ai_stack/containers/langgraph-agents/tools/__init__.py`

**Add these imports** (after the existing task tool imports):

```python
# Event bulk operations
from .event_bulk_operations import (
    bulk_create_events,
    bulk_update_event_status,
    bulk_reschedule_events,
    bulk_add_attendees,
    bulk_delete_events,
)

# Event recurring
from .event_recurring import (
    create_recurring_event,
    update_recurring_series,
    skip_recurring_instance,
    delete_recurring_series,
    get_recurring_series,
)

# Event advanced search
from .event_advanced_search import (
    search_by_attendees,
    search_by_location,
    advanced_event_filter,
    get_event_statistics,
)

# Event scheduling
from .event_scheduling import (
    find_available_slots,
    suggest_meeting_times,
    bulk_check_conflicts,
    get_busy_free_times,
)
```

**Update __all__ list** to include all 18 new tools:

```python
__all__ = [
    # ... existing tools ...

    # Event bulk operations
    "bulk_create_events",
    "bulk_update_event_status",
    "bulk_reschedule_events",
    "bulk_add_attendees",
    "bulk_delete_events",

    # Event recurring
    "create_recurring_event",
    "update_recurring_series",
    "skip_recurring_instance",
    "delete_recurring_series",
    "get_recurring_series",

    # Event advanced search
    "search_by_attendees",
    "search_by_location",
    "advanced_event_filter",
    "get_event_statistics",

    # Event scheduling
    "find_available_slots",
    "suggest_meeting_times",
    "bulk_check_conflicts",
    "get_busy_free_times",
]
```

### Step 2: Update agents/event_agent.py

**Location**: `/mnt/user/appdata/ai_stack/containers/langgraph-agents/agents/event_agent.py`

**Current imports** (search for this pattern):
```python
from tools import (
    search_events,
    create_event,
    get_events_today,
    get_events_week,
    check_time_conflicts,
)
```

**Replace with** (add all 18 new tools):
```python
from tools import (
    # Basic event operations (6 tools)
    search_events,
    create_event,
    get_events_today,
    get_events_week,
    check_time_conflicts,
    unified_search,  # Already exists from task tools
    # Event bulk operations (5 tools)
    bulk_create_events,
    bulk_update_event_status,
    bulk_reschedule_events,
    bulk_add_attendees,
    bulk_delete_events,
    # Event recurring (5 tools)
    create_recurring_event,
    update_recurring_series,
    skip_recurring_instance,
    delete_recurring_series,
    get_recurring_series,
    # Event advanced search (4 tools)
    search_by_attendees,
    search_by_location,
    advanced_event_filter,
    get_event_statistics,
    # Event scheduling (4 tools)
    find_available_slots,
    suggest_meeting_times,
    bulk_check_conflicts,
    get_busy_free_times,
)
```

**Find EVENT_TOOLS list** (around line 40):
```python
EVENT_TOOLS = [
    search_events,
    create_event,
    get_events_today,
    get_events_week,
    check_time_conflicts,
]
```

**Replace with**:
```python
# Define tools once (25 tools total: 6 original + 18 new + unified_search)
EVENT_TOOLS = [
    # Basic event operations (6 tools)
    search_events,
    create_event,
    get_events_today,
    get_events_week,
    check_time_conflicts,
    unified_search,  # Cross-entity search
    # Event bulk operations (5 tools)
    bulk_create_events,
    bulk_update_event_status,
    bulk_reschedule_events,
    bulk_add_attendees,
    bulk_delete_events,
    # Event recurring (5 tools)
    create_recurring_event,
    update_recurring_series,
    skip_recurring_instance,
    delete_recurring_series,
    get_recurring_series,
    # Event advanced search (4 tools)
    search_by_attendees,
    search_by_location,
    advanced_event_filter,
    get_event_statistics,
    # Event scheduling (4 tools)
    find_available_slots,
    suggest_meeting_times,
    bulk_check_conflicts,
    get_busy_free_times,
]
```

### Step 3: Update prompts/event_agent.txt

**Location**: `/mnt/user/appdata/ai_stack/containers/langgraph-agents/prompts/event_agent.txt`

**Find the "Tools at Your Disposal" section** and replace with:

```markdown
## Tools at Your Disposal

You have access to 25 powerful calendar management tools organized by functionality:

### Basic Event Operations
- search_events: Search events by date range
- create_event: Create a single event
- get_events_today: Show today's calendar
- get_events_week: Show this week's events
- check_time_conflicts: Check if a time slot is free
- unified_search: Search across tasks, events, and reminders

### Bulk Operations (for efficiency)
- bulk_create_events: Create multiple events at once (meetings, time blocks, etc.)
- bulk_update_event_status: Cancel/confirm multiple events (useful when sick, traveling)
- bulk_reschedule_events: Shift multiple events by time delta (reschedule day's meetings)
- bulk_add_attendees: Add people to multiple events (add team member to all meetings)
- bulk_delete_events: Delete multiple events (cleanup, remove old events)

Use these when users want to:
- "Schedule 5 meetings: Monday 9am, Tuesday 2pm..."
- "Cancel all my meetings tomorrow" (sick day)
- "Move all afternoon meetings back 1 hour"
- "Add Sarah to all client meetings this week"

### Recurring Events (leveraging native support)
- create_recurring_event: Create event series (daily, weekly, biweekly, monthly)
- update_recurring_series: Change all future occurrences
- skip_recurring_instance: Cancel one occurrence (holiday, vacation)
- delete_recurring_series: Remove entire series
- get_recurring_series: List all instances of recurring event

Use these when users want to:
- "Schedule weekly team meeting every Monday at 9am"
- "Daily standup for the next 2 weeks"
- "No standup on Friday" (skip instance)
- "Move weekly sync to Tuesdays" (update series)

### Advanced Search & Analytics
- search_by_attendees: Find events by participant ("all meetings with John")
- search_by_location: Find events by location ("all Zoom meetings", "Conference Room A")
- advanced_event_filter: Multi-criteria search (status, tags, attendees, dates, location)
- get_event_statistics: Calendar analytics (meeting hours, breakdown by day/location/status)

Use these when users want to:
- "Show all meetings with the client team"
- "How much time do I spend in meetings?"
- "Find all events in the downtown office"
- "Show confirmed meetings next week with attendees"

### Scheduling Helpers (smart scheduling)
- find_available_slots: Find free time slots ("when am I free tomorrow?")
- suggest_meeting_times: AI-powered suggestions with preferences
- bulk_check_conflicts: Check multiple proposed times ("which of these 5 times work?")
- get_busy_free_times: Free/busy report for a period

Use these when users want to:
- "When am I available for a 1-hour meeting this week?"
- "Suggest good times for a client call"
- "Check if I'm free at 2pm, 3pm, or 4pm tomorrow"
- "Show my availability for next week"

## Example Interactions

**Basic Operations:**
User: "Add a meeting with the client tomorrow at 2pm"
You: *Use create_event with title, start_time, end_time*

User: "What's on my calendar today?"
You: *Use get_events_today*

**Bulk Operations:**
User: "I'm sick tomorrow, cancel all my meetings"
You: *Use search_events for tomorrow, then bulk_update_event_status with status='cancelled'*

User: "Schedule meetings with Design team: Monday 2pm, Wednesday 3pm, Friday 10am"
You: *Use bulk_create_events with all three meetings*

**Recurring Events:**
User: "Schedule weekly team standup every Monday at 9am for the next 3 months"
You: *Use create_recurring_event with pattern='weekly', count=12*

User: "No standup next Monday, it's a holiday"
You: *Find the specific instance, use skip_recurring_instance*

**Advanced Search:**
User: "Show all meetings with John Smith"
You: *Use search_by_attendees with john.smith@company.com*

User: "How much time do I spend in meetings per week?"
You: *Use get_event_statistics to analyze meeting hours*

**Scheduling:**
User: "When am I free tomorrow afternoon?"
You: *Use find_available_slots with tomorrow's date, business hours afternoon*

User: "Find a good time for a 2-hour meeting next week"
You: *Use suggest_meeting_times with duration=120, days_ahead=7*

**Handoffs:**
User: "Add a task to prepare for the meeting"
You: "I'll connect you with the Task Agent who handles to-do items."
*HANDOFF to task_agent*
```

### Step 4: Test Imports

Run syntax check:
```bash
cd /mnt/user/appdata/ai_stack/containers/langgraph-agents/tools
python3 -m py_compile event_advanced_search.py event_scheduling.py
python3 -m py_compile __init__.py
cd ..
python3 -m py_compile agents/event_agent.py
```

### Step 5: Create Integration Summary

Create file: `EVENT_TOOLS_INTEGRATION_SUMMARY.md`

Should include:
- What was integrated (18 tools)
- Files created (4 new files)
- Files modified (3 files)
- Database compatibility (no migration needed)
- Testing instructions
- Performance expectations
- Comparison with task tools

---

## Code Patterns to Follow

### 1. Import Pattern
```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)
USER_ID = "00000000-0000-0000-0000-000000000001"
```

### 2. Tool Decorator
```python
@tool
async def tool_name(
    param1: str,
    param2: Optional[str] = None,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Clear description of what this tool does.

    Args:
        param1: Description
        param2: Description (optional)
        user_id: User identifier

    Returns:
        Description of return value
    """
```

### 3. Database Query Pattern
```python
pool = await get_db_pool()

try:
    async with pool.acquire() as conn:
        result = await conn.fetch(query, *params)
        # Process result
        logger.info(f"Success message")
        return {"success": True, "data": result}
except Exception as e:
    logger.error(f"Error: {e}")
    return {"success": False, "error": str(e)}
```

### 4. UUID Handling
```python
# Convert UUID to string for JSON serialization
"id": str(row["id"])
```

### 5. DateTime Handling
```python
# Convert timestamp to ISO string
"start_time": row["start_time"].isoformat()

# Parse ISO string to datetime
dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
```

---

## Testing Plan

### After Implementation

1. **Syntax Check**
   ```bash
   python3 -m py_compile tools/event_*.py
   ```

2. **Import Test** (requires Docker)
   ```bash
   docker exec -it langgraph-agents python3 -c "from tools import bulk_create_events; print('OK')"
   ```

3. **Rebuild Container**
   ```bash
   cd /mnt/user/appdata/ai_stack
   docker build -t langgraph-agents:latest containers/langgraph-agents/
   docker-compose restart langgraph-agents
   ```

4. **API Tests** (via curl)
   - Test bulk_create_events
   - Test create_recurring_event
   - Test find_available_slots
   - Test get_event_statistics

---

## Expected Outcomes

### Tool Count
- **Before**: 6 event tools
- **After**: 24 event tools (6 + 18 new)
- **Task Agent**: 26 tools (for comparison)

### Files Created
1. `tools/event_bulk_operations.py` - 277 lines
2. `tools/event_recurring.py` - 318 lines
3. `tools/event_advanced_search.py` - ~350 lines (estimate)
4. `tools/event_scheduling.py` - ~380 lines (estimate)

### Files Modified
1. `tools/__init__.py` - Add 18 imports
2. `agents/event_agent.py` - Add 18 tools to imports and EVENT_TOOLS list
3. `prompts/event_agent.txt` - Expand documentation

### Performance
- Bulk operations: ~70% faster than individual calls
- Recurring events: Creates series in one transaction
- Search tools: Leverage existing indexes (fast)
- Scheduling tools: Algorithmic (client-side calculation)

---

## Common Errors to Avoid

1. **Missing datetime import** - Already fixed in task tools
2. **UUID serialization** - Always use `str(uuid)`
3. **Timestamp serialization** - Always use `.isoformat()`
4. **SQL injection** - Always use parameterized queries
5. **JSONB null handling** - Check `IS NOT NULL` before operations
6. **Array operations** - Use PostgreSQL array operators correctly
7. **Limit validation** - Check max limits on user inputs

---

## Success Criteria

✅ All 4 tool files created
✅ All files pass Python syntax check
✅ tools/__init__.py imports all 18 new tools
✅ event_agent.py uses all 18 new tools
✅ event_agent.txt documents all capabilities
✅ Integration summary document created
✅ No database migration required
✅ Container builds successfully
✅ API tests pass

---

## Priority Order for Implementation

If time-limited, implement in this order:

1. **event_advanced_search.py** (4 tools) - High user value, leverages existing indexes
2. **event_scheduling.py** (4 tools) - Unique calendar features, high impact
3. Integration steps 1-3 (update __init__, agent, prompt)
4. Testing

This gives you 8 new tools + integration, expanding from 6 → 14 event tools.

Full implementation (all 18 tools) is ~2-3 hours of work.

---

## Quick Start Command

To continue this work in a new session:

```bash
cd /mnt/user/appdata/ai_stack/containers/langgraph-agents
cat EVENT_TOOLS_IMPLEMENTATION_PLAN.md
# Then implement tools/event_advanced_search.py following the specs above
# Then implement tools/event_scheduling.py following the specs above
# Then follow integration steps 1-5
```

Good luck! 🚀
