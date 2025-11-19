"""
Database connection management.
"""

import asyncio
import asyncpg
from typing import Optional
from config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool with retry logic.

    FIX: Added retry logic with exponential backoff for database connection failures.

    Returns:
        asyncpg connection pool

    Raises:
        ConnectionError: If unable to connect after max retries
    """
    global _db_pool

    if _db_pool is not None:
        return _db_pool

    # FIX: Retry logic for database connection
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Attempting to connect to database (attempt {attempt + 1}/{max_retries}) "
                f"at {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            )

            _db_pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )

            logger.info("Database connection pool created successfully")
            return _db_pool

        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("All database connection attempts failed")
                raise ConnectionError(
                    f"Failed to connect to database after {max_retries} attempts: {str(e)}"
                )

    return _db_pool


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _db_pool

    if _db_pool is not None:
        logger.info("Closing database connection pool")
        await _db_pool.close()
        _db_pool = None
