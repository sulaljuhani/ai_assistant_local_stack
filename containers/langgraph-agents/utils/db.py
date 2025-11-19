"""
Database connection management.
"""

import asyncpg
from typing import Optional
from config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool.

    Returns:
        asyncpg connection pool
    """
    global _db_pool

    if _db_pool is None:
        logger.info(f"Creating database connection pool to {settings.postgres_host}")
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


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _db_pool

    if _db_pool is not None:
        logger.info("Closing database connection pool")
        await _db_pool.close()
        _db_pool = None
