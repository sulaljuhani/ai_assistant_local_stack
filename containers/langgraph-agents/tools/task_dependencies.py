"""
Task dependency management tools.

Utilizes the existing depends_on and blocks fields in the tasks table.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def add_task_dependency(
    task_id: str,
    depends_on_task_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Add a dependency: task_id depends on depends_on_task_id.

    The task cannot be started until the dependency is completed.

    Args:
        task_id: ID of the task that has a dependency
        depends_on_task_id: ID of the task this depends on
        user_id: User identifier

    Returns:
        Success status and updated task info
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Verify both tasks exist and belong to user
            tasks = await conn.fetch(
                "SELECT id, title, status FROM tasks WHERE id = ANY($1) AND user_id = $2",
                [task_id, depends_on_task_id],
                user_id
            )

            if len(tasks) != 2:
                return {"success": False, "error": "One or both tasks not found"}

            # Check for circular dependencies
            existing_deps = await conn.fetchval(
                "SELECT depends_on FROM tasks WHERE id = $1",
                depends_on_task_id
            )

            if existing_deps and task_id in existing_deps:
                return {
                    "success": False,
                    "error": "Circular dependency detected"
                }

            # Add dependency
            result = await conn.fetchrow(
                """
                UPDATE tasks
                SET depends_on = array_append(
                    COALESCE(depends_on, ARRAY[]::UUID[]),
                    $1::UUID
                ),
                    blocks = (
                        SELECT array_append(
                            COALESCE(blocks, ARRAY[]::UUID[]),
                            $2::UUID
                        )
                        FROM tasks
                        WHERE id = $1
                    )
                WHERE id = $2 AND user_id = $3
                RETURNING id, title, depends_on
                """,
                depends_on_task_id,
                task_id,
                user_id
            )

            logger.info(f"Added dependency: {task_id} depends on {depends_on_task_id}")

            return {
                "success": True,
                "task_id": str(result["id"]),
                "task_title": result["title"],
                "depends_on": [str(d) for d in result["depends_on"]]
            }

    except Exception as e:
        logger.error(f"Error adding dependency: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_task_dependencies(
    task_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Get all dependencies for a task (what it depends on and what depends on it).

    Args:
        task_id: Task ID
        user_id: User identifier

    Returns:
        Task dependencies and blocked tasks
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get task with dependencies
            task = await conn.fetchrow(
                """
                SELECT id, title, depends_on, blocks, status
                FROM tasks
                WHERE id = $1 AND user_id = $2
                """,
                task_id,
                user_id
            )

            if not task:
                return {"success": False, "error": "Task not found"}

            # Get details of dependencies
            dependencies = []
            if task["depends_on"]:
                deps = await conn.fetch(
                    """
                    SELECT id, title, status, completed_at
                    FROM tasks
                    WHERE id = ANY($1)
                    ORDER BY due_date NULLS LAST, priority DESC
                    """,
                    task["depends_on"]
                )
                dependencies = [dict(d) for d in deps]

            # Get details of blocked tasks
            blocked_tasks = []
            if task["blocks"]:
                blocked = await conn.fetch(
                    """
                    SELECT id, title, status, due_date
                    FROM tasks
                    WHERE id = ANY($1)
                    ORDER BY due_date NULLS LAST, priority DESC
                    """,
                    task["blocks"]
                )
                blocked_tasks = [dict(b) for b in blocked]

            return {
                "success": True,
                "task": {
                    "id": str(task["id"]),
                    "title": task["title"],
                    "status": task["status"]
                },
                "depends_on": dependencies,
                "blocks": blocked_tasks,
                "can_start": all(d["status"] == "done" for d in dependencies) if dependencies else True
            }

    except Exception as e:
        logger.error(f"Error getting dependencies: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_available_tasks(
    user_id: str = USER_ID,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get tasks that can be started (no pending dependencies).

    Returns tasks that either have no dependencies or all dependencies are completed.

    Args:
        user_id: User identifier
        limit: Maximum results

    Returns:
        List of tasks ready to start
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get tasks with no dependencies or completed dependencies
            tasks = await conn.fetch(
                """
                SELECT
                    t.id,
                    t.title,
                    t.status,
                    t.priority,
                    t.due_date,
                    t.depends_on,
                    CASE
                        WHEN t.depends_on IS NULL OR array_length(t.depends_on, 1) IS NULL THEN true
                        ELSE (
                            SELECT bool_and(status = 'done')
                            FROM tasks
                            WHERE id = ANY(t.depends_on)
                        )
                    END as can_start
                FROM tasks t
                WHERE t.user_id = $1
                  AND t.status NOT IN ('done', 'cancelled')
                ORDER BY
                    can_start DESC,
                    t.priority DESC,
                    t.due_date NULLS LAST
                LIMIT $2
                """,
                user_id,
                limit
            )

            result = []
            for task in tasks:
                task_dict = dict(task)
                task_dict["id"] = str(task_dict["id"])

                # Get dependency details if any
                if task["depends_on"]:
                    deps = await conn.fetch(
                        "SELECT id, title, status FROM tasks WHERE id = ANY($1)",
                        task["depends_on"]
                    )
                    task_dict["dependencies"] = [dict(d) for d in deps]

                result.append(task_dict)

            logger.info(f"Found {len(result)} available tasks")
            return result

    except Exception as e:
        logger.error(f"Error getting available tasks: {e}")
        return []


@tool
async def complete_task_with_unblock(
    task_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Complete a task and show which blocked tasks are now available.

    Args:
        task_id: Task ID to complete
        user_id: User identifier

    Returns:
        Completion status and newly unblocked tasks
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get task and blocked tasks
            task = await conn.fetchrow(
                "SELECT id, title, blocks FROM tasks WHERE id = $1 AND user_id = $2",
                task_id,
                user_id
            )

            if not task:
                return {"success": False, "error": "Task not found"}

            # Complete the task
            await conn.execute(
                "UPDATE tasks SET status = 'done', completed_at = NOW() WHERE id = $1",
                task_id
            )

            # Find newly unblocked tasks
            unblocked = []
            if task["blocks"]:
                # Check which blocked tasks now have all dependencies completed
                for blocked_id in task["blocks"]:
                    blocked_task = await conn.fetchrow(
                        """
                        SELECT
                            t.id,
                            t.title,
                            t.depends_on,
                            (
                                SELECT bool_and(status = 'done')
                                FROM tasks
                                WHERE id = ANY(t.depends_on)
                            ) as all_deps_done
                        FROM tasks t
                        WHERE t.id = $1 AND t.status NOT IN ('done', 'cancelled')
                        """,
                        blocked_id
                    )

                    if blocked_task and blocked_task["all_deps_done"]:
                        unblocked.append({
                            "id": str(blocked_task["id"]),
                            "title": blocked_task["title"]
                        })

            return {
                "success": True,
                "task": {
                    "id": str(task["id"]),
                    "title": task["title"],
                    "status": "done"
                },
                "unblocked_tasks": unblocked,
                "message": f"Completed '{task['title']}'. {len(unblocked)} task(s) now available."
            }

    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return {"success": False, "error": str(e)}
