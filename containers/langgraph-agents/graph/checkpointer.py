"""
Redis-based checkpointer for state persistence.
"""

import json
import pickle
from typing import Optional, Any, Sequence
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple, CheckpointMetadata
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import ChannelVersions
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
        config: RunnableConfig,
    ) -> Optional[Checkpoint]:
        """
        Get checkpoint from Redis.

        Args:
            config: Configuration with thread_id

        Returns:
            Checkpoint if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        redis = await self._get_redis()
        key = self._get_key(thread_id)

        try:
            data = await redis.get(key)
            if data:
                checkpoint = pickle.loads(data.encode('latin1'))
                logger.debug(f"Retrieved checkpoint for thread {thread_id}")
                return checkpoint
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")

        return None

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """
        Get checkpoint tuple from Redis.

        Args:
            config: Configuration with thread_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        redis = await self._get_redis()
        key = self._get_key(thread_id)

        try:
            data = await redis.get(key)
            if data:
                checkpoint = pickle.loads(data.encode('latin1'))
                logger.debug(f"Retrieved checkpoint tuple for thread {thread_id}")

                # Return CheckpointTuple with required fields
                # Initialize metadata with step counter
                metadata = CheckpointMetadata(
                    source="input",
                    step=getattr(checkpoint, "step", 0),
                    writes={},
                    parents={}
                )

                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=None,
                    pending_writes=None
                )
        except Exception as e:
            logger.error(f"Error retrieving checkpoint tuple: {e}")

        return None

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """
        Save checkpoint to Redis.

        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint to save
            metadata: Checkpoint metadata
            new_versions: Channel versions

        Returns:
            Updated RunnableConfig
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, skipping checkpoint save")
            return config

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

        return config

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = '',
    ) -> None:
        """
        Store pending writes to Redis.

        Args:
            config: Configuration with thread_id
            writes: Sequence of (channel, value) tuples to write
            task_id: Task identifier
            task_path: Optional task path
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, skipping writes")
            return

        redis = await self._get_redis()
        key = f"checkpoint:{thread_id}:writes:{task_id}"

        try:
            # Serialize writes
            data = pickle.dumps(writes).decode('latin1')

            # Save with shorter TTL (writes are temporary)
            await redis.setex(
                key,
                3600,  # 1 hour TTL for pending writes
                data
            )

            logger.debug(f"Saved {len(writes)} pending writes for thread {thread_id}, task {task_id}")
        except Exception as e:
            logger.error(f"Error saving pending writes: {e}")

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
