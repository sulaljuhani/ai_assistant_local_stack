"""
Tasks Router

API endpoints for task management operations.
Replaces n8n workflow: 02-create-task.json
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from middleware.validation import (
    CreateTaskRequest,
    UpdateTaskRequest,
    SuccessResponse,
    ErrorResponse,
    TaskStatus,
    TaskPriority,
)
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# Response models
class TaskResponse(BaseModel):
    """Task response model"""
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: int
    status: str
    category: Optional[str]
    tags: List[str]
    is_recurring: bool
    recurrence_pattern: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class TaskListResponse(BaseModel):
    """Task list response model"""
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# CREATE Task
# ============================================================================

@router.post("/create", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """
    Create a new task.

    Replaces n8n workflow: 02-create-task.json

    Logic:
    1. Validate input (handled by Pydantic)
    2. Get category ID from database (if category provided)
    3. Insert task with parameterized query
    4. Return created task
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
                    WHERE name = $1 AND type = 'task'
                    LIMIT 1
                    """,
                    request.category
                )

                # If category doesn't exist, create it
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'task', '#3B82F6')
                        RETURNING id
                        """,
                        request.category
                    )

                category_id = category_row['id']

            # Insert task
            task = await conn.fetchrow(
                """
                INSERT INTO tasks (
                    title,
                    description,
                    due_date,
                    priority,
                    status,
                    category_id,
                    tags,
                    is_recurring,
                    recurrence_pattern,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                RETURNING
                    id, title, description, due_date, priority, status,
                    tags, is_recurring, recurrence_pattern,
                    created_at, updated_at, completed_at
                """,
                request.title,
                request.description,
                request.due_date,
                request.priority.value,
                request.status.value,
                category_id,
                request.tags,
                request.is_recurring,
                request.recurrence_pattern.value if request.recurrence_pattern else None
            )

            logger.info(f"Created task: {task['id']} - {task['title']}")

            return TaskResponse(
                id=task['id'],
                title=task['title'],
                description=task['description'],
                due_date=task['due_date'],
                priority=task['priority'],
                status=task['status'],
                category=request.category,
                tags=task['tags'] or [],
                is_recurring=task['is_recurring'],
                recurrence_pattern=task['recurrence_pattern'],
                created_at=task['created_at'],
                updated_at=task['updated_at'],
                completed_at=task['completed_at']
            )

    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


# ============================================================================
# READ Tasks
# ============================================================================

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_recurring: Optional[bool] = Query(None, description="Filter recurring tasks"),
    limit: int = Query(50, ge=1, le=200, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List tasks with optional filtering.

    Supports filtering by:
    - status (todo, in_progress, waiting, done, cancelled)
    - priority (1-5)
    - category
    - is_recurring
    """
    try:
        pool = await get_db_pool()

        # Build query dynamically based on filters
        where_clauses = []
        params = []
        param_count = 1

        if status:
            where_clauses.append(f"t.status = ${param_count}")
            params.append(status.value)
            param_count += 1

        if priority:
            where_clauses.append(f"t.priority = ${param_count}")
            params.append(priority.value)
            param_count += 1

        if category:
            where_clauses.append(f"c.name = ${param_count}")
            params.append(category)
            param_count += 1

        if is_recurring is not None:
            where_clauses.append(f"t.is_recurring = ${param_count}")
            params.append(is_recurring)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        async with pool.acquire() as conn:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                {where_clause}
            """
            total = await conn.fetchval(count_query, *params)

            # Get tasks
            params.extend([limit, offset])
            query = f"""
                SELECT
                    t.id, t.title, t.description, t.due_date, t.priority, t.status,
                    t.tags, t.is_recurring, t.recurrence_pattern,
                    t.created_at, t.updated_at, t.completed_at,
                    c.name as category
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                {where_clause}
                ORDER BY t.created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """

            rows = await conn.fetch(query, *params)

            tasks = [
                TaskResponse(
                    id=row['id'],
                    title=row['title'],
                    description=row['description'],
                    due_date=row['due_date'],
                    priority=row['priority'],
                    status=row['status'],
                    category=row['category'],
                    tags=row['tags'] or [],
                    is_recurring=row['is_recurring'],
                    recurrence_pattern=row['recurrence_pattern'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    completed_at=row['completed_at']
                )
                for row in rows
            ]

            return TaskListResponse(
                tasks=tasks,
                total=total,
                limit=limit,
                offset=offset
            )

    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get a specific task by ID."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    t.id, t.title, t.description, t.due_date, t.priority, t.status,
                    t.tags, t.is_recurring, t.recurrence_pattern,
                    t.created_at, t.updated_at, t.completed_at,
                    c.name as category
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.id = $1
                """,
                task_id
            )

            if not row:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

            return TaskResponse(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                due_date=row['due_date'],
                priority=row['priority'],
                status=row['status'],
                category=row['category'],
                tags=row['tags'] or [],
                is_recurring=row['is_recurring'],
                recurrence_pattern=row['recurrence_pattern'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


# ============================================================================
# UPDATE Task
# ============================================================================

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, request: UpdateTaskRequest):
    """
    Update an existing task.

    Only provided fields will be updated.
    """
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Check if task exists
            existing = await conn.fetchrow("SELECT id FROM tasks WHERE id = $1", task_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

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

            if request.due_date is not None:
                update_fields.append(f"due_date = ${param_count}")
                params.append(request.due_date)
                param_count += 1

            if request.priority is not None:
                update_fields.append(f"priority = ${param_count}")
                params.append(request.priority.value)
                param_count += 1

            if request.status is not None:
                update_fields.append(f"status = ${param_count}")
                params.append(request.status.value)
                param_count += 1

                # If status is 'done', set completed_at
                if request.status == TaskStatus.DONE:
                    update_fields.append("completed_at = NOW()")

            if request.tags is not None:
                update_fields.append(f"tags = ${param_count}")
                params.append(request.tags)
                param_count += 1

            if request.is_recurring is not None:
                update_fields.append(f"is_recurring = ${param_count}")
                params.append(request.is_recurring)
                param_count += 1

            if request.recurrence_pattern is not None:
                update_fields.append(f"recurrence_pattern = ${param_count}")
                params.append(request.recurrence_pattern.value)
                param_count += 1

            # Handle category
            if request.category is not None:
                category_row = await conn.fetchrow(
                    "SELECT id FROM categories WHERE name = $1 AND type = 'task'",
                    request.category
                )
                if not category_row:
                    category_row = await conn.fetchrow(
                        """
                        INSERT INTO categories (name, type, color)
                        VALUES ($1, 'task', '#3B82F6')
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

            # Add task_id as last parameter
            params.append(task_id)

            # Execute update
            query = f"""
                UPDATE tasks
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING
                    id, title, description, due_date, priority, status,
                    tags, is_recurring, recurrence_pattern,
                    created_at, updated_at, completed_at
            """

            task = await conn.fetchrow(query, *params)

            # Get category name
            category_name = None
            if task:
                category_row = await conn.fetchrow(
                    "SELECT name FROM categories WHERE id = (SELECT category_id FROM tasks WHERE id = $1)",
                    task_id
                )
                if category_row:
                    category_name = category_row['name']

            logger.info(f"Updated task: {task['id']} - {task['title']}")

            return TaskResponse(
                id=task['id'],
                title=task['title'],
                description=task['description'],
                due_date=task['due_date'],
                priority=task['priority'],
                status=task['status'],
                category=category_name,
                tags=task['tags'] or [],
                is_recurring=task['is_recurring'],
                recurrence_pattern=task['recurrence_pattern'],
                created_at=task['created_at'],
                updated_at=task['updated_at'],
                completed_at=task['completed_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


# ============================================================================
# DELETE Task
# ============================================================================

@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """Delete a task."""
    try:
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1",
                task_id
            )

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

            logger.info(f"Deleted task: {task_id}")

            return {"success": True, "message": f"Task {task_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")
