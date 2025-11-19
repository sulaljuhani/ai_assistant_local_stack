"""
Vector search tools using Qdrant for semantic queries.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)

# Global Qdrant client
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global _qdrant_client

    if _qdrant_client is None:
        logger.info(f"Creating Qdrant client connection to {settings.qdrant_url}")
        _qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            timeout=30,
        )
        logger.info("Qdrant client created successfully")

    return _qdrant_client


@tool
async def vector_search_foods(
    query: str,
    user_id: str,
    limit: int = 10,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Semantic search for similar foods using vector embeddings.

    Args:
        query: Search query (e.g., "something like Thai curry")
        user_id: User identifier for filtering
        limit: Maximum results to return
        score_threshold: Minimum similarity score (0-1)

    Returns:
        List of similar food entries with scores
    """
    try:
        client = get_qdrant_client()

        # Note: In production, you'd generate embeddings here
        # For now, we'll use Qdrant's search-by-text if available
        # or assume embeddings are pre-generated

        # Search in food_memories collection
        results = client.query(
            collection_name="food_memories",
            query_text=query,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit,
            score_threshold=score_threshold,
        )

        # Format results
        formatted_results = []
        for hit in results:
            formatted_results.append({
                "id": hit.id,
                "score": hit.score,
                "food_name": hit.payload.get("food_name"),
                "food_type": hit.payload.get("food_type"),
                "rating": hit.payload.get("rating"),
                "notes": hit.payload.get("notes"),
                "logged_at": hit.payload.get("logged_at"),
            })

        logger.info(f"Vector search found {len(formatted_results)} similar foods")
        return formatted_results

    except Exception as e:
        logger.error(f"Error in vector search for foods: {e}")
        # Return empty list on error rather than failing
        return []


@tool
async def vector_search_memories(
    query: str,
    user_id: str,
    limit: int = 5,
    score_threshold: float = 0.75
) -> List[Dict[str, Any]]:
    """
    Semantic search for memories and notes.

    Args:
        query: Search query
        user_id: User identifier
        limit: Maximum results
        score_threshold: Minimum similarity score

    Returns:
        List of relevant memories
    """
    try:
        client = get_qdrant_client()

        # Search in memories collection
        results = client.query(
            collection_name="memories",
            query_text=query,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit,
            score_threshold=score_threshold,
        )

        # Format results
        formatted_results = []
        for hit in results:
            formatted_results.append({
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content"),
                "sector": hit.payload.get("sector"),
                "created_at": hit.payload.get("created_at"),
                "tags": hit.payload.get("tags", []),
            })

        logger.info(f"Vector search found {len(formatted_results)} memories")
        return formatted_results

    except Exception as e:
        logger.error(f"Error in vector search for memories: {e}")
        return []
