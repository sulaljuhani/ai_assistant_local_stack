"""
Direct database query tools for structured data access.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_days_ago(days_ago: Optional[int]) -> None:
    """Validate days_ago parameter."""
    if days_ago is not None and (days_ago < 1 or days_ago > 365):
        raise ValueError("days_ago must be between 1 and 365")


def validate_limit(limit: int) -> None:
    """Validate limit parameter."""
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")


def validate_rating(rating: Optional[int]) -> None:
    """Validate rating parameter."""
    if rating is not None and (rating < 1 or rating > 5):
        raise ValueError("rating must be between 1 and 5")


def validate_food_type(food_type: Optional[str]) -> None:
    """Validate food_type parameter."""
    valid_types = ['breakfast', 'lunch', 'dinner', 'snack']
    if food_type is not None and food_type not in valid_types:
        raise ValueError(f"food_type must be one of: {', '.join(valid_types)}")


def validate_task_status(status: Optional[str]) -> None:
    """Validate task status parameter."""
    valid_statuses = ['pending', 'in_progress', 'waiting', 'done', 'completed', 'cancelled']
    if status is not None and status not in valid_statuses:
        raise ValueError(f"status must be one of: {', '.join(valid_statuses)}")


def validate_priority(priority: Optional[str]) -> None:
    """Validate priority parameter."""
    valid_priorities = ['low', 'medium', 'high']
    if priority is not None and priority not in valid_priorities:
        raise ValueError(f"priority must be one of: {', '.join(valid_priorities)}")


# ============================================================================
# FOOD TOOLS
# ============================================================================

@tool
async def search_food_log(
    user_id: str,
    days_ago: Optional[int] = 7,
    min_rating: Optional[int] = None,
    food_type: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search food log entries with filters.

    Args:
        user_id: User identifier
        days_ago: Number of days to look back (default 7, max 365)
        min_rating: Minimum rating filter (1-5)
        food_type: Filter by food type (breakfast, lunch, dinner, snack)
        limit: Maximum results to return (max 100)

    Returns:
        List of food log entries

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_days_ago(days_ago)
    validate_limit(limit)
    validate_rating(min_rating)
    validate_food_type(food_type)

    pool = await get_db_pool()

    # Build query dynamically with parameterized queries
    query = """
        SELECT
            id, user_id, food_name, food_type, rating, notes,
            logged_at, created_at
        FROM food_log
        WHERE user_id = $1
    """
    params = [user_id]
    param_count = 1

    if days_ago:
        param_count += 1
        params.append(days_ago)
        # FIX: Use parameterized interval multiplication instead of string interpolation
        query += f" AND logged_at >= NOW() - INTERVAL '1 day' * ${param_count}"

    if min_rating:
        param_count += 1
        params.append(min_rating)
        query += f" AND rating >= ${param_count}"

    if food_type:
        param_count += 1
        params.append(food_type)
        query += f" AND food_type = ${param_count}"

    # Use parameterized limit for consistency
    param_count += 1
    params.append(limit)
    query += f" ORDER BY logged_at DESC LIMIT ${param_count}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} food log entries")
            return results
    except ValueError as e:
        # Re-raise validation errors
        logger.error(f"Validation error in search_food_log: {e}")
        raise
    except Exception as e:
        logger.error(f"Error searching food log: {e}")
        raise


@tool
async def log_food_entry(
    user_id: str,
    food_name: str,
    food_type: str,
    rating: Optional[int] = None,
    notes: Optional[str] = None,
    logged_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a new food entry.

    Args:
        user_id: User identifier
        food_name: Name/description of food
        food_type: Type (breakfast, lunch, dinner, snack)
        rating: Optional rating 1-5
        notes: Optional notes
        logged_at: Optional timestamp (ISO format), defaults to now

    Returns:
        Created food entry

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_food_type(food_type)
    validate_rating(rating)

    if not food_name or not food_name.strip():
        raise ValueError("food_name is required and cannot be empty")

    pool = await get_db_pool()

    if not logged_at:
        logged_at = datetime.utcnow().isoformat()

    query = """
        INSERT INTO food_log (user_id, food_name, food_type, rating, notes, logged_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, user_id, food_name, food_type, rating, notes, logged_at, created_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id, food_name, food_type, rating, notes, logged_at
            )
            result = dict(row)
            logger.info(f"Logged food entry: {food_name}")
            return result
    except ValueError as e:
        logger.error(f"Validation error in log_food_entry: {e}")
        raise
    except Exception as e:
        logger.error(f"Error logging food: {e}")
        raise


@tool
async def update_food_entry(
    entry_id: int,
    user_id: str,
    rating: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing food entry.

    Args:
        entry_id: Food entry ID
        user_id: User identifier (for authorization)
        rating: New rating (1-5)
        notes: New notes

    Returns:
        Updated food entry

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_rating(rating)

    if rating is None and notes is None:
        raise ValueError("At least one of rating or notes must be provided")

    pool = await get_db_pool()

    # Build update query dynamically
    updates = []
    params = [entry_id, user_id]
    param_count = 2

    if rating is not None:
        param_count += 1
        params.append(rating)
        updates.append(f"rating = ${param_count}")

    if notes is not None:
        param_count += 1
        params.append(notes)
        updates.append(f"notes = ${param_count}")

    query = f"""
        UPDATE food_log
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = $1 AND user_id = $2
        RETURNING id, user_id, food_name, food_type, rating, notes, logged_at, updated_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                result = dict(row)
                logger.info(f"Updated food entry {entry_id}")
                return result
            else:
                raise ValueError("Entry not found or unauthorized")
    except ValueError as e:
        logger.error(f"Validation error in update_food_entry: {e}")
        raise
    except Exception as e:
        logger.error(f"Error updating food entry: {e}")
        raise


@tool
async def get_food_by_rating(
    user_id: str,
    min_rating: int = 4,
    days_ago: int = 30,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get highly rated foods from recent history.

    Args:
        user_id: User identifier
        min_rating: Minimum rating (default 4)
        days_ago: Days to look back (default 30)
        limit: Maximum results

    Returns:
        List of highly rated food entries
    """
    return await search_food_log(
        user_id=user_id,
        days_ago=days_ago,
        min_rating=min_rating,
        limit=limit
    )


@tool
async def analyze_food_patterns(
    user_id: str,
    days_ago: int = 30
) -> Dict[str, Any]:
    """
    Analyze food patterns and statistics.

    Args:
        user_id: User identifier
        days_ago: Days to analyze (max 365)

    Returns:
        Pattern analysis with counts, favorites, etc.

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_days_ago(days_ago)

    pool = await get_db_pool()

    # FIX: Use parameterized query instead of string formatting
    query = """
        WITH recent_foods AS (
            SELECT * FROM food_log
            WHERE user_id = $1 AND logged_at >= NOW() - INTERVAL '1 day' * $2
        )
        SELECT
            COUNT(*) as total_entries,
            AVG(rating) as avg_rating,
            COUNT(DISTINCT DATE(logged_at)) as days_logged,
            COUNT(CASE WHEN food_type = 'breakfast' THEN 1 END) as breakfast_count,
            COUNT(CASE WHEN food_type = 'lunch' THEN 1 END) as lunch_count,
            COUNT(CASE WHEN food_type = 'dinner' THEN 1 END) as dinner_count,
            COUNT(CASE WHEN food_type = 'snack' THEN 1 END) as snack_count,
            COUNT(CASE WHEN rating >= 4 THEN 1 END) as high_rated_count
        FROM recent_foods
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id, days_ago)
            result = dict(row) if row else {}
            logger.info(f"Analyzed food patterns for {days_ago} days")
            return result
    except ValueError as e:
        logger.error(f"Validation error in analyze_food_patterns: {e}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing food patterns: {e}")
        raise


# ============================================================================
# TASK TOOLS
# ============================================================================

@tool
async def search_tasks(
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search tasks with filters.

    Args:
        user_id: User identifier
        status: Filter by status (pending, in_progress, completed, etc.)
        priority: Filter by priority (low, medium, high)
        limit: Maximum results (max 100)

    Returns:
        List of tasks

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_task_status(status)
    validate_priority(priority)
    validate_limit(limit)

    pool = await get_db_pool()

    query = """
        SELECT
            id, user_id, title, description, status, priority,
            due_date, created_at, updated_at, completed_at
        FROM tasks
        WHERE user_id = $1
    """
    params = [user_id]
    param_count = 1

    if status:
        param_count += 1
        params.append(status)
        query += f" AND status = ${param_count}"

    if priority:
        param_count += 1
        params.append(priority)
        query += f" AND priority = ${param_count}"

    # Use parameterized limit for consistency
    param_count += 1
    params.append(limit)
    query += f" ORDER BY priority DESC, due_date ASC LIMIT ${param_count}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} tasks")
            return results
    except ValueError as e:
        logger.error(f"Validation error in search_tasks: {e}")
        raise
    except Exception as e:
        logger.error(f"Error searching tasks: {e}")
        raise


@tool
async def create_task(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new task.

    Args:
        user_id: User identifier
        title: Task title
        description: Task description
        priority: Priority level (low, medium, high)
        due_date: Due date (ISO format)

    Returns:
        Created task

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_priority(priority)

    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")

    pool = await get_db_pool()

    query = """
        INSERT INTO tasks (user_id, title, description, priority, due_date, status)
        VALUES ($1, $2, $3, $4, $5, 'pending')
        RETURNING id, user_id, title, description, status, priority, due_date, created_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id, title, description, priority, due_date
            )
            result = dict(row)
            logger.info(f"Created task: {title}")
            return result
    except ValueError as e:
        logger.error(f"Validation error in create_task: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise


@tool
async def update_task(
    task_id: int,
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing task.

    Args:
        task_id: Task ID
        user_id: User identifier
        status: New status (pending, in_progress, completed, etc.)
        priority: New priority (low, medium, high)
        due_date: New due date (ISO format)

    Returns:
        Updated task

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_task_status(status)
    validate_priority(priority)

    if status is None and priority is None and due_date is None:
        raise ValueError("At least one of status, priority, or due_date must be provided")

    pool = await get_db_pool()

    updates = []
    params = [task_id, user_id]
    param_count = 2

    if status is not None:
        param_count += 1
        params.append(status)
        updates.append(f"status = ${param_count}")
        if status == "completed":
            updates.append("completed_at = NOW()")

    if priority is not None:
        param_count += 1
        params.append(priority)
        updates.append(f"priority = ${param_count}")

    if due_date is not None:
        param_count += 1
        params.append(due_date)
        updates.append(f"due_date = ${param_count}")

    query = f"""
        UPDATE tasks
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = $1 AND user_id = $2
        RETURNING id, user_id, title, status, priority, due_date, updated_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                result = dict(row)
                logger.info(f"Updated task {task_id}")
                return result
            else:
                raise ValueError("Task not found or unauthorized")
    except ValueError as e:
        logger.error(f"Validation error in update_task: {e}")
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise


@tool
async def get_tasks_by_priority(
    user_id: str,
    priority: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get tasks by priority level."""
    return await search_tasks(user_id=user_id, priority=priority, status="pending", limit=limit)


@tool
async def get_tasks_due_soon(
    user_id: str,
    days: int = 7,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get tasks due within the next N days.

    Args:
        user_id: User identifier
        days: Number of days ahead to check (max 365)
        limit: Maximum results (max 100)

    Returns:
        List of upcoming tasks

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_days_ago(days)  # Reuse validation (same logic)
    validate_limit(limit)

    pool = await get_db_pool()

    # FIX: Use parameterized query instead of string formatting
    query = """
        SELECT
            id, user_id, title, description, status, priority,
            due_date, created_at
        FROM tasks
        WHERE user_id = $1
            AND status != 'completed'
            AND due_date IS NOT NULL
            AND due_date <= NOW() + INTERVAL '1 day' * $2
        ORDER BY due_date ASC
        LIMIT $3
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, days, limit)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} tasks due soon")
            return results
    except ValueError as e:
        logger.error(f"Validation error in get_tasks_due_soon: {e}")
        raise
    except Exception as e:
        logger.error(f"Error getting tasks due soon: {e}")
        raise


# ============================================================================
# EVENT TOOLS
# ============================================================================

@tool
async def search_events(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search calendar events.

    Args:
        user_id: User identifier
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        limit: Maximum results (max 100)

    Returns:
        List of events

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    validate_limit(limit)

    pool = await get_db_pool()

    query = """
        SELECT
            id, user_id, title, description, start_time, end_time,
            location, created_at
        FROM events
        WHERE user_id = $1
    """
    params = [user_id]
    param_count = 1

    if start_date:
        param_count += 1
        params.append(start_date)
        query += f" AND start_time >= ${param_count}"

    if end_date:
        param_count += 1
        params.append(end_date)
        query += f" AND start_time <= ${param_count}"

    # Use parameterized limit for consistency
    param_count += 1
    params.append(limit)
    query += f" ORDER BY start_time ASC LIMIT ${param_count}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} events")
            return results
    except ValueError as e:
        logger.error(f"Validation error in search_events: {e}")
        raise
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise


@tool
async def create_event(
    user_id: str,
    title: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a calendar event.

    Args:
        user_id: User identifier
        title: Event title
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        description: Event description
        location: Event location

    Returns:
        Created event

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")

    if not start_time or not end_time:
        raise ValueError("start_time and end_time are required")

    pool = await get_db_pool()

    query = """
        INSERT INTO events (user_id, title, description, start_time, end_time, location)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, user_id, title, description, start_time, end_time, location, created_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id, title, description, start_time, end_time, location
            )
            result = dict(row)
            logger.info(f"Created event: {title}")
            return result
    except ValueError as e:
        logger.error(f"Validation error in create_event: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise


@tool
async def get_events_today(user_id: str) -> List[Dict[str, Any]]:
    """Get today's events."""
    today = datetime.now().date().isoformat()
    tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
    return await search_events(user_id=user_id, start_date=today, end_date=tomorrow)


@tool
async def get_events_week(user_id: str) -> List[Dict[str, Any]]:
    """Get this week's events."""
    today = datetime.now().date().isoformat()
    next_week = (datetime.now().date() + timedelta(days=7)).isoformat()
    return await search_events(user_id=user_id, start_date=today, end_date=next_week)


@tool
async def check_time_conflicts(
    user_id: str,
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """
    Check if a time slot has conflicts with existing events.

    Args:
        user_id: User identifier
        start_time: Proposed start time (ISO format)
        end_time: Proposed end time (ISO format)

    Returns:
        Conflict information with list of conflicting events
    """
    pool = await get_db_pool()

    query = """
        SELECT
            id, title, start_time, end_time
        FROM events
        WHERE user_id = $1
            AND (
                (start_time <= $2 AND end_time > $2)  -- Starts before, ends during
                OR (start_time < $3 AND end_time >= $3)  -- Starts during, ends after
                OR (start_time >= $2 AND end_time <= $3)  -- Completely within
            )
        ORDER BY start_time
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, start_time, end_time)
            conflicts = [dict(row) for row in rows]
            result = {
                "has_conflicts": len(conflicts) > 0,
                "conflict_count": len(conflicts),
                "conflicts": conflicts
            }
            logger.info(f"Found {len(conflicts)} time conflicts")
            return result
    except Exception as e:
        logger.error(f"Error checking time conflicts: {e}")
        return {"error": str(e)}
