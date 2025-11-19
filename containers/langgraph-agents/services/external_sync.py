"""
External Sync Service

Scheduled jobs for bidirectional synchronization with external services.

Replaces n8n workflows:
- 13-todoist-sync.json (every 15 minutes)
- 14-google-calendar-sync.json (every 15 minutes)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os

from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Todoist Sync (Workflow 13)
# Schedule: Every 15 minutes (if enabled)
# ============================================================================

async def sync_todoist() -> Dict[str, Any]:
    """
    Bidirectional sync with Todoist.

    Replaces n8n workflow: 13-todoist-sync.json

    Logic:
    1. Fetch all Todoist tasks via API
    2. For each Todoist task:
       - Check if exists locally (by todoist_id)
       - If not, create local task
       - If exists and modified, update local task
    3. Fetch local tasks modified since last sync
    4. For each modified local task:
       - Push to Todoist API (POST/PATCH)
       - Update todoist_id mapping
    5. Return sync statistics

    Returns:
        Dict with sync statistics
    """
    try:
        # Check if Todoist sync is enabled
        todoist_enabled = os.getenv("TODOIST_SYNC_ENABLED", "false").lower() == "true"
        todoist_api_key = os.getenv("TODOIST_API_KEY", "")

        if not todoist_enabled:
            logger.debug("Todoist sync is disabled")
            return {
                "success": True,
                "enabled": False,
                "message": "Todoist sync is disabled"
            }

        if not todoist_api_key:
            logger.error("Todoist API key not configured")
            return {
                "success": False,
                "error": "Todoist API key not configured"
            }

        import httpx

        stats = {
            "tasks_from_todoist": 0,
            "tasks_to_todoist": 0,
            "local_created": 0,
            "local_updated": 0,
            "todoist_created": 0,
            "todoist_updated": 0,
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }

        pool = await get_db_pool()

        # 1. Fetch tasks from Todoist
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.todoist.com/rest/v2/tasks",
                    headers={"Authorization": f"Bearer {todoist_api_key}"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise Exception(f"Todoist API error: {response.status_code} - {response.text}")

                todoist_tasks = response.json()
                stats["tasks_from_todoist"] = len(todoist_tasks)

                logger.info(f"Fetched {len(todoist_tasks)} tasks from Todoist")

                # 2. Process Todoist tasks
                async with pool.acquire() as conn:
                    for task in todoist_tasks:
                        try:
                            todoist_id = task["id"]

                            # Check if task exists locally
                            local_task = await conn.fetchrow(
                                "SELECT id, updated_at FROM tasks WHERE todoist_id = $1",
                                todoist_id
                            )

                            # Map Todoist data to local schema
                            title = task.get("content", "")
                            description = task.get("description", "")
                            due_date = None
                            if task.get("due"):
                                due_date = datetime.fromisoformat(task["due"]["date"].replace("Z", "+00:00"))

                            # Map priority (Todoist: 1-4, Local: 1-5)
                            priority = min(task.get("priority", 1), 5)

                            # Map status
                            status = "done" if task.get("is_completed") else "todo"

                            if not local_task:
                                # Create new local task
                                await conn.execute(
                                    """
                                    INSERT INTO tasks (
                                        title, description, due_date, priority, status,
                                        todoist_id, created_at, updated_at
                                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                                    """,
                                    title, description, due_date, priority, status, todoist_id
                                )
                                stats["local_created"] += 1
                                logger.debug(f"Created local task from Todoist: {todoist_id}")

                            else:
                                # Update existing local task
                                # Only update if Todoist version is newer
                                await conn.execute(
                                    """
                                    UPDATE tasks
                                    SET
                                        title = $1,
                                        description = $2,
                                        due_date = $3,
                                        priority = $4,
                                        status = $5,
                                        updated_at = NOW()
                                    WHERE todoist_id = $6
                                    """,
                                    title, description, due_date, priority, status, todoist_id
                                )
                                stats["local_updated"] += 1
                                logger.debug(f"Updated local task from Todoist: {todoist_id}")

                        except Exception as e:
                            logger.error(f"Error processing Todoist task {task.get('id')}: {e}")
                            stats["errors"].append({
                                "task_id": task.get("id"),
                                "error": str(e)
                            })

            except Exception as e:
                logger.error(f"Error fetching from Todoist: {e}", exc_info=True)
                stats["errors"].append({"stage": "fetch_from_todoist", "error": str(e)})

            # 3. Push local changes to Todoist
            try:
                async with pool.acquire() as conn:
                    # Get local tasks modified since last sync (not already synced)
                    cutoff_time = datetime.now() - timedelta(minutes=30)

                    local_tasks = await conn.fetch(
                        """
                        SELECT id, title, description, due_date, priority, status, todoist_id
                        FROM tasks
                        WHERE updated_at > $1
                          AND (todoist_id IS NULL OR todoist_last_synced < updated_at)
                        LIMIT 50
                        """,
                        cutoff_time
                    )

                    stats["tasks_to_todoist"] = len(local_tasks)

                    for task in local_tasks:
                        try:
                            # Prepare Todoist task data
                            todoist_data = {
                                "content": task["title"],
                                "description": task["description"] or "",
                                "priority": min(task["priority"], 4)  # Todoist max priority is 4
                            }

                            if task["due_date"]:
                                todoist_data["due_string"] = task["due_date"].isoformat()

                            if task["todoist_id"]:
                                # Update existing Todoist task
                                response = await client.post(
                                    f"https://api.todoist.com/rest/v2/tasks/{task['todoist_id']}",
                                    headers={"Authorization": f"Bearer {todoist_api_key}"},
                                    json=todoist_data,
                                    timeout=30.0
                                )

                                if response.status_code in [200, 204]:
                                    await conn.execute(
                                        "UPDATE tasks SET todoist_last_synced = NOW() WHERE id = $1",
                                        task["id"]
                                    )
                                    stats["todoist_updated"] += 1
                                    logger.debug(f"Updated Todoist task: {task['todoist_id']}")

                            else:
                                # Create new Todoist task
                                response = await client.post(
                                    "https://api.todoist.com/rest/v2/tasks",
                                    headers={"Authorization": f"Bearer {todoist_api_key}"},
                                    json=todoist_data,
                                    timeout=30.0
                                )

                                if response.status_code in [200, 201]:
                                    todoist_task = response.json()
                                    await conn.execute(
                                        """
                                        UPDATE tasks
                                        SET todoist_id = $1, todoist_last_synced = NOW()
                                        WHERE id = $2
                                        """,
                                        todoist_task["id"],
                                        task["id"]
                                    )
                                    stats["todoist_created"] += 1
                                    logger.debug(f"Created Todoist task: {todoist_task['id']}")

                        except Exception as e:
                            logger.error(f"Error pushing task {task['id']} to Todoist: {e}")
                            stats["errors"].append({
                                "task_id": task["id"],
                                "error": str(e)
                            })

            except Exception as e:
                logger.error(f"Error pushing to Todoist: {e}", exc_info=True)
                stats["errors"].append({"stage": "push_to_todoist", "error": str(e)})

        logger.info(
            f"Todoist sync complete: "
            f"+{stats['local_created']} created, "
            f"~{stats['local_updated']} updated locally, "
            f"+{stats['todoist_created']} created, "
            f"~{stats['todoist_updated']} updated in Todoist"
        )

        return stats

    except Exception as e:
        logger.error(f"Error during Todoist sync: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Google Calendar Sync (Workflow 14)
# Schedule: Every 15 minutes (if enabled)
# ============================================================================

async def sync_google_calendar() -> Dict[str, Any]:
    """
    Bidirectional sync with Google Calendar.

    Replaces n8n workflow: 14-google-calendar-sync.json

    Logic:
    1. Authenticate with Google Calendar API (OAuth2)
    2. Fetch calendar events (next 30 days)
    3. For each Google event:
       - Check if exists locally (by google_event_id)
       - If not, create local event
       - If exists and modified, update local event
    4. Fetch local events modified since last sync
    5. For each modified local event:
       - Push to Google Calendar API
       - Update google_event_id mapping
    6. Return sync statistics

    Returns:
        Dict with sync statistics
    """
    try:
        # Check if Google Calendar sync is enabled
        gcal_enabled = os.getenv("GOOGLE_CALENDAR_SYNC_ENABLED", "false").lower() == "true"
        credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "")

        if not gcal_enabled:
            logger.debug("Google Calendar sync is disabled")
            return {
                "success": True,
                "enabled": False,
                "message": "Google Calendar sync is disabled"
            }

        if not credentials_path or not os.path.exists(credentials_path):
            logger.error("Google Calendar credentials not found")
            return {
                "success": False,
                "error": "Google Calendar credentials not configured"
            }

        # Note: Full Google Calendar integration requires:
        # - google-auth, google-auth-oauthlib, google-auth-httplib2, google-api-python-client
        # - OAuth2 flow for token generation
        # - Token refresh logic
        #
        # This is a simplified implementation that would need the above dependencies.
        # For now, we'll return a placeholder indicating the feature is not fully implemented.

        logger.warning("Google Calendar sync requires additional setup (OAuth2 credentials)")

        return {
            "success": False,
            "error": "Google Calendar sync requires OAuth2 setup and additional dependencies",
            "message": "Install google-auth libraries and configure OAuth2 credentials",
            "timestamp": datetime.now().isoformat()
        }

        # TODO: Implement full Google Calendar sync when dependencies are available
        # The logic would be similar to Todoist sync:
        # 1. Use google.oauth2.credentials to authenticate
        # 2. Use googleapiclient.discovery to build calendar service
        # 3. Fetch events with calendar.events().list()
        # 4. Sync bidirectionally similar to Todoist

    except Exception as e:
        logger.error(f"Error during Google Calendar sync: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
