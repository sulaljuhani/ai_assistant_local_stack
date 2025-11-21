"""
Document Tools

Tools for document embedding and vault management.

Replaces functionality from n8n workflows:
- 07-watch-vault.json (re-embed changed vault files)
- 15-watch-documents.json (embed general documents)
- 18-scheduled-vault-sync.json (scheduled vault sync)
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib
import asyncio
from datetime import datetime

from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger
from config import settings

logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""


def read_file_content(file_path: str) -> Optional[str]:
    """Read file content as text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap

    return chunks


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using Ollama.

    Args:
        text: Text to embed

    Returns:
        Embedding vector or None if failed
    """
    try:
        import httpx

        ollama_url = f"{settings.ollama_base_url}/api/embeddings"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"Ollama embedding failed: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Error generating embedding: {e}", exc_info=True)
        return None


async def store_in_qdrant(
    collection_name: str,
    point_id: str,
    vector: List[float],
    payload: Dict[str, Any]
) -> bool:
    """
    Store vector and payload in Qdrant.

    Args:
        collection_name: Qdrant collection name
        point_id: Unique point ID
        vector: Embedding vector
        payload: Metadata payload

    Returns:
        True if successful, False otherwise
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Ensure collection exists
        collections = client.get_collections().collections
        if not any(col.name == collection_name for col in collections):
            from qdrant_client.models import Distance, VectorParams
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

        # Upsert point
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

        return True

    except Exception as e:
        logger.error(f"Error storing in Qdrant: {e}", exc_info=True)
        return False


# ============================================================================
# Document Tools
# ============================================================================

@tool
async def embed_document(
    file_path: str,
    file_type: str,
    collection_name: str = "knowledge_base",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Embed a document and store in Qdrant knowledge base.

    Replaces n8n workflow: 15-watch-documents.json

    Args:
        file_path: Absolute path to the document
        file_type: File type (txt, md, pdf, json)
        collection_name: Qdrant collection name
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        metadata: Additional metadata

    Returns:
        Dict with embedding results
    """
    try:
        # Validate file exists
        if not Path(file_path).exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        # Read file content
        content = read_file_content(file_path)
        if not content:
            return {"success": False, "error": "Failed to read file content"}

        # Calculate file hash
        file_hash = calculate_file_hash(file_path)

        # Chunk document
        chunks = chunk_text(content, chunk_size, chunk_overlap)

        if not chunks:
            return {"success": False, "error": "No content to embed"}

        # Generate embeddings and store each chunk
        embedded_chunks = []

        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = await generate_embedding(chunk)

            if not embedding:
                logger.warning(f"Failed to generate embedding for chunk {i}")
                continue

            # Create point ID
            point_id = f"{file_hash}_{i}"

            # Create payload
            payload = {
                "file_path": file_path,
                "file_type": file_type,
                "file_hash": file_hash,
                "chunk_index": i,
                "chunk_total": len(chunks),
                "content": chunk,
                "embedded_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }

            # Store in Qdrant
            success = await store_in_qdrant(collection_name, point_id, embedding, payload)

            if success:
                embedded_chunks.append({
                    "chunk_index": i,
                    "point_id": point_id,
                    "content_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
                })

        logger.info(
            f"Embedded document: {file_path} - "
            f"{len(embedded_chunks)}/{len(chunks)} chunks stored"
        )

        return {
            "success": True,
            "file_path": file_path,
            "file_hash": file_hash,
            "total_chunks": len(chunks),
            "embedded_chunks": len(embedded_chunks),
            "collection": collection_name,
            "chunks": embedded_chunks
        }

    except Exception as e:
        logger.error(f"Error embedding document {file_path}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def reembed_vault_file(
    file_path: str,
    file_hash: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Re-embed a vault file if it has changed.

    Replaces n8n workflow: 07-watch-vault.json

    Args:
        file_path: Absolute path to the vault file
        file_hash: Optional file hash for change detection
        force: Force re-embedding even if hash unchanged

    Returns:
        Dict with re-embedding results
    """
    try:
        # Validate file exists
        if not Path(file_path).exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        # Calculate current file hash
        current_hash = calculate_file_hash(file_path)

        # Check if file changed
        if not force and file_hash and current_hash == file_hash:
            logger.debug(f"File unchanged, skipping: {file_path}")
            return {
                "success": True,
                "skipped": True,
                "reason": "File unchanged",
                "file_path": file_path,
                "file_hash": current_hash
            }

        # Get file type from extension
        file_ext = Path(file_path).suffix.lower().lstrip('.')
        if file_ext not in ['txt', 'md', 'json']:
            file_ext = 'txt'  # Default to txt

        # Embed document (vault files go to 'vault' collection)
        embed_fn = getattr(embed_document, "coroutine", None) or getattr(embed_document, "func", None) or embed_document

        result = await embed_fn(
            file_path=file_path,
            file_type=file_ext,
            collection_name="vault",
            metadata={
                "source": "vault",
                "previous_hash": file_hash
            }
        )

        # Store file record in database (best effort)
        if result.get("success"):
            try:
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO vault_files (file_path, file_hash, last_embedded, chunk_count)
                        VALUES ($1, $2, NOW(), $3)
                        ON CONFLICT (file_path)
                        DO UPDATE SET
                            file_hash = EXCLUDED.file_hash,
                            last_embedded = EXCLUDED.last_embedded,
                            chunk_count = EXCLUDED.chunk_count
                        """,
                        file_path,
                        current_hash,
                        result.get("embedded_chunks", 0)
                    )
            except Exception:
                logger.warning("vault_files table missing; skipping vault DB persistence")

        logger.info(f"Re-embedded vault file: {file_path}")

        return result

    except Exception as e:
        logger.error(f"Error re-embedding vault file {file_path}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def search_embedded_documents(
    query: str,
    collection_name: str = "knowledge_base",
    limit: int = 10,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search for similar documents in Qdrant.

    Args:
        query: Search query text
        collection_name: Qdrant collection to search
        limit: Number of results to return
        score_threshold: Minimum similarity score

    Returns:
        List of similar documents with scores
    """
    try:
        # Generate query embedding
        query_embedding = await generate_embedding(query)

        if not query_embedding:
            return []

        # Search Qdrant
        from qdrant_client import QdrantClient

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        documents = []
        for result in results:
            documents.append({
                "id": result.id,
                "score": result.score,
                "file_path": result.payload.get("file_path"),
                "content": result.payload.get("content"),
                "chunk_index": result.payload.get("chunk_index"),
                "metadata": result.payload
            })

        logger.info(f"Found {len(documents)} documents for query: {query[:50]}")

        return documents

    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        return []
