"""
Maintenance Service

Scheduled jobs for system maintenance and cleanup.

Replaces n8n workflows:
- 08-cleanup-old-data.json (weekly Sunday 2 AM)
- 21-health-check.json (every 5 minutes)
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from utils.db import get_db_pool
from utils.logging import get_logger
import asyncio

logger = get_logger(__name__)


# ============================================================================
# Cleanup Old Data (Workflow 08)
# Schedule: Weekly on Sunday at 2 AM
# ============================================================================

async def cleanup_old_data() -> Dict[str, Any]:
    """
    Archive old completed tasks, reminders, and events.
    Decay memory salience for unused memories.

    Replaces n8n workflow: 08-cleanup-old-data.json

    Logic:
    1. Archive completed tasks older than 90 days
    2. Archive completed reminders older than 90 days
    3. Archive past events older than 365 days
    4. Decay memory salience (reduce by 10% for memories not accessed in 30 days)
    5. Return cleanup statistics

    Returns:
        Dict with cleanup statistics
    """
    try:
        pool = await get_db_pool()
        now = datetime.now()

        stats = {
            "tasks_archived": 0,
            "reminders_archived": 0,
            "events_archived": 0,
            "memories_decayed": 0,
            "timestamp": now.isoformat()
        }

        async with pool.acquire() as conn:
            # 1. Archive completed tasks older than 90 days
            tasks_cutoff = now - timedelta(days=90)
            tasks_result = await conn.execute(
                """
                UPDATE tasks
                SET archived = TRUE, updated_at = NOW()
                WHERE status = 'done'
                  AND completed_at < $1
                  AND archived = FALSE
                """,
                tasks_cutoff
            )
            # Extract count from result string "UPDATE N"
            stats["tasks_archived"] = int(tasks_result.split()[-1]) if tasks_result else 0

            # 2. Archive completed reminders older than 90 days
            reminders_cutoff = now - timedelta(days=90)
            reminders_result = await conn.execute(
                """
                UPDATE reminders
                SET archived = TRUE, updated_at = NOW()
                WHERE is_completed = TRUE
                  AND completed_at < $1
                  AND archived = FALSE
                """,
                reminders_cutoff
            )
            stats["reminders_archived"] = int(reminders_result.split()[-1]) if reminders_result else 0

            # 3. Archive past events older than 365 days
            events_cutoff = now - timedelta(days=365)
            events_result = await conn.execute(
                """
                UPDATE events
                SET archived = TRUE, updated_at = NOW()
                WHERE end_time < $1
                  AND archived = FALSE
                """,
                events_cutoff
            )
            stats["events_archived"] = int(events_result.split()[-1]) if events_result else 0

            # 4. Decay memory salience for unused memories
            # Reduce salience by 10% for memories not accessed in 30 days
            salience_cutoff = now - timedelta(days=30)
            memories_result = await conn.execute(
                """
                UPDATE memories
                SET salience_score = salience_score * 0.9,
                    updated_at = NOW()
                WHERE last_accessed_at < $1
                  AND salience_score > 0.1
                RETURNING id
                """,
                salience_cutoff
            )
            stats["memories_decayed"] = int(memories_result.split()[-1]) if memories_result else 0

            logger.info(
                f"Cleanup completed: {stats['tasks_archived']} tasks, "
                f"{stats['reminders_archived']} reminders, "
                f"{stats['events_archived']} events archived, "
                f"{stats['memories_decayed']} memories decayed"
            )

            return stats

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


# ============================================================================
# Health Check (Workflow 21)
# Schedule: Every 5 minutes
# ============================================================================

async def health_check() -> Dict[str, Any]:
    """
    Check system health and connectivity.

    Replaces n8n workflow: 21-health-check.json

    Logic:
    1. Check PostgreSQL connection
    2. Check Qdrant connection (future)
    3. Check Redis connection (future)
    4. Check Ollama connection (future)
    5. Return health status

    Returns:
        Dict with health check results
    """
    try:
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }

        # 1. Check PostgreSQL
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                health_status["checks"]["postgres"] = {
                    "status": "healthy" if result == 1 else "unhealthy",
                    "response_time_ms": 0  # Could add timing if needed
                }
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            health_status["checks"]["postgres"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"

        # 2. Check Qdrant (future implementation)
        # try:
        #     from qdrant_client import QdrantClient
        #     client = QdrantClient(host="qdrant", port=6333)
        #     collections = client.get_collections()
        #     health_status["checks"]["qdrant"] = {"status": "healthy"}
        # except Exception as e:
        #     health_status["checks"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
        #     health_status["status"] = "unhealthy"

        # 3. Check Redis (future implementation)
        # try:
        #     from utils.redis_client import get_redis_client
        #     redis = get_redis_client()
        #     await redis.ping()
        #     health_status["checks"]["redis"] = {"status": "healthy"}
        # except Exception as e:
        #     health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        #     health_status["status"] = "unhealthy"

        # 4. Check Ollama (future implementation)
        # try:
        #     import httpx
        #     async with httpx.AsyncClient() as client:
        #         response = await client.get("http://ollama:11434/api/tags")
        #         health_status["checks"]["ollama"] = {
        #             "status": "healthy" if response.status_code == 200 else "unhealthy"
        #         }
        # except Exception as e:
        #     health_status["checks"]["ollama"] = {"status": "unhealthy", "error": str(e)}
        #     health_status["status"] = "unhealthy"

        # Log if unhealthy
        if health_status["status"] == "unhealthy":
            logger.warning(f"Health check failed: {health_status}")
        else:
            logger.debug("Health check passed")

        return health_status

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
