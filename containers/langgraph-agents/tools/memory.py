"""
Memory Tools

Tools for OpenMemory operations: storing, searching, and managing conversation memories.

Replaces functionality from n8n workflows:
- 09-store-chat-turn.json (store chat turns as memories)
- 10-search-and-summarize.json (search memories with optional summarization)
"""

from typing import Dict, Any, List, Optional, Callable, TypeVar
from datetime import datetime
import uuid
import asyncio

from langchain_core.tools import tool
import json
from utils.db import get_db_pool
from utils.logging import get_logger
from config import settings

logger = get_logger(__name__)
T = TypeVar("T")


# ============================================================================
# Helper Functions
# ============================================================================

def classify_memory_sectors(content: str, role: str) -> List[str]:
    """
    Classify memory content into sectors using heuristic rules.

    Sectors:
    - semantic: Facts, definitions, explanations, concepts
    - episodic: Events, experiences, personal stories, time-specific info
    - procedural: How-tos, steps, instructions, processes
    - emotional: Preferences, feelings, opinions, reactions
    - reflective: Insights, patterns, meta-cognition, learning

    Args:
        content: Message content
        role: Message role (user, assistant, system)

    Returns:
        List of applicable sector names
    """
    content_lower = content.lower()
    sectors = []

    # Semantic indicators (facts, definitions)
    semantic_keywords = ['is', 'are', 'means', 'defined as', 'refers to', 'called', 'known as']
    if any(keyword in content_lower for keyword in semantic_keywords):
        sectors.append('semantic')

    # Episodic indicators (events, experiences)
    episodic_keywords = ['yesterday', 'today', 'last week', 'happened', 'did', 'went', 'was', 'remember when']
    if any(keyword in content_lower for keyword in episodic_keywords):
        sectors.append('episodic')

    # Procedural indicators (how-tos, steps)
    procedural_keywords = ['how to', 'step', 'first', 'then', 'next', 'finally', 'process', 'method']
    if any(keyword in content_lower for keyword in procedural_keywords):
        sectors.append('procedural')

    # Emotional indicators (preferences, feelings)
    emotional_keywords = ['like', 'love', 'hate', 'feel', 'enjoy', 'prefer', 'want', 'wish', 'hope']
    if any(keyword in content_lower for keyword in emotional_keywords):
        sectors.append('emotional')

    # Reflective indicators (insights, patterns)
    reflective_keywords = ['realize', 'understand', 'learned', 'insight', 'pattern', 'think about', 'consider']
    if any(keyword in content_lower for keyword in reflective_keywords):
        sectors.append('reflective')

    # Default sector based on role
    if not sectors:
        if role == 'user':
            sectors.append('episodic')  # User messages often describe experiences
        else:
            sectors.append('semantic')  # Assistant messages often provide information

    return sectors


async def _with_qdrant_retry(operation: str, func: Callable[[], T], retries: int = 2, base_delay: float = 0.5) -> T:
    """
    Execute a Qdrant operation with simple retry/backoff.

    Args:
        operation: Name of the operation for logging
        func: Callable to execute
        retries: Number of retries on failure
        base_delay: Initial delay between retries

    Returns:
        Result of the callable if successful

    Raises:
        Last exception if all attempts fail
    """
    last_exception: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as exc:  # noqa: PERF203
            last_exception = exc
            logger.warning(
                f"Qdrant {operation} failed (attempt {attempt + 1}/{retries + 1}): {exc}"
            )
            if attempt < retries:
                await asyncio.sleep(base_delay * (2**attempt))

    logger.error(f"Qdrant {operation} failed after {retries + 1} attempts", exc_info=True)
    raise last_exception  # type: ignore[misc]


async def generate_memory_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for memory content using Ollama.

    Args:
        text: Text to embed

    Returns:
        Embedding vector or None if failed
    """
    try:
        import httpx

        ollama_url = f"{settings.ollama_embed_url}/api/embeddings"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": settings.ollama_embed_model,
                    "prompt": text
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"Ollama embedding failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"Error generating memory embedding: {e}", exc_info=True)
        return None


async def store_memory_vector(
    memory_id: int,
    vector: List[float],
    sectors: List[str],
    content: str,
    metadata: Dict[str, Any]
) -> bool:
    """
    Store memory vector in Qdrant with multi-sector support.

    Creates one point per sector, allowing sector-specific retrieval.

    Args:
        memory_id: Memory ID from database
        vector: Embedding vector
        sectors: List of applicable sectors
        content: Memory content
        metadata: Additional metadata

    Returns:
        True if successful, False otherwise
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, Distance, VectorParams

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collection_name = settings.memory_collection_name

        # Ensure memories collection exists
        collections = await _with_qdrant_retry(
            "list collections",
            lambda: client.get_collections().collections
        )

        if not any(col.name == collection_name for col in collections):
            await _with_qdrant_retry(
                "create collection",
                lambda: client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE)
                )
            )
            logger.info("Created Qdrant collection: %s", collection_name)

        # Create one point per sector for flexible retrieval
        points = []
        for idx, sector in enumerate(sectors, start=1):
            point_id = memory_id * 10 + idx
            payload = {
                "memory_id": memory_id,
                "sector": sector,
                "content": content,
                **metadata
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        # Upsert all points
        await _with_qdrant_retry("upsert memory vectors", lambda: client.upsert(collection_name=collection_name, points=points))

        return True

    except Exception as e:
        logger.error(f"Error storing memory vector: {e}", exc_info=True)
        return False


# ============================================================================
# Memory Tools
# ============================================================================

@tool
async def store_chat_turn(
    user_id: str,
    role: str,
    content: str,
    conversation_id: Optional[str] = None,
    conversation_title: str = "Untitled Conversation",
    source: str = "chat",
    salience_score: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store a chat turn as a memory in OpenMemory.

    Replaces n8n workflow: 09-store-chat-turn.json

    Logic:
    1. Upsert conversation record
    2. Classify content into memory sectors
    3. Create memory record in database
    4. Generate embedding with Ollama
    5. Store vectors in Qdrant (one per sector)
    6. Return memory ID and sectors

    Args:
        user_id: User identifier
        role: Message role (user, assistant, system)
        content: Message content
        conversation_id: Optional conversation UUID (auto-generated if not provided)
        conversation_title: Conversation title
        source: Memory source (chat, chatgpt, claude, gemini, anythingllm)
        salience_score: Initial salience score (0.0-1.0)
        metadata: Additional metadata

    Returns:
        Dict with memory ID, sectors, and status
    """
    try:
        pool = await get_db_pool()

        # Generate conversation_id if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            # 1. Upsert conversation
            conversation = await conn.fetchrow(
                """
                INSERT INTO conversations (id, user_id, title, source, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    updated_at = NOW()
                RETURNING id, title
                """,
                conversation_id,
                user_id,
                conversation_title,
                source
            )

            # 2. Classify content into sectors
            sectors = classify_memory_sectors(content, role)

            # 3. Create memory record
            memory = await conn.fetchrow(
                """
                INSERT INTO memories (
                    conversation_id,
                    user_id,
                    role,
                    content,
                    salience_score,
                    source,
                    metadata,
                    created_at,
                    updated_at,
                    last_accessed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW(), NOW())
                RETURNING id, conversation_id, role, content, salience_score
                """,
                conversation_id,
                user_id,
                role,
                content,
                salience_score,
                source,
                json.dumps(metadata or {})
            )

            memory_id = memory['id']

            # 4. Insert sector records
            for sector in sectors:
                await conn.execute(
                    """
                    INSERT INTO memory_sectors (memory_id, sector, weight)
                    VALUES ($1, $2, $3)
                    """,
                    memory_id,
                    sector,
                    1.0 / len(sectors)  # Equal weight distribution
                )

            # 5. Generate embedding
            embedding = await generate_memory_embedding(content)

            if not embedding:
                logger.warning(f"Failed to generate embedding for memory {memory_id}")
                return {
                    "success": False,
                    "error": "Failed to generate embedding",
                    "memory_id": memory_id,
                    "conversation_id": conversation_id,
                    "sectors": sectors
                }

            # 6. Store in Qdrant
            vector_stored = await store_memory_vector(
                memory_id=memory_id,
                vector=embedding,
                sectors=sectors,
                content=content,
                metadata={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": role,
                    "source": source,
                    "salience_score": salience_score,
                    "created_at": datetime.utcnow().isoformat()
                }
            )

            if not vector_stored:
                logger.warning(f"Failed to store vectors for memory {memory_id}")

            logger.info(
                f"Stored chat turn: memory_id={memory_id}, "
                f"sectors={sectors}, conversation={conversation_id}"
            )

            return {
                "success": True,
                "memory_id": memory_id,
                "conversation_id": conversation_id,
                "sectors": sectors,
                "vector_stored": vector_stored
            }

    except Exception as e:
        logger.error(f"Error storing chat turn: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def search_memories(
    query: str,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 10,
    summarize: bool = False,
    min_salience: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search memories with optional LLM summarization.

    Replaces n8n workflow: 10-search-and-summarize.json

    Logic:
    1. Generate query embedding
    2. Search Qdrant for similar memories
    3. Filter by user_id, conversation_id, sector if provided
    4. If summarize=true, send to LLM for summarization
    5. Return results (with or without summary)

    Args:
        query: Search query
        user_id: Optional filter by user ID
        conversation_id: Optional filter by conversation ID
        sector: Optional filter by sector
        limit: Number of results to return
        summarize: Whether to summarize results with LLM
        min_salience: Minimum salience score filter

    Returns:
        Dict with search results and optional summary
    """
    try:
        # 1. Generate query embedding
        query_embedding = await generate_memory_embedding(query)

        if not query_embedding:
            return {
                "success": False,
                "error": "Failed to generate query embedding",
                "results": []
            }

        # 2. Search Qdrant
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import UnexpectedResponse
        from qdrant_client.models import Filter, FieldCondition, MatchValue, VectorParams, Distance

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collection_name = settings.memory_collection_name

        # Build filter
        must_conditions = []

        if user_id:
            must_conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )

        if conversation_id:
            must_conditions.append(
                FieldCondition(key="conversation_id", match=MatchValue(value=conversation_id))
            )

        if sector:
            must_conditions.append(
                FieldCondition(key="sector", match=MatchValue(value=sector))
            )

        if min_salience:
            must_conditions.append(
                FieldCondition(key="salience_score", range={"gte": min_salience})
            )

        search_filter = Filter(must=must_conditions) if must_conditions else None

        def ensure_collection():
            collections = client.get_collections().collections
            if not any(col.name == collection_name for col in collections):
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=len(query_embedding), distance=Distance.COSINE)
                )

        ensure_collection()

        try:
            search_results = await _with_qdrant_retry(
                "vector search",
                lambda: client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=search_filter,
                    limit=limit,
                    score_threshold=0.5
                )
            )
        except UnexpectedResponse as e:
            if "doesn't exist" in str(e) or "OutputTooSmall" in str(e):
                logger.warning("Recreating Qdrant collection %s after search error", collection_name)
                client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=len(query_embedding), distance=Distance.COSINE)
                )
                search_results = client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=search_filter,
                    limit=limit,
                    score_threshold=0.5
                )
            else:
                logger.error(f"Qdrant search failed: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Qdrant search failed: {e}",
                    "query": query,
                    "count": 0,
                    "results": [],
                    "summary": None
                }
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Qdrant search failed: {e}",
                "query": query,
                "count": 0,
                "results": [],
                "summary": None
            }

        # Format results
        results = []
        for result in search_results:
            results.append({
                "memory_id": result.payload.get("memory_id"),
                "score": result.score,
                "content": result.payload.get("content"),
                "sector": result.payload.get("sector"),
                "role": result.payload.get("role"),
                "conversation_id": result.payload.get("conversation_id"),
                "salience_score": result.payload.get("salience_score"),
                "created_at": result.payload.get("created_at")
            })

        logger.info(f"Found {len(results)} memories for query: {query[:50]}")

        # 3. Optionally summarize results
        summary = None
        if summarize and results:
            try:
                # Concatenate top results
                combined_content = "\n\n".join([r["content"] for r in results[:5]])

                # Call LLM for summarization
                from utils.llm import get_agent_llm

                llm = get_agent_llm(temperature=0.3)

                summary_prompt = f"""Summarize the following memories related to the query "{query}":

{combined_content}

Provide a concise summary highlighting the key points."""

                summary_response = await llm.ainvoke(summary_prompt)
                summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)

                logger.info(f"Generated summary for {len(results)} memories")

            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                summary = None

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error searching memories: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
        }
