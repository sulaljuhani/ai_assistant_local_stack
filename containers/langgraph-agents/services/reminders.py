"""
Reminder Service

Scheduled jobs for reminder and task management.

Replaces n8n workflows:
- 04-fire-reminders.json (every 5 minutes)
- 05-daily-summary.json (8 AM daily)
- 06-expand-recurring-tasks.json (midnight daily)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Fire Reminders (Workflow 04)
# Schedule: Every 5 minutes
# ============================================================================

async def fire_reminders() -> Dict[str, Any]:
    """
    Check for due reminders and mark them as fired.

    Replaces n8n workflow: 04-fire-reminders.json

    Logic:
    1. Query reminders WHERE remind_at <= NOW() AND is_completed = FALSE
    2. For each reminder:
       - Mark as completed
       - Log reminder fired
       - (Future: Send notification)
    3. Return count of fired reminders

    Returns:
        Dict with fired reminder count and details
    """
    try:
        pool = await get_db_pool()
        now = datetime.now()

        async with pool.acquire() as conn:
            # Get due reminders
            due_reminders = await conn.fetch(
                """
                SELECT id, title, description, remind_at, priority
                FROM reminders
                WHERE remind_at <= $1
                  AND is_completed = FALSE
                ORDER BY priority DESC, remind_at ASC
                """,
                now
            )

            if not due_reminders:
                logger.debug("No due reminders found")
                return {"count": 0, "reminders": []}

            # Mark reminders as completed
            reminder_ids = [r['id'] for r in due_reminders]

            await conn.execute(
                """
                UPDATE reminders
                SET is_completed = TRUE, completed_at = NOW(), updated_at = NOW()
                WHERE id = ANY($1)
                """,
                reminder_ids
            )

            # Log each fired reminder
            fired_reminders = []
            for reminder in due_reminders:
                logger.info(
                    f"Fired reminder: {reminder['id']} - {reminder['title']} "
                    f"(priority: {reminder['priority']}, due: {reminder['remind_at']})"
                )
                fired_reminders.append({
                    "id": reminder['id'],
                    "title": reminder['title'],
                    "description": reminder['description'],
                    "remind_at": reminder['remind_at'].isoformat(),
                    "priority": reminder['priority']
                })

            logger.info(f"Fired {len(due_reminders)} reminders")

            # TODO: Send notifications (integrate with notification service)
            # For now, we just log them

            return {
                "count": len(due_reminders),
                "reminders": fired_reminders,
                "timestamp": now.isoformat()
            }

    except Exception as e:
        logger.error(f"Error firing reminders: {e}", exc_info=True)
        return {"count": 0, "error": str(e)}


# ============================================================================
# Generate Daily Summary (Workflow 05)
# Schedule: Daily at 8 AM
# ============================================================================

async def generate_daily_summary() -> Dict[str, Any]:
    """
    Generate daily summary of tasks, events, and reminders.

    Replaces n8n workflow: 05-daily-summary.json

    Logic:
    1. Get today's tasks (not completed)
    2. Get today's events
    3. Get today's reminders (not completed)
    4. Format summary
    5. (Future: Send notification/email)

    Returns:
        Dict with summary data
    """
    try:
        pool = await get_db_pool()
        today = datetime.now().date()

        async with pool.acquire() as conn:
            # Get today's tasks
            tasks = await conn.fetch(
                """
                SELECT id, title, priority, status, due_date
                FROM tasks
                WHERE DATE(due_date) = $1
                  AND status != 'done'
                ORDER BY priority DESC
                """,
                today
            )

            # Get today's events
            events = await conn.fetch(
                """
                SELECT id, title, start_time, end_time, location
                FROM events
                WHERE DATE(start_time) = $1
                ORDER BY start_time ASC
                """,
                today
            )

            # Get today's reminders
            reminders = await conn.fetch(
                """
                SELECT id, title, remind_at, priority
                FROM reminders
                WHERE DATE(remind_at) = $1
                  AND is_completed = FALSE
                ORDER BY remind_at ASC
                """,
                today
            )

            # Format summary
            summary = {
                "date": today.isoformat(),
                "tasks": {
                    "count": len(tasks),
                    "items": [
                        {
                            "id": t['id'],
                            "title": t['title'],
                            "priority": t['priority'],
                            "status": t['status'],
                            "due_date": t['due_date'].isoformat() if t['due_date'] else None
                        }
                        for t in tasks
                    ]
                },
                "events": {
                    "count": len(events),
                    "items": [
                        {
                            "id": e['id'],
                            "title": e['title'],
                            "start_time": e['start_time'].isoformat(),
                            "end_time": e['end_time'].isoformat(),
                            "location": e['location']
                        }
                        for e in events
                    ]
                },
                "reminders": {
                    "count": len(reminders),
                    "items": [
                        {
                            "id": r['id'],
                            "title": r['title'],
                            "remind_at": r['remind_at'].isoformat(),
                            "priority": r['priority']
                        }
                        for r in reminders
                    ]
                },
                "generated_at": datetime.now().isoformat()
            }

            logger.info(
                f"Daily summary generated: {len(tasks)} tasks, "
                f"{len(events)} events, {len(reminders)} reminders"
            )

            # TODO: Send summary notification/email
            # For now, we just return and log it

            return summary

    except Exception as e:
        logger.error(f"Error generating daily summary: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================================================
# Expand Recurring Tasks (Workflow 06)
# Schedule: Daily at midnight
# ============================================================================

async def expand_recurring_tasks() -> Dict[str, Any]:
    """
    Create task instances from recurring tasks based on their recurrence pattern.

    Replaces n8n workflow: 06-expand-recurring-tasks.json

    Logic:
    1. Query tasks WHERE is_recurring = TRUE
    2. For each recurring task:
       - Check recurrence_pattern (daily, weekly, monthly, yearly)
       - Calculate next occurrence based on last_expanded or created_at
       - Create new task instance
       - Update last_expanded timestamp
    3. Return count of expanded tasks

    Returns:
        Dict with expanded task count and details
    """
    try:
        pool = await get_db_pool()
        now = datetime.now()

        async with pool.acquire() as conn:
            # Get recurring tasks that need expansion
            recurring_tasks = await conn.fetch(
                """
                SELECT
                    id, title, description, priority, category_id, tags,
                    recurrence_pattern, due_date, last_expanded, created_at
                FROM tasks
                WHERE is_recurring = TRUE
                  AND recurrence_pattern != 'none'
                """
            )

            if not recurring_tasks:
                logger.debug("No recurring tasks found")
                return {"count": 0, "tasks": []}

            expanded_tasks = []

            for task in recurring_tasks:
                # Determine the base date for calculating next occurrence
                base_date = task['last_expanded'] or task['created_at']

                # Calculate next due date based on recurrence pattern
                next_due_date = None
                pattern = task['recurrence_pattern']

                if pattern == 'daily':
                    next_due_date = base_date + timedelta(days=1)
                elif pattern == 'weekly':
                    next_due_date = base_date + timedelta(weeks=1)
                elif pattern == 'monthly':
                    # Add approximately 30 days (more accurate would use dateutil)
                    next_due_date = base_date + timedelta(days=30)
                elif pattern == 'yearly':
                    next_due_date = base_date + timedelta(days=365)

                # Only create instance if next occurrence is today or in the past
                if next_due_date and next_due_date.date() <= now.date():
                    # Create new task instance
                    new_task = await conn.fetchrow(
                        """
                        INSERT INTO tasks (
                            title,
                            description,
                            due_date,
                            priority,
                            category_id,
                            tags,
                            status,
                            is_recurring,
                            parent_task_id,
                            created_at,
                            updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, 'todo', FALSE, $7, NOW(), NOW())
                        RETURNING id, title, due_date
                        """,
                        task['title'],
                        task['description'],
                        next_due_date,
                        task['priority'],
                        task['category_id'],
                        task['tags'],
                        task['id']  # parent_task_id
                    )

                    # Update last_expanded on recurring task
                    await conn.execute(
                        """
                        UPDATE tasks
                        SET last_expanded = $1, updated_at = NOW()
                        WHERE id = $2
                        """,
                        now,
                        task['id']
                    )

                    logger.info(
                        f"Expanded recurring task: {task['id']} - {task['title']} "
                        f"({pattern}) -> new task: {new_task['id']}"
                    )

                    expanded_tasks.append({
                        "parent_id": task['id'],
                        "parent_title": task['title'],
                        "new_id": new_task['id'],
                        "new_title": new_task['title'],
                        "due_date": next_due_date.isoformat(),
                        "pattern": pattern
                    })

            logger.info(f"Expanded {len(expanded_tasks)} recurring tasks")

            return {
                "count": len(expanded_tasks),
                "tasks": expanded_tasks,
                "timestamp": now.isoformat()
            }

    except Exception as e:
        logger.error(f"Error expanding recurring tasks: {e}", exc_info=True)
        return {"count": 0, "error": str(e)}
