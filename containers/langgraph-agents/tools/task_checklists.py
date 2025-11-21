"""
Task checklist/subtask management tools.

Utilizes the existing checklist JSONB field in the tasks table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger
import json

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


@tool
async def add_checklist_item(
    task_id: str,
    item_text: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Add a checklist item (subtask) to a task.

    Args:
        task_id: Task ID
        item_text: Checklist item text
        user_id: User identifier

    Returns:
        Success status and updated checklist
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get current checklist
            result = await conn.fetchrow(
                "SELECT id, title, checklist FROM tasks WHERE id = $1 AND user_id = $2",
                task_id,
                user_id
            )

            if not result:
                return {"success": False, "error": "Task not found"}

            # Parse existing checklist
            checklist = result["checklist"] or []
            if isinstance(checklist, str):
                checklist = json.loads(checklist)

            # Add new item
            new_item = {
                "text": item_text,
                "done": False,
                "created_at": datetime.utcnow().isoformat()
            }
            checklist.append(new_item)

            # Update task
            await conn.execute(
                "UPDATE tasks SET checklist = $1 WHERE id = $2",
                json.dumps(checklist),
                task_id
            )

            logger.info(f"Added checklist item to task {task_id}")

            return {
                "success": True,
                "task_id": str(result["id"]),
                "task_title": result["title"],
                "checklist": checklist,
                "total_items": len(checklist),
                "completed_items": sum(1 for item in checklist if item.get("done", False))
            }

    except Exception as e:
        logger.error(f"Error adding checklist item: {e}")
        return {"success": False, "error": str(e)}


@tool
async def check_checklist_item(
    task_id: str,
    item_index: int,
    done: bool = True,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Mark a checklist item as done or undone.

    Args:
        task_id: Task ID
        item_index: Index of checklist item (0-based)
        done: True to mark done, False to mark undone
        user_id: User identifier

    Returns:
        Success status and updated checklist
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT id, title, checklist FROM tasks WHERE id = $1 AND user_id = $2",
                task_id,
                user_id
            )

            if not result:
                return {"success": False, "error": "Task not found"}

            checklist = result["checklist"] or []
            if isinstance(checklist, str):
                checklist = json.loads(checklist)

            if item_index < 0 or item_index >= len(checklist):
                return {"success": False, "error": f"Invalid item index: {item_index}"}

            # Update item
            checklist[item_index]["done"] = done
            if done:
                checklist[item_index]["completed_at"] = datetime.utcnow().isoformat()

            # Update task
            await conn.execute(
                "UPDATE tasks SET checklist = $1 WHERE id = $2",
                json.dumps(checklist),
                task_id
            )

            completed = sum(1 for item in checklist if item.get("done", False))
            progress_pct = (completed / len(checklist) * 100) if checklist else 0

            logger.info(f"Updated checklist item {item_index} in task {task_id}")

            return {
                "success": True,
                "task_id": str(result["id"]),
                "task_title": result["title"],
                "checklist": checklist,
                "progress": {
                    "completed": completed,
                    "total": len(checklist),
                    "percentage": round(progress_pct, 1)
                }
            }

    except Exception as e:
        logger.error(f"Error checking checklist item: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_task_with_checklist(
    task_id: str,
    user_id: str = USER_ID
) -> Dict[str, Any]:
    """
    Get a task with its checklist and progress.

    Args:
        task_id: Task ID
        user_id: User identifier

    Returns:
        Task details with checklist progress
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT id, title, description, status, priority,
                       due_date, checklist, created_at
                FROM tasks
                WHERE id = $1 AND user_id = $2
                """,
                task_id,
                user_id
            )

            if not result:
                return {"success": False, "error": "Task not found"}

            checklist = result["checklist"] or []
            if isinstance(checklist, str):
                checklist = json.loads(checklist)

            completed = sum(1 for item in checklist if item.get("done", False))
            progress_pct = (completed / len(checklist) * 100) if checklist else 0

            return {
                "success": True,
                "task": {
                    "id": str(result["id"]),
                    "title": result["title"],
                    "description": result["description"],
                    "status": result["status"],
                    "priority": result["priority"],
                    "due_date": result["due_date"].isoformat() if result["due_date"] else None,
                    "checklist": checklist
                },
                "progress": {
                    "completed": completed,
                    "total": len(checklist),
                    "percentage": round(progress_pct, 1),
                    "remaining": len(checklist) - completed
                }
            }

    except Exception as e:
        logger.error(f"Error getting task checklist: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_tasks_with_incomplete_checklists(
    user_id: str = USER_ID,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get tasks that have incomplete checklist items.

    Useful for finding tasks with partial progress.

    Args:
        user_id: User identifier
        limit: Maximum results

    Returns:
        List of tasks with incomplete checklists
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            tasks = await conn.fetch(
                """
                SELECT id, title, status, priority, due_date, checklist
                FROM tasks
                WHERE user_id = $1
                  AND status NOT IN ('done', 'cancelled')
                  AND checklist IS NOT NULL
                  AND jsonb_array_length(checklist) > 0
                ORDER BY priority DESC, due_date NULLS LAST
                LIMIT $2
                """,
                user_id,
                limit
            )

            result = []
            for task in tasks:
                checklist = task["checklist"] or []
                if isinstance(checklist, str):
                    checklist = json.loads(checklist)

                completed = sum(1 for item in checklist if item.get("done", False))
                total = len(checklist)

                # Only include if there are incomplete items
                if completed < total:
                    result.append({
                        "id": str(task["id"]),
                        "title": task["title"],
                        "status": task["status"],
                        "priority": task["priority"],
                        "due_date": task["due_date"].isoformat() if task["due_date"] else None,
                        "progress": {
                            "completed": completed,
                            "total": total,
                            "percentage": round(completed / total * 100, 1)
                        },
                        "checklist": checklist
                    })

            logger.info(f"Found {len(result)} tasks with incomplete checklists")
            return result

    except Exception as e:
        logger.error(f"Error getting incomplete checklists: {e}")
        return []
