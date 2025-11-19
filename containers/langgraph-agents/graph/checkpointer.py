"""
Redis-based checkpointer for state persistence.
"""

import json
import pickle
from typing import Optional, Any
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
from config import settings
from utils.redis_client import get_redis_client
from utils.logging import get_logger

logger = get_logger(__name__)


class RedisCheckpointSaver(BaseCheckpointSaver):
    """
    Redis-based checkpoint saver for LangGraph state persistence.

    Stores conversation state in Redis with TTL for automatic cleanup.
    """

    def __init__(self):
        """Initialize Redis checkpointer."""
        super().__init__()
        self.redis_client = None

    async def _get_redis(self):
        """Get Redis client lazily."""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        return self.redis_client

    def _get_key(self, thread_id: str, checkpoint_id: Optional[str] = None) -> str:
        """Generate Redis key for checkpoint."""
        if checkpoint_id:
            return f"checkpoint:{thread_id}:{checkpoint_id}"
        return f"checkpoint:{thread_id}:latest"

    async def aget(
        self,
        config: dict,
        *,
        checkpoint_id: Optional[str] = None,
    ) -> Optional[Checkpoint]:
        """
        Get checkpoint from Redis.

        Args:
            config: Configuration with thread_id
            checkpoint_id: Optional specific checkpoint ID

        Returns:
            Checkpoint if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        redis = await self._get_redis()
        key = self._get_key(thread_id, checkpoint_id)

        try:
            data = await redis.get(key)
            if data:
                checkpoint = pickle.loads(data.encode('latin1'))
                logger.debug(f"Retrieved checkpoint for thread {thread_id}")
                return checkpoint
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")

        return None

    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
    ) -> None:
        """
        Save checkpoint to Redis.

        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint to save
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, skipping checkpoint save")
            return

        redis = await self._get_redis()
        key = self._get_key(thread_id)

        try:
            # Serialize checkpoint
            data = pickle.dumps(checkpoint).decode('latin1')

            # Save with TTL
            await redis.setex(
                key,
                settings.state_ttl_seconds,
                data
            )

            logger.debug(f"Saved checkpoint for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    def get(
        self,
        config: dict,
        *,
        checkpoint_id: Optional[str] = None,
    ) -> Optional[Checkpoint]:
        """Synchronous get (not implemented)."""
        raise NotImplementedError("Use aget instead")

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
    ) -> None:
        """Synchronous put (not implemented)."""
        raise NotImplementedError("Use aput instead")

    async def adelete(self, thread_id: str) -> None:
        """
        Delete all checkpoints for a thread.

        Args:
            thread_id: Thread identifier
        """
        redis = await self._get_redis()
        pattern = f"checkpoint:{thread_id}:*"

        try:
            # Find and delete all keys matching pattern
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            if deleted > 0:
                logger.info(f"Deleted {deleted} checkpoints for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error deleting checkpoints: {e}")
