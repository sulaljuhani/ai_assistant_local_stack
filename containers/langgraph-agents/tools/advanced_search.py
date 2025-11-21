"""
Advanced search and filtering across tasks, events, and reminders.

Utilizes PostgreSQL full-text search and advanced querying.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def unified_search(
    query: str,
    user_id: str = USER_ID,
    search_in: Optional[List[str]] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search across tasks, events, and reminders using full-text search.

    Similar to Atlas's unified search capability.

    Args:
        query: Search query text
        user_id: User identifier
        search_in: List of types to search (tasks, events, reminders). Default: all
        limit: Maximum results per type

    Returns:
        Search results grouped by type
    """
    pool = await get_db_pool()

    if search_in is None:
        search_in = ["tasks", "events", "reminders"]

    results = {}

    try:
        async with pool.acquire() as conn:
            # Search tasks
            if "tasks" in search_in:
                tasks = await conn.fetch(
                    """
                    SELECT id, title, description, status, priority, due_date, tags,
                           ts_rank(
                               to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(notes, '')),
                               plainto_tsquery('english', $1)
                           ) as rank
                    FROM tasks
                    WHERE user_id = $2
                      AND to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(notes, ''))
                          @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, priority DESC, due_date NULLS LAST
                    LIMIT $3
                    """,
                    query, user_id, limit
                )
                results["tasks"] = [dict(t) for t in tasks]

            # Search events
            if "events" in search_in:
                events = await conn.fetch(
                    """
                    SELECT id, title, description, start_time, end_time, location,
                           ts_rank(
                               to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, '')),
                               plainto_tsquery('english', $1)
                           ) as rank
                    FROM events
                    WHERE user_id = $2
                      AND to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, ''))
                          @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, start_time DESC
                    LIMIT $3
                    """,
                    query, user_id, limit
                )
                results["events"] = [dict(e) for e in events]

            # Search reminders
            if "reminders" in search_in:
                reminders = await conn.fetch(
                    """
                    SELECT id, title, description, remind_at, priority,
                           ts_rank(
                               to_tsvector('english', title || ' ' || COALESCE(description, '')),
                               plainto_tsquery('english', $1)
                           ) as rank
                    FROM reminders
                    WHERE user_id = $2
                      AND to_tsvector('english', title || ' ' || COALESCE(description, ''))
                          @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, remind_at DESC
                    LIMIT $3
                    """,
                    query, user_id, limit
                )
                results["reminders"] = [dict(r) for r in reminders]

            total_results = sum(len(v) for v in results.values())
            logger.info(f"Unified search for '{query}': {total_results} results")

            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": total_results
            }

    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        return {"success": False, "error": str(e)}


@tool
async def search_by_tags(
    tags: List[str],
    match_all: bool = False,
    user_id: str = USER_ID,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search tasks by tags.

    Args:
        tags: List of tags to search for
        match_all: If True, tasks must have all tags. If False, tasks with any tag.
        user_id: User identifier
        limit: Maximum results

    Returns:
        List of tasks matching tag criteria
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            if match_all:
                # Task must have all specified tags
                query = """
                    SELECT id, title, status, priority, due_date, tags
                    FROM tasks
                    WHERE user_id = $1
                      AND tags @> $2
                    ORDER BY priority DESC, due_date NULLS LAST
                    LIMIT $3
                """
            else:
                # Task must have at least one tag
                query = """
                    SELECT id, title, status, priority, due_date, tags
                    FROM tasks
                    WHERE user_id = $1
                      AND tags && $2
                    ORDER BY priority DESC, due_date NULLS LAST
                    LIMIT $3
                """

            tasks = await conn.fetch(query, user_id, tags, limit)

            logger.info(f"Found {len(tasks)} tasks with tags {tags} (match_all={match_all})")
            return [dict(t) for t in tasks]

    except Exception as e:
        logger.error(f"Error searching by tags: {e}")
        return []


@tool
async def advanced_task_filter(
    user_id: str = USER_ID,
    status: Optional[List[str]] = None,
    priority_min: Optional[int] = None,
    priority_max: Optional[int] = None,
    has_due_date: Optional[bool] = None,
    overdue_only: bool = False,
    has_dependencies: Optional[bool] = None,
    project: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Advanced multi-criteria task filtering.

    Args:
        user_id: User identifier
        status: List of statuses to include
        priority_min: Minimum priority (0-4)
        priority_max: Maximum priority (0-4)
        has_due_date: True=only with due date, False=only without
        overdue_only: True to show only overdue tasks
        has_dependencies: True=only with dependencies, False=only without
        project: Filter by project name
        tags: Filter by tags (any match)
        limit: Maximum results

    Returns:
        List of tasks matching all criteria
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Build dynamic query
            conditions = ["user_id = $1"]
            params = [user_id]
            param_num = 2

            if status:
                conditions.append(f"status = ANY(${param_num})")
                params.append(status)
                param_num += 1

            if priority_min is not None:
                conditions.append(f"priority >= ${param_num}")
                params.append(priority_min)
                param_num += 1

            if priority_max is not None:
                conditions.append(f"priority <= ${param_num}")
                params.append(priority_max)
                param_num += 1

            if has_due_date is not None:
                if has_due_date:
                    conditions.append("due_date IS NOT NULL")
                else:
                    conditions.append("due_date IS NULL")

            if overdue_only:
                conditions.append("due_date < NOW()")
                conditions.append("status NOT IN ('done', 'cancelled')")

            if has_dependencies is not None:
                if has_dependencies:
                    conditions.append("depends_on IS NOT NULL AND array_length(depends_on, 1) > 0")
                else:
                    conditions.append("(depends_on IS NULL OR array_length(depends_on, 1) = 0)")

            if project:
                conditions.append(f"project = ${param_num}")
                params.append(project)
                param_num += 1

            if tags:
                conditions.append(f"tags && ${param_num}")
                params.append(tags)
                param_num += 1

            query = f"""
                SELECT id, title, description, status, priority, due_date,
                       project, tags, depends_on, created_at
                FROM tasks
                WHERE {' AND '.join(conditions)}
                ORDER BY priority DESC, due_date NULLS LAST
                LIMIT ${param_num}
            """
            params.append(limit)

            tasks = await conn.fetch(query, *params)

            logger.info(f"Advanced filter found {len(tasks)} tasks")
            return [dict(t) for t in tasks]

    except Exception as e:
        logger.error(f"Error in advanced filter: {e}")
        return []


@tool
async def get_task_statistics(
    user_id: str = USER_ID,
    project: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about tasks.

    Args:
        user_id: User identifier
        project: Optional project filter

    Returns:
        Statistics including counts by status, priority, tags, etc.
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            project_filter = "AND project = $2" if project else ""
            params = [user_id, project] if project else [user_id]

            # Status counts
            status_counts = await conn.fetch(
                f"""
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE user_id = $1 {project_filter}
                GROUP BY status
                """,
                *params
            )

            # Priority distribution
            priority_counts = await conn.fetch(
                f"""
                SELECT priority, COUNT(*) as count
                FROM tasks
                WHERE user_id = $1 {project_filter}
                GROUP BY priority
                ORDER BY priority DESC
                """,
                *params
            )

            # Tag frequency
            tag_counts = await conn.fetch(
                f"""
                SELECT unnest(tags) as tag, COUNT(*) as count
                FROM tasks
                WHERE user_id = $1 {project_filter} AND tags IS NOT NULL
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 20
                """,
                *params
            )

            # Overdue count
            overdue = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM tasks
                WHERE user_id = $1 {project_filter}
                  AND due_date < NOW()
                  AND status NOT IN ('done', 'cancelled')
                """,
                *params
            )

            # Due soon (next 7 days)
            due_soon = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM tasks
                WHERE user_id = $1 {project_filter}
                  AND due_date BETWEEN NOW() AND NOW() + INTERVAL '7 days'
                  AND status NOT IN ('done', 'cancelled')
                """,
                *params
            )

            return {
                "success": True,
                "project": project or "all",
                "status_counts": {s["status"]: s["count"] for s in status_counts},
                "priority_counts": {p["priority"]: p["count"] for p in priority_counts},
                "top_tags": [{"tag": t["tag"], "count": t["count"]} for t in tag_counts],
                "overdue_tasks": overdue,
                "due_soon_tasks": due_soon
            }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"success": False, "error": str(e)}
