"""
Events Router

API endpoints for event/calendar management operations.
Replaces n8n workflow: 03-create-event.json
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import json

from middleware.validation import (
    CreateEventRequest,
    UpdateEventRequest,
    SuccessResponse,
)
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
router = APIRouter(prefix="/api/events", tags=["events"])


# Response models
class EventResponse(BaseModel):
    """Event response model"""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    category: Optional[str]
    attendees: List[str]
    is_all_day: bool
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    """Event list response model"""
    events: List[EventResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# CREATE Event
# ============================================================================

@router.post("/create", response_model=EventResponse)
async def create_event(request: CreateEventRequest):
    """
    Create a new event.

    Replaces n8n workflow: 03-create-event.json

    Logic:
    1. Validate input (handled by Pydantic, including start_time < end_time)
    2. Get category ID from database (if category provided)
    3. Optionally check for time conflicts
    4. Insert event with parameterized query
    5. Return created event
    """
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Get category ID if category name provided
            category_id = None
            if request.category:
                category_row = await conn.fetchrow(
                    """
                    SELECT id FROM categories
                    WHERE name = $1 AND type = 'event'
                    LIMIT 1
                    """,
                    request.category
                )

                # If category doesn't exist, create it
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'event', '#10B981')
                        RETURNING id
                        """,
                        request.category
                    )

                category_id = category_row['id']

            # Optional: Check for time conflicts
            # (can be enabled/disabled based on requirements)
            # conflicts = await conn.fetch(
            #     """
            #     SELECT id, title FROM events
            #     WHERE (start_time, end_time) OVERLAPS ($1, $2)
            #     """,
            #     request.start_time,
            #     request.end_time
            # )
            # if conflicts:
            #     logger.warning(f"Event conflicts detected: {[c['title'] for c in conflicts]}")

            # Insert event
            start_time = request.start_time.replace(tzinfo=None) if request.start_time.tzinfo else request.start_time
            end_time = request.end_time.replace(tzinfo=None) if request.end_time and request.end_time.tzinfo else request.end_time

            attendees_json = json.dumps(request.attendees or [])

            event = await conn.fetchrow(
                """
                INSERT INTO events (
                    user_id,
                    title,
                    description,
                    start_time,
                    end_time,
                    location,
                    category_id,
                    attendees,
                    is_all_day,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                RETURNING
                    id, title, description, start_time, end_time, location,
                    attendees, is_all_day, created_at, updated_at
                """,
                DEFAULT_USER_ID,
                request.title,
                request.description,
                start_time,
                end_time,
                request.location,
                category_id,
                attendees_json,
                request.is_all_day
            )

            logger.info(f"Created event: {event['id']} - {event['title']} at {event['start_time']}")

            return EventResponse(
                id=str(event['id']),
                title=event['title'],
                description=event['description'],
                start_time=event['start_time'],
                end_time=event['end_time'],
                location=event['location'],
                category=request.category,
                attendees=json.loads(event['attendees']) if isinstance(event['attendees'], str) else (event['attendees'] or []),
                is_all_day=event['is_all_day'],
                created_at=event['created_at'],
                updated_at=event['updated_at']
            )

    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


# ============================================================================
# READ Events
# ============================================================================

@router.get("", response_model=EventListResponse)
async def list_events(
    start_date: Optional[datetime] = Query(None, description="Filter events starting after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events ending before this date"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_all_day: Optional[bool] = Query(None, description="Filter all-day events"),
    limit: int = Query(50, ge=1, le=200, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List events with optional filtering.

    Supports filtering by:
    - start_date (events starting after this date)
    - end_date (events ending before this date)
    - category
    - is_all_day
    """
    try:
        pool = await get_db_pool()

        # Build query dynamically based on filters
        where_clauses = []
        params = []
        param_count = 1

        if start_date:
            where_clauses.append(f"e.start_time >= ${param_count}")
            params.append(start_date)
            param_count += 1

        if end_date:
            where_clauses.append(f"e.end_time <= ${param_count}")
            params.append(end_date)
            param_count += 1

        if category:
            where_clauses.append(f"c.name = ${param_count}")
            params.append(category)
            param_count += 1

        if is_all_day is not None:
            where_clauses.append(f"e.is_all_day = ${param_count}")
            params.append(is_all_day)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        async with pool.acquire() as conn:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM events e
                LEFT JOIN categories c ON e.category_id = c.id
                {where_clause}
            """
            total = await conn.fetchval(count_query, *params)

            # Get events
            params.extend([limit, offset])
            query = f"""
                SELECT
                    e.id, e.title, e.description, e.start_time, e.end_time,
                    e.location, e.attendees, e.is_all_day,
                    e.created_at, e.updated_at,
                    c.name as category
                FROM events e
                LEFT JOIN categories c ON e.category_id = c.id
                {where_clause}
                ORDER BY e.start_time ASC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """

            rows = await conn.fetch(query, *params)

            events = [
                EventResponse(
                    id=str(row['id']),
                    title=row['title'],
                    description=row['description'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    category=row['category'],
                    attendees=json.loads(row['attendees']) if isinstance(row['attendees'], str) else (row['attendees'] or []),
                    is_all_day=row['is_all_day'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

            return EventListResponse(
                events=events,
                total=total,
                limit=limit,
                offset=offset
            )

    except Exception as e:
        logger.error(f"Error listing events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")


@router.get("/today", response_model=EventListResponse)
async def get_events_today():
    """Get all events scheduled for today."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    e.id, e.title, e.description, e.start_time, e.end_time,
                    e.location, e.attendees, e.is_all_day,
                    e.created_at, e.updated_at,
                    c.name as category
                FROM events e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE DATE(e.start_time) = CURRENT_DATE
                ORDER BY e.start_time ASC
                """
            )

            events = [
                EventResponse(
                    id=str(row['id']),
                    title=row['title'],
                    description=row['description'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    category=row['category'],
                    attendees=json.loads(row['attendees']) if isinstance(row['attendees'], str) else (row['attendees'] or []),
                    is_all_day=row['is_all_day'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

            return EventListResponse(
                events=events,
                total=len(events),
                limit=len(events),
                offset=0
            )

    except Exception as e:
        logger.error(f"Error getting today's events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get today's events: {str(e)}")


@router.get("/week", response_model=EventListResponse)
async def get_events_week():
    """Get all events scheduled for the next 7 days."""
    try:
        pool = await get_db_pool()
        now = datetime.now()
        week_later = now + timedelta(days=7)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    e.id, e.title, e.description, e.start_time, e.end_time,
                    e.location, e.attendees, e.is_all_day,
                    e.created_at, e.updated_at,
                    c.name as category
                FROM events e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.start_time >= $1 AND e.start_time <= $2
                ORDER BY e.start_time ASC
                """,
                now,
                week_later
            )

            events = [
                EventResponse(
                    id=str(row['id']),
                    title=row['title'],
                    description=row['description'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    category=row['category'],
                    attendees=json.loads(row['attendees']) if isinstance(row['attendees'], str) else (row['attendees'] or []),
                    is_all_day=row['is_all_day'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

            return EventListResponse(
                events=events,
                total=len(events),
                limit=len(events),
                offset=0
            )

    except Exception as e:
        logger.error(f"Error getting week's events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get week's events: {str(e)}")


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str):
    """Get a specific event by ID."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    e.id, e.title, e.description, e.start_time, e.end_time,
                    e.location, e.attendees, e.is_all_day,
                    e.created_at, e.updated_at,
                    c.name as category
                FROM events e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.id = $1
                """,
                event_id
            )

            if not row:
                raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

            return EventResponse(
                id=str(row['id']),
                title=row['title'],
                description=row['description'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                location=row['location'],
                category=row['category'],
                attendees=json.loads(row['attendees']) if isinstance(row['attendees'], str) else (row['attendees'] or []),
                is_all_day=row['is_all_day'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get event: {str(e)}")


# ============================================================================
# UPDATE Event
# ============================================================================

@router.put("/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, request: UpdateEventRequest):
    """
    Update an existing event.

    Only provided fields will be updated.
    """
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Check if event exists
            existing = await conn.fetchrow("SELECT id FROM events WHERE id = $1", event_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

            # Build dynamic UPDATE query
            update_fields = []
            params = []
            param_count = 1

            if request.title is not None:
                update_fields.append(f"title = ${param_count}")
                params.append(request.title)
                param_count += 1

            if request.description is not None:
                update_fields.append(f"description = ${param_count}")
                params.append(request.description)
                param_count += 1

            if request.start_time is not None:
                update_fields.append(f"start_time = ${param_count}")
                params.append(request.start_time)
                param_count += 1

            if request.end_time is not None:
                update_fields.append(f"end_time = ${param_count}")
                params.append(request.end_time)
                param_count += 1

            if request.location is not None:
                update_fields.append(f"location = ${param_count}")
                params.append(request.location)
                param_count += 1

            if request.attendees is not None:
                update_fields.append(f"attendees = ${param_count}")
                params.append(json.dumps(request.attendees))
                param_count += 1

            if request.is_all_day is not None:
                update_fields.append(f"is_all_day = ${param_count}")
                params.append(request.is_all_day)
                param_count += 1

            # Handle category
            if request.category is not None:
                category_row = await conn.fetchrow(
                    "SELECT id FROM categories WHERE name = $1 AND type = 'event'",
                    request.category
                )
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'event', '#10B981')
                        RETURNING id
                        """,
                        request.category
                    )
                update_fields.append(f"category_id = ${param_count}")
                params.append(category_row['id'])
                param_count += 1

            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            # Always update updated_at
            update_fields.append("updated_at = NOW()")

            # Add event_id as last parameter
            params.append(event_id)

            # Execute update
            query = f"""
                UPDATE events
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING
                    id, title, description, start_time, end_time, location,
                    attendees, is_all_day, created_at, updated_at
            """

            event = await conn.fetchrow(query, *params)

            # Get category name
            category_name = None
            if event:
                category_row = await conn.fetchrow(
                    "SELECT name FROM categories WHERE id = (SELECT category_id FROM events WHERE id = $1)",
                    event_id
                )
                if category_row:
                    category_name = category_row['name']

            logger.info(f"Updated event: {event['id']} - {event['title']}")

            return EventResponse(
                id=str(event['id']),
                title=event['title'],
                description=event['description'],
                start_time=event['start_time'],
                end_time=event['end_time'],
                location=event['location'],
                category=category_name,
                attendees=json.loads(event['attendees']) if isinstance(event['attendees'], str) else (event['attendees'] or []),
                is_all_day=event['is_all_day'],
                created_at=event['created_at'],
                updated_at=event['updated_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(e)}")


# ============================================================================
# DELETE Event
# ============================================================================

@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Delete an event."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM events WHERE id = $1",
                event_id
            )

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

            logger.info(f"Deleted event: {event_id}")

            return {"success": True, "message": f"Event {event_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(e)}")
