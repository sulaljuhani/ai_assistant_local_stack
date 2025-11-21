"""
Reminders Router

API endpoints for reminder management operations.
Replaces n8n workflow: 01-create-reminder.json
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from middleware.validation import (
    CreateReminderRequest,
    UpdateReminderRequest,
    SuccessResponse,
    ReminderPriority,
    RecurrencePattern,
)
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
router = APIRouter(prefix="/api/reminders", tags=["reminders"])


# Response models
class ReminderResponse(BaseModel):
    """Reminder response model"""
    id: str
    title: str
    description: Optional[str]
    remind_at: datetime
    priority: int
    category: Optional[str]
    recurrence: str
    is_completed: bool
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ReminderListResponse(BaseModel):
    """Reminder list response model"""
    reminders: List[ReminderResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# CREATE Reminder
# ============================================================================

@router.post("/create", response_model=ReminderResponse)
async def create_reminder(request: CreateReminderRequest):
    """
    Create a new reminder.

    Replaces n8n workflow: 01-create-reminder.json

    Logic:
    1. Validate input (handled by Pydantic, including future datetime check)
    2. Get category ID from database (if category provided)
    3. Insert reminder with parameterized query
    4. Return created reminder
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
                    WHERE name = $1 AND type = 'reminder'
                    LIMIT 1
                    """,
                    request.category
                )

                # If category doesn't exist, create it
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'reminder', '#F59E0B')
                        RETURNING id
                        """,
                        request.category
                    )

                category_id = category_row['id']

            # Insert reminder
            remind_at = request.remind_at.replace(tzinfo=None) if request.remind_at.tzinfo else request.remind_at

            is_recurring = request.recurrence != RecurrencePattern.NONE
            recurrence_rule = request.recurrence.value if request.recurrence != RecurrencePattern.NONE else None

            reminder = await conn.fetchrow(
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
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW(), NOW())
                RETURNING
                    id, title, description, remind_at, priority,
                    is_recurring, recurrence_rule, status, completed_at,
                    created_at, updated_at
                """,
                DEFAULT_USER_ID,
                request.title,
                request.description,
                remind_at,
                request.priority.value,
                category_id,
                is_recurring,
                recurrence_rule
            )

            logger.info(f"Created reminder: {reminder['id']} - {reminder['title']} at {reminder['remind_at']}")

            return ReminderResponse(
                id=str(reminder['id']),
                title=reminder['title'],
                description=reminder['description'],
                remind_at=reminder['remind_at'],
                priority=reminder['priority'],
                category=request.category,
                recurrence=reminder['recurrence_rule'] or RecurrencePattern.NONE,
                is_completed=reminder['status'] == 'completed',
                completed_at=reminder['completed_at'],
                created_at=reminder['created_at'],
                updated_at=reminder['updated_at']
            )

    except Exception as e:
        logger.error(f"Error creating reminder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {str(e)}")


# ============================================================================
# READ Reminders
# ============================================================================

@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[ReminderPriority] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Number of reminders to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List reminders with optional filtering.

    Supports filtering by:
    - is_completed (true/false)
    - priority (0-3)
    - category
    """
    try:
        pool = await get_db_pool()

        # Build query dynamically based on filters
        where_clauses = []
        params = []
        param_count = 1

        if is_completed is not None:
            where_clauses.append(f"r.is_completed = ${param_count}")
            params.append(is_completed)
            param_count += 1

        if priority:
            where_clauses.append(f"r.priority = ${param_count}")
            params.append(priority.value)
            param_count += 1

        if category:
            where_clauses.append(f"c.name = ${param_count}")
            params.append(category)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        async with pool.acquire() as conn:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM reminders r
                LEFT JOIN categories c ON r.category_id = c.id
                {where_clause}
            """
            total = await conn.fetchval(count_query, *params)

            # Get reminders
            params.extend([limit, offset])
            query = f"""
                SELECT
                    r.id, r.title, r.description, r.remind_at, r.priority,
                    r.recurrence_rule, r.status, r.completed_at,
                    r.created_at, r.updated_at,
                    c.name as category
                FROM reminders r
                LEFT JOIN categories c ON r.category_id = c.id
                {where_clause}
                ORDER BY r.remind_at ASC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """

            rows = await conn.fetch(query, *params)

            reminders = [
                ReminderResponse(
                    id=str(row['id']),
                    title=row['title'],
                    description=row['description'],
                    remind_at=row['remind_at'],
                    priority=row['priority'],
                    category=row['category'],
                    recurrence=row['recurrence_rule'] or "none",
                    is_completed=row['status'] == 'completed',
                    completed_at=row['completed_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

            return ReminderListResponse(
                reminders=reminders,
                total=total,
                limit=limit,
                offset=offset
            )

    except Exception as e:
        logger.error(f"Error listing reminders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reminders: {str(e)}")


@router.get("/today", response_model=ReminderListResponse)
async def get_reminders_today():
    """Get all reminders scheduled for today (not completed)."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    r.id, r.title, r.description, r.remind_at, r.priority,
                    r.recurrence_rule, r.status, r.completed_at,
                    r.created_at, r.updated_at,
                    c.name as category
                FROM reminders r
                LEFT JOIN categories c ON r.category_id = c.id
                WHERE DATE(r.remind_at) = CURRENT_DATE
                  AND r.status <> 'completed'
                ORDER BY r.remind_at ASC
                """
            )

            reminders = [
                ReminderResponse(
                    id=str(row['id']),
                    title=row['title'],
                    description=row['description'],
                    remind_at=row['remind_at'],
                    priority=row['priority'],
                    category=row['category'],
                    recurrence=row['recurrence_rule'] or "none",
                    is_completed=row['status'] == 'completed',
                    completed_at=row['completed_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

            return ReminderListResponse(
                reminders=reminders,
                total=len(reminders),
                limit=len(reminders),
                offset=0
            )

    except Exception as e:
        logger.error(f"Error getting today's reminders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get today's reminders: {str(e)}")


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(reminder_id: str):
    """Get a specific reminder by ID."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    r.id, r.title, r.description, r.remind_at, r.priority,
                    r.recurrence_rule, r.status, r.completed_at,
                    r.created_at, r.updated_at,
                    c.name as category
                FROM reminders r
                LEFT JOIN categories c ON r.category_id = c.id
                WHERE r.id = $1
                """,
                reminder_id
            )

            if not row:
                raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")

            return ReminderResponse(
                id=str(row['id']),
                title=row['title'],
                description=row['description'],
                remind_at=row['remind_at'],
                priority=row['priority'],
                category=row['category'],
                recurrence=row['recurrence_rule'] or "none",
                is_completed=row['status'] == 'completed',
                completed_at=row['completed_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reminder {reminder_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get reminder: {str(e)}")


# ============================================================================
# UPDATE Reminder
# ============================================================================

@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(reminder_id: str, request: UpdateReminderRequest):
    """
    Update an existing reminder.

    Only provided fields will be updated.
    """
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Check if reminder exists
            existing = await conn.fetchrow("SELECT id FROM reminders WHERE id = $1", reminder_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")

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

            if request.remind_at is not None:
                update_fields.append(f"remind_at = ${param_count}")
                remind_at = request.remind_at.replace(tzinfo=None) if request.remind_at and request.remind_at.tzinfo else request.remind_at
                params.append(remind_at)
                param_count += 1

            if request.priority is not None:
                update_fields.append(f"priority = ${param_count}")
                params.append(request.priority.value)
                param_count += 1

            if request.recurrence is not None:
                update_fields.append(f"recurrence_rule = ${param_count}")
                params.append(request.recurrence.value)
                param_count += 1

            if request.is_completed is not None:
                update_fields.append(f"status = ${param_count}")
                params.append("completed" if request.is_completed else "pending")
                param_count += 1
                if request.is_completed:
                    update_fields.append("completed_at = NOW()")

            # Handle category
            if request.category is not None:
                category_row = await conn.fetchrow(
                    "SELECT id FROM categories WHERE name = $1 AND type = 'reminder'",
                    request.category
                )
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'reminder', '#F59E0B')
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

            # Add reminder_id as last parameter
            params.append(reminder_id)

            # Execute update
            query = f"""
                UPDATE reminders
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING
                    id, title, description, remind_at, priority,
                    recurrence_rule, status, completed_at,
                    created_at, updated_at
            """

            reminder = await conn.fetchrow(query, *params)

            # Get category name
            category_name = None
            if reminder:
                category_row = await conn.fetchrow(
                    "SELECT name FROM categories WHERE id = (SELECT category_id FROM reminders WHERE id = $1)",
                    reminder_id
                )
                if category_row:
                    category_name = category_row['name']

            logger.info(f"Updated reminder: {reminder['id']} - {reminder['title']}")

            return ReminderResponse(
                id=str(reminder['id']),
                title=reminder['title'],
                description=reminder['description'],
                remind_at=reminder['remind_at'],
                priority=reminder['priority'],
                category=category_name,
                recurrence=reminder['recurrence_rule'] or "none",
                is_completed=reminder['status'] == 'completed',
                completed_at=reminder['completed_at'],
                created_at=reminder['created_at'],
                updated_at=reminder['updated_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reminder {reminder_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update reminder: {str(e)}")


# ============================================================================
# DELETE Reminder
# ============================================================================

@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """Delete a reminder."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM reminders WHERE id = $1",
                reminder_id
            )

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Reminder {reminder_id} not found")

            logger.info(f"Deleted reminder: {reminder_id}")

            return {"success": True, "message": f"Reminder {reminder_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder {reminder_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {str(e)}")
