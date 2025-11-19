"""
Redis client management for state persistence.
"""

import redis.asyncio as redis
from typing import Optional
from config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        logger.info(f"Creating Redis client connection to {settings.redis_host}")
        _redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("Redis client connected successfully")

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client is not None:
        logger.info("Closing Redis client connection")
        await _redis_client.close()
        _redis_client = None
