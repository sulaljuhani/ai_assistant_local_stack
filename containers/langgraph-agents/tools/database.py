"""
Direct database query tools for structured data access.
"""

import json
import re
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger
from config import settings

logger = get_logger(__name__)


def serialize_tool_result(result: Any) -> str:
    """
    Serialize tool results to JSON string for LLM compatibility.

    Some LLM providers (e.g., DeepSeek) require tool results to be strings,
    not complex data structures. This function ensures compatibility.

    Args:
        result: Tool result (can be list, dict, or any JSON-serializable type)

    Returns:
        JSON string representation
    """
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to serialize result: {e}")
        return str(result)


async def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for text using Ollama.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (768 dimensions for nomic-embed-text)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_embed_url}/api/embeddings",
                json={
                    "model": settings.ollama_embed_model,
                    "prompt": text
                }
            )
            result = response.json()
            return result["embedding"]
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return []


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score (0-1, where 1 is identical)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


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


def normalize_due_date(due_date: Optional[str]) -> Optional[datetime]:
    """
    Convert a natural language due date into a datetime object.

    Handles simple phrases (today, tomorrow, in X days, next week) and
    falls back to dateutil.parser for free-form inputs. Returns None if
    parsing fails.
    """
    if not due_date:
        return None

    text = due_date.strip()
    if not text:
        return None

    lower = text.lower()
    now = datetime.utcnow()

    def end_of_day(dt: datetime) -> datetime:
        return dt.replace(hour=17, minute=0, second=0, microsecond=0)

    try:
        # Common quick phrases
        if lower in {"today", "by today", "end of day", "eod", "tonight"}:
            return end_of_day(now)

        if lower in {"tomorrow", "tmr", "tmrw"}:
            return end_of_day(now + timedelta(days=1))

        in_days_match = re.match(r"in\s+(\d+)\s+day[s]?", lower)
        if in_days_match:
            days = int(in_days_match.group(1))
            return end_of_day(now + timedelta(days=days))

        if lower == "next week":
            return end_of_day(now + timedelta(days=7))

        # Fall back to dateutil parsing
        parsed = date_parser.parse(text, fuzzy=True, default=now)
        return parsed
    except Exception as e:
        logger.warning(f"Could not parse due_date '{due_date}': {e}")
        return None


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
    location: str,
    preference: str,
    restaurant_name: Optional[str] = None,
    description: Optional[str] = None,
    meal_type: Optional[str] = None,
    ingredients: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    calories: Optional[int] = None,
    notes: Optional[str] = None,
    consumed_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a new food entry with the updated schema.

    Args:
        user_id: User identifier (UUID string or 'anythingllm')
        food_name: Name/description of food
        location: Where food was eaten ('home' or 'outside')
        preference: User preference ('liked', 'disliked', or 'favorite')
        restaurant_name: Restaurant name (required if location='outside')
        description: Optional description
        meal_type: Optional meal type ('breakfast', 'lunch', 'dinner', 'snack')
        ingredients: Optional list of ingredients
        tags: Optional list of tags
        calories: Optional calorie count
        notes: Optional notes
        consumed_at: Optional timestamp (ISO format), defaults to now

    Returns:
        Created food entry

    Raises:
        ValueError: If input parameters are invalid
    """
    # Normalize user_id (convert 'anythingllm' to default UUID)
    if user_id == 'anythingllm' or not user_id:
        user_id = '00000000-0000-0000-0000-000000000001'

    # Validate and normalize inputs
    location = location.lower() if location else 'home'
    preference = preference.lower() if preference else 'liked'

    if location not in ['home', 'outside']:
        raise ValueError("location must be 'home' or 'outside'")

    if preference not in ['liked', 'disliked', 'favorite']:
        raise ValueError("preference must be 'liked', 'disliked', or 'favorite'")

    if location == 'outside' and not restaurant_name:
        raise ValueError("restaurant_name is required when location='outside'")

    if meal_type and meal_type.lower() not in ['breakfast', 'lunch', 'dinner', 'snack']:
        meal_type = None  # Ignore invalid meal types
    elif meal_type:
        meal_type = meal_type.lower()

    if not food_name or not food_name.strip():
        raise ValueError("food_name is required and cannot be empty")

    pool = await get_db_pool()

    # Convert consumed_at string to datetime object
    if consumed_at:
        if isinstance(consumed_at, str):
            from dateutil import parser
            consumed_at_dt = parser.isoparse(consumed_at)
        else:
            consumed_at_dt = consumed_at
    else:
        consumed_at_dt = datetime.utcnow()

    query = """
        INSERT INTO food_log (
            user_id, food_name, location, preference, restaurant_name,
            description, meal_type, ingredients, tags, calories, notes, consumed_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id, user_id, food_name, location, preference, restaurant_name,
                  description, meal_type, ingredients, tags, calories, notes,
                  consumed_at, created_at
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id, food_name, location, preference, restaurant_name,
                description, meal_type, ingredients or [], tags or [],
                calories, notes, consumed_at_dt
            )
            result = dict(row)
            logger.info(f"Logged food entry: {food_name} at {location}")
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
) -> str:
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
            return serialize_tool_result(results)
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
) -> str:
    """
    Create a new task (checks for duplicates first).

    Args:
        user_id: User identifier (UUID string or 'anythingllm')
        title: Task title
        description: Task description
        priority: Priority level (low, medium, high, urgent) or integer (0-4)
        due_date: Due date (natural language like "tomorrow" or ISO string)

    Returns:
        JSON string with created task or duplicate notification

    Raises:
        ValueError: If input parameters are invalid
    """
    # Normalize user_id (convert 'anythingllm' to default UUID)
    if user_id == 'anythingllm' or not user_id:
        user_id = '00000000-0000-0000-0000-000000000001'

    # Parse natural-language due dates
    normalized_due_date = normalize_due_date(due_date)
    if due_date and not normalized_due_date:
        logger.info(f"Unable to parse due date '{due_date}', leaving unset")

    # Convert priority string to integer if needed
    priority_map = {
        'none': 0,
        'low': 1,
        'medium': 2,
        'high': 3,
        'urgent': 4
    }

    # Handle both string and integer priorities
    if isinstance(priority, str):
        priority_lower = priority.lower()
        if priority_lower in priority_map:
            priority_int = priority_map[priority_lower]
        elif priority.isdigit():
            priority_int = int(priority)
        else:
            # Default to medium if invalid
            priority_int = 2
    else:
        priority_int = int(priority) if priority else 2

    # Clamp priority to valid range (0-4)
    priority_int = max(0, min(4, priority_int))

    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Step 1: Check for exact title match (fast path)
            exact_match_check = """
                SELECT id, title, description, status, priority, due_date, created_at
                FROM tasks
                WHERE user_id = $1
                  AND LOWER(title) = LOWER($2)
                  AND status NOT IN ('completed', 'deleted')
                LIMIT 1
            """

            exact_match = await conn.fetchrow(exact_match_check, user_id, title)

            if exact_match:
                logger.info(f"Exact duplicate task found: {title}")
                result = {
                    "duplicate": True,
                    "similarity": 1.0,
                    "match_type": "exact",
                    "message": f"A task with the title '{title}' already exists",
                    "existing_task": dict(exact_match)
                }
                return serialize_tool_result(result)

            # Step 2: Check for semantic similarity using embeddings
            # Get recent non-completed tasks for similarity comparison
            recent_tasks_query = """
                SELECT id, title, description, status, priority, due_date, created_at
                FROM tasks
                WHERE user_id = $1
                  AND status NOT IN ('completed', 'deleted')
                  AND created_at > NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 20
            """

            recent_tasks = await conn.fetch(recent_tasks_query, user_id)
            logger.info(f"Checking similarity against {len(recent_tasks)} recent tasks")

            if recent_tasks:
                # Get embedding for new task
                new_task_text = f"{title}. {description or ''}"
                logger.info(f"Getting embedding for new task: {new_task_text[:50]}...")
                new_embedding = await get_embedding(new_task_text)
                logger.info(f"New task embedding: {len(new_embedding) if new_embedding else 0} dimensions")

                if new_embedding:
                    # Compare with existing tasks
                    for task in recent_tasks:
                        existing_text = f"{task['title']}. {task['description'] or ''}"
                        existing_embedding = await get_embedding(existing_text)

                        if existing_embedding:
                            similarity = cosine_similarity(new_embedding, existing_embedding)
                            logger.info(f"Comparing with '{task['title']}': similarity = {similarity:.3f}")

                            # Consider it a duplicate if similarity > 0.80 (80%)
                            if similarity > 0.80:
                                logger.info(f"DUPLICATE DETECTED: {task['title']} (similarity: {similarity:.2f})")
                                result = {
                                    "duplicate": True,
                                    "similarity": round(similarity, 2),
                                    "match_type": "similar",
                                    "message": f"A very similar task already exists: '{task['title']}' (similarity: {int(similarity*100)}%)",
                                    "existing_task": dict(task)
                                }
                                return serialize_tool_result(result)
                else:
                    logger.warning("Failed to get embedding for new task")

            # No duplicate found, create the task
            insert_query = """
                INSERT INTO tasks (user_id, title, description, priority, due_date, status)
                VALUES ($1, $2, $3, $4, $5, 'todo')
                RETURNING id, user_id, title, description, status, priority, due_date, created_at
            """

            row = await conn.fetchrow(
                insert_query,
                user_id, title, description, priority_int, normalized_due_date
            )
            result = {
                "duplicate": False,
                "message": "Task created successfully",
                "task": dict(row)
            }
            logger.info(f"Created task: {title} with priority {priority_int}")
            return serialize_tool_result(result)

    except ValueError as e:
        logger.error(f"Validation error in create_task: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise


@tool
async def update_task(
    task_id: str,
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing task.

    Args:
        task_id: Task ID (UUID string)
        user_id: User identifier
        status: New status (pending, in_progress, completed, etc.)
        priority: New priority (low, medium, high)
        due_date: New due date (natural language or ISO string)

    Returns:
        Updated task

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    if not task_id:
        raise ValueError("task_id is required")
    validate_task_status(status)
    validate_priority(priority)

    if status is None and priority is None and due_date is None:
        raise ValueError("At least one of status, priority, or due_date must be provided")

    normalized_due_date = normalize_due_date(due_date) if due_date is not None else None
    if due_date and normalized_due_date is None:
        logger.info(f"Unable to parse due date '{due_date}', leaving unchanged")

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

    if due_date is not None and normalized_due_date is not None:
        param_count += 1
        params.append(normalized_due_date)
        updates.append(f"due_date = ${param_count}")

    if not updates:
        raise ValueError("No valid updates provided (check status/priority/due_date values)")

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
) -> str:
    """
    Create a calendar event (checks for duplicates first).

    Args:
        user_id: User identifier (UUID string or 'anythingllm')
        title: Event title
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        description: Event description
        location: Event location

    Returns:
        JSON string with created event or duplicate notification

    Raises:
        ValueError: If input parameters are invalid
    """
    # Normalize user_id (convert 'anythingllm' to default UUID)
    if user_id == 'anythingllm' or not user_id:
        user_id = '00000000-0000-0000-0000-000000000001'

    # Validate inputs
    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")

    if not start_time or not end_time:
        raise ValueError("start_time and end_time are required")

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Step 1: Check for exact title match with overlapping time (fast path)
            exact_match_check = """
                SELECT id, title, description, start_time, end_time, location, created_at
                FROM events
                WHERE user_id = $1
                  AND LOWER(title) = LOWER($2)
                  AND (
                    -- Check if times overlap
                    (start_time <= $3 AND end_time >= $3) OR  -- New start within existing
                    (start_time <= $4 AND end_time >= $4) OR  -- New end within existing
                    (start_time >= $3 AND end_time <= $4)     -- Existing within new
                  )
                LIMIT 1
            """

            exact_match = await conn.fetchrow(exact_match_check, user_id, title, start_time, end_time)

            if exact_match:
                logger.info(f"Exact duplicate event found: {title}")
                result = {
                    "duplicate": True,
                    "similarity": 1.0,
                    "match_type": "exact",
                    "message": f"An event with the title '{title}' already exists at this time",
                    "existing_event": dict(exact_match)
                }
                return serialize_tool_result(result)

            # Step 2: Check for semantically similar events around the same time
            # Get events within ±7 days of the requested time
            similar_events_query = """
                SELECT id, title, description, start_time, end_time, location, created_at
                FROM events
                WHERE user_id = $1
                  AND start_time BETWEEN $2::timestamp - INTERVAL '7 days'
                                     AND $2::timestamp + INTERVAL '7 days'
                ORDER BY start_time ASC
                LIMIT 20
            """

            nearby_events = await conn.fetch(similar_events_query, user_id, start_time)

            if nearby_events:
                # Get embedding for new event
                new_event_text = f"{title}. {description or ''}. Location: {location or 'none'}"
                new_embedding = await get_embedding(new_event_text)

                if new_embedding:
                    # Compare with existing events
                    for event in nearby_events:
                        existing_text = f"{event['title']}. {event['description'] or ''}. Location: {event['location'] or 'none'}"
                        existing_embedding = await get_embedding(existing_text)

                        if existing_embedding:
                            similarity = cosine_similarity(new_embedding, existing_embedding)
                            logger.info(f"Comparing with '{event['title']}': similarity = {similarity:.3f}")

                            # Consider it a duplicate if similarity > 0.80 (80%)
                            if similarity > 0.80:
                                logger.info(f"DUPLICATE EVENT DETECTED: {event['title']} (similarity: {similarity:.2f})")
                                result = {
                                    "duplicate": True,
                                    "similarity": round(similarity, 2),
                                    "match_type": "similar",
                                    "message": f"A very similar event already exists: '{event['title']}' on {event['start_time'].strftime('%Y-%m-%d %H:%M')} (similarity: {int(similarity*100)}%)",
                                    "existing_event": dict(event)
                                }
                                return serialize_tool_result(result)

            # No duplicate found, create the event
            insert_query = """
                INSERT INTO events (user_id, title, description, start_time, end_time, location)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, title, description, start_time, end_time, location, created_at
            """

            row = await conn.fetchrow(
                insert_query,
                user_id, title, description, start_time, end_time, location
            )
            result = {
                "duplicate": False,
                "message": "Event created successfully",
                "event": dict(row)
            }
            logger.info(f"Created event: {title}")
            return serialize_tool_result(result)

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
