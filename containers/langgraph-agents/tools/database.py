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
        days_ago: Number of days to look back (default 7)
        min_rating: Minimum rating filter (1-5)
        food_type: Filter by food type (breakfast, lunch, dinner, snack)
        limit: Maximum results to return

    Returns:
        List of food log entries
    """
    pool = await get_db_pool()

    # Build query dynamically
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
        query += f" AND logged_at >= NOW() - INTERVAL '{days_ago} days'"

    if min_rating:
        param_count += 1
        params.append(min_rating)
        query += f" AND rating >= ${param_count}"

    if food_type:
        param_count += 1
        params.append(food_type)
        query += f" AND food_type = ${param_count}"

    query += f" ORDER BY logged_at DESC LIMIT {limit}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} food log entries")
            return results
    except Exception as e:
        logger.error(f"Error searching food log: {e}")
        return []


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
    """
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
    except Exception as e:
        logger.error(f"Error logging food: {e}")
        return {"error": str(e)}


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
        rating: New rating
        notes: New notes

    Returns:
        Updated food entry
    """
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

    if not updates:
        return {"error": "No updates provided"}

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
                return {"error": "Entry not found or unauthorized"}
    except Exception as e:
        logger.error(f"Error updating food entry: {e}")
        return {"error": str(e)}


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
        days_ago: Days to analyze

    Returns:
        Pattern analysis with counts, favorites, etc.
    """
    pool = await get_db_pool()

    query = """
        WITH recent_foods AS (
            SELECT * FROM food_log
            WHERE user_id = $1 AND logged_at >= NOW() - INTERVAL '{days} days'
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
    """.format(days=days_ago)

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            result = dict(row) if row else {}
            logger.info(f"Analyzed food patterns for {days_ago} days")
            return result
    except Exception as e:
        logger.error(f"Error analyzing food patterns: {e}")
        return {"error": str(e)}


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
        status: Filter by status (pending, in_progress, completed)
        priority: Filter by priority (low, medium, high)
        limit: Maximum results

    Returns:
        List of tasks
    """
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

    query += f" ORDER BY priority DESC, due_date ASC LIMIT {limit}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} tasks")
            return results
    except Exception as e:
        logger.error(f"Error searching tasks: {e}")
        return []


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
    """
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
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {"error": str(e)}


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
        status: New status
        priority: New priority
        due_date: New due date

    Returns:
        Updated task
    """
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

    if not updates:
        return {"error": "No updates provided"}

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
                return {"error": "Task not found or unauthorized"}
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return {"error": str(e)}


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
        days: Number of days ahead to check
        limit: Maximum results

    Returns:
        List of upcoming tasks
    """
    pool = await get_db_pool()

    query = """
        SELECT
            id, user_id, title, description, status, priority,
            due_date, created_at
        FROM tasks
        WHERE user_id = $1
            AND status != 'completed'
            AND due_date IS NOT NULL
            AND due_date <= NOW() + INTERVAL '{days} days'
        ORDER BY due_date ASC
        LIMIT {limit}
    """.format(days=days, limit=limit)

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} tasks due soon")
            return results
    except Exception as e:
        logger.error(f"Error getting tasks due soon: {e}")
        return []


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
        limit: Maximum results

    Returns:
        List of events
    """
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

    query += f" ORDER BY start_time ASC LIMIT {limit}"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info(f"Found {len(results)} events")
            return results
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        return []


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
    """
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
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return {"error": str(e)}


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
