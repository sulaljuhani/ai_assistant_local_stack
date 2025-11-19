"""
Memory Router

API endpoints for OpenMemory operations - storing and searching conversation memories.

Replaces n8n workflows:
- 09-store-chat-turn.json (store chat turns)
- 10-search-and-summarize.json (search memories)
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from middleware.validation import StoreChatTurnRequest, SearchMemoriesRequest
from tools.memory import store_chat_turn, search_memories
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


# Response models
class StoreChatTurnResponse(BaseModel):
    """Store chat turn response model"""
    success: bool
    memory_id: int
    conversation_id: str
    sectors: List[str]
    vector_stored: bool


class MemoryResult(BaseModel):
    """Memory search result model"""
    memory_id: int
    score: float
    content: str
    sector: str
    role: str
    conversation_id: str
    salience_score: float
    created_at: str


class SearchMemoriesResponse(BaseModel):
    """Search memories response model"""
    success: bool
    query: str
    count: int
    results: List[MemoryResult]
    summary: Optional[str] = None


# ============================================================================
# Store Chat Turn
# ============================================================================

@router.post("/store", response_model=StoreChatTurnResponse)
async def store_chat_turn_endpoint(request: StoreChatTurnRequest):
    """
    Store a chat turn as a memory in OpenMemory.

    Replaces n8n workflow: 09-store-chat-turn.json

    This endpoint receives chat messages and:
    1. Creates/updates conversation record
    2. Classifies content into memory sectors (semantic, episodic, etc.)
    3. Stores memory in database
    4. Generates embeddings via Ollama
    5. Stores vectors in Qdrant for each sector
    6. Returns memory ID and classification

    The multi-sector approach allows flexible retrieval:
    - Semantic sector for facts and knowledge
    - Episodic sector for experiences and events
    - Procedural sector for how-tos and processes
    - Emotional sector for preferences and feelings
    - Reflective sector for insights and patterns

    Args:
        request: StoreChatTurnRequest with message details

    Returns:
        StoreChatTurnResponse with memory ID and sectors
    """
    try:
        logger.info(
            f"Store chat turn: user={request.user_id}, "
            f"role={request.role}, conversation={request.conversation_id}"
        )

        # Call the memory tool
        result = await store_chat_turn(
            user_id=request.user_id,
            role=request.role,
            content=request.content,
            conversation_id=request.conversation_id,
            conversation_title=request.conversation_title,
            source=request.source.value,
            salience_score=request.salience_score,
            metadata=request.metadata
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to store chat turn")
            )

        return StoreChatTurnResponse(
            success=True,
            memory_id=result["memory_id"],
            conversation_id=result["conversation_id"],
            sectors=result["sectors"],
            vector_stored=result.get("vector_stored", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in store endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to store chat turn: {str(e)}")


# ============================================================================
# Search Memories
# ============================================================================

@router.post("/search", response_model=SearchMemoriesResponse)
async def search_memories_endpoint(request: SearchMemoriesRequest):
    """
    Search memories with optional LLM summarization.

    Replaces n8n workflow: 10-search-and-summarize.json

    This endpoint performs semantic search across stored memories:
    1. Generates embedding for query
    2. Searches Qdrant for similar memory vectors
    3. Filters by user_id, conversation_id, sector if provided
    4. Optionally summarizes results using LLM

    Use cases:
    - Retrieve relevant context for conversations
    - Find past discussions on specific topics
    - Search within a specific conversation
    - Filter by memory type (sector)
    - Get AI-generated summaries of search results

    Args:
        request: SearchMemoriesRequest with query and filters

    Returns:
        SearchMemoriesResponse with results and optional summary
    """
    try:
        logger.info(f"Search memories: query='{request.query[:50]}', limit={request.limit}")

        # Call the memory tool
        result = await search_memories(
            query=request.query,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            sector=request.sector.value if request.sector else None,
            limit=request.limit,
            summarize=request.summarize,
            min_salience=request.min_salience
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to search memories")
            )

        # Format results
        memory_results = [
            MemoryResult(
                memory_id=r["memory_id"],
                score=r["score"],
                content=r["content"],
                sector=r["sector"],
                role=r["role"],
                conversation_id=r["conversation_id"],
                salience_score=r["salience_score"],
                created_at=r["created_at"]
            )
            for r in result["results"]
        ]

        return SearchMemoriesResponse(
            success=True,
            query=result["query"],
            count=result["count"],
            results=memory_results,
            summary=result.get("summary")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


# ============================================================================
# Memory Statistics
# ============================================================================

@router.get("/stats")
async def get_memory_stats(user_id: Optional[str] = None):
    """
    Get memory statistics.

    Args:
        user_id: Optional filter by user ID

    Returns:
        Memory statistics
    """
    try:
        from utils.db import get_db_pool

        pool = await get_db_pool()

        async with pool.acquire() as conn:
            if user_id:
                # User-specific stats
                total_memories = await conn.fetchval(
                    "SELECT COUNT(*) FROM memories WHERE user_id = $1",
                    user_id
                )

                total_conversations = await conn.fetchval(
                    "SELECT COUNT(DISTINCT conversation_id) FROM memories WHERE user_id = $1",
                    user_id
                )

                # Sector distribution
                sector_stats = await conn.fetch(
                    """
                    SELECT ms.sector, COUNT(*) as count
                    FROM memory_sectors ms
                    JOIN memories m ON ms.memory_id = m.id
                    WHERE m.user_id = $1
                    GROUP BY ms.sector
                    ORDER BY count DESC
                    """,
                    user_id
                )

            else:
                # Global stats
                total_memories = await conn.fetchval(
                    "SELECT COUNT(*) FROM memories"
                )

                total_conversations = await conn.fetchval(
                    "SELECT COUNT(DISTINCT id) FROM conversations"
                )

                # Sector distribution
                sector_stats = await conn.fetch(
                    """
                    SELECT sector, COUNT(*) as count
                    FROM memory_sectors
                    GROUP BY sector
                    ORDER BY count DESC
                    """
                )

            return {
                "total_memories": total_memories,
                "total_conversations": total_conversations,
                "sector_distribution": [
                    {"sector": row["sector"], "count": row["count"]}
                    for row in sector_stats
                ],
                "user_id": user_id
            }

    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {str(e)}")


@router.get("/conversations")
async def list_conversations(user_id: str, limit: int = 50, offset: int = 0):
    """
    List conversations for a user.

    Args:
        user_id: User ID
        limit: Number of conversations to return
        offset: Offset for pagination

    Returns:
        List of conversations
    """
    try:
        from utils.db import get_db_pool

        pool = await get_db_pool()

        async with pool.acquire() as conn:
            conversations = await conn.fetch(
                """
                SELECT
                    c.id,
                    c.title,
                    c.source,
                    c.created_at,
                    c.updated_at,
                    COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN memories m ON c.id = m.conversation_id
                WHERE c.user_id = $1
                GROUP BY c.id, c.title, c.source, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset
            )

            return {
                "conversations": [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "source": row["source"],
                        "message_count": row["message_count"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat()
                    }
                    for row in conversations
                ],
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")
