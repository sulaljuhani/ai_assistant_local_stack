"""
Bulk operations for tasks, events, and reminders.

Inspired by Atlas MCP server's bulk capabilities.
"""

from typing import List, Dict, Any
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def bulk_create_tasks(
    tasks: List[Dict[str, Any]],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Create multiple tasks at once.

    Useful for breaking down projects or importing task lists.

    Args:
        tasks: List of task dicts with title, description, priority, due_date, tags
        user_id: User identifier

    Example:
        tasks = [
            {"title": "Research topic", "priority": 3, "tags": ["research"]},
            {"title": "Write outline", "priority": 2, "due_date": "2024-12-01"},
            {"title": "Draft content", "priority": 1}
        ]

    Returns:
        Success status and created task IDs
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            created = []

            for task_data in tasks:
                title = task_data.get("title")
                if not title:
                    continue

                description = task_data.get("description")
                priority = task_data.get("priority", 0)
                due_date = task_data.get("due_date")
                tags = task_data.get("tags", [])
                status = task_data.get("status", "todo")

                result = await conn.fetchrow(
                    """
                    INSERT INTO tasks (user_id, title, description, priority, due_date, tags, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, title
                    """,
                    user_id, title, description, priority, due_date, tags, status
                )

                created.append({
                    "id": str(result["id"]),
                    "title": result["title"]
                })

            logger.info(f"Bulk created {len(created)} tasks")

            return {
                "success": True,
                "created_count": len(created),
                "tasks": created
            }

    except Exception as e:
        logger.error(f"Error bulk creating tasks: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_update_task_status(
    task_ids: List[str],
    new_status: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Update status for multiple tasks at once.

    Useful for batch completion or cancellation.

    Args:
        task_ids: List of task IDs
        new_status: New status (todo, in_progress, done, cancelled)
        user_id: User identifier

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE tasks
                SET status = $1, updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                new_status,
                task_ids,
                user_id
            )

            # Extract count from result string "UPDATE N"
            count = int(result.split()[-1]) if result else 0

            logger.info(f"Bulk updated {count} tasks to status '{new_status}'")

            return {
                "success": True,
                "updated_count": count,
                "new_status": new_status
            }

    except Exception as e:
        logger.error(f"Error bulk updating tasks: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_add_tags(
    task_ids: List[str],
    tags: List[str],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Add tags to multiple tasks at once.

    Args:
        task_ids: List of task IDs
        tags: List of tags to add
        user_id: User identifier

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE tasks
                SET tags = array(
                    SELECT DISTINCT unnest(COALESCE(tags, ARRAY[]::TEXT[]) || $1)
                ),
                    updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                tags,
                task_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.info(f"Bulk added tags {tags} to {count} tasks")

            return {
                "success": True,
                "updated_count": count,
                "added_tags": tags
            }

    except Exception as e:
        logger.error(f"Error bulk adding tags: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_set_priority(
    task_ids: List[str],
    priority: int,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Set priority for multiple tasks at once.

    Args:
        task_ids: List of task IDs
        priority: Priority level (0=none, 1=low, 2=medium, 3=high, 4=urgent)
        user_id: User identifier

    Returns:
        Success status and count updated
    """
    if not 0 <= priority <= 4:
        return {"success": False, "error": "Priority must be 0-4"}

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE tasks
                SET priority = $1, updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                priority,
                task_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.info(f"Bulk set priority to {priority} for {count} tasks")

            return {
                "success": True,
                "updated_count": count,
                "priority": priority
            }

    except Exception as e:
        logger.error(f"Error bulk setting priority: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_delete_tasks(
    task_ids: List[str],
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Delete multiple tasks at once.

    WARNING: This permanently deletes tasks. Consider using bulk_update_task_status
    with status='cancelled' instead.

    Args:
        task_ids: List of task IDs to delete
        user_id: User identifier

    Returns:
        Success status and count deleted
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = ANY($1) AND user_id = $2",
                task_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.warning(f"Bulk deleted {count} tasks")

            return {
                "success": True,
                "deleted_count": count,
                "warning": "Tasks permanently deleted"
            }

    except Exception as e:
        logger.error(f"Error bulk deleting tasks: {e}")
        return {"success": False, "error": str(e)}


@tool
async def bulk_move_to_project(
    task_ids: List[str],
    project_name: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Move multiple tasks to a project.

    Args:
        task_ids: List of task IDs
        project_name: Project name
        user_id: User identifier

    Returns:
        Success status and count updated
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE tasks
                SET project = $1, updated_at = NOW()
                WHERE id = ANY($2) AND user_id = $3
                """,
                project_name,
                task_ids,
                user_id
            )

            count = int(result.split()[-1]) if result else 0

            logger.info(f"Bulk moved {count} tasks to project '{project_name}'")

            return {
                "success": True,
                "updated_count": count,
                "project": project_name
            }

    except Exception as e:
        logger.error(f"Error bulk moving to project: {e}")
        return {"success": False, "error": str(e)}
