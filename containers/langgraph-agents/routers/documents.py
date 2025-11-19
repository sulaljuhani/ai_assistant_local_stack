"""
Documents Router

API endpoints for general document embedding and search.
Replaces n8n workflow: 15-watch-documents.json
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path

from middleware.validation import EmbedDocumentRequest
from tools.documents import embed_document, search_embedded_documents
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


# Response models
class EmbedResponse(BaseModel):
    """Embed response model"""
    success: bool
    file_path: str
    file_hash: str
    total_chunks: int
    embedded_chunks: int
    collection: str


class SearchResult(BaseModel):
    """Search result model"""
    id: str
    score: float
    file_path: Optional[str]
    content: str
    chunk_index: Optional[int]
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    count: int


# ============================================================================
# Embed Document
# ============================================================================

@router.post("/embed", response_model=EmbedResponse)
async def embed_document_endpoint(request: EmbedDocumentRequest):
    """
    Embed a document and store in Qdrant knowledge base.

    Replaces n8n workflow: 15-watch-documents.json

    This endpoint processes documents (txt, pdf, json, md), chunks them,
    generates embeddings, and stores them in Qdrant.

    Logic:
    1. Receive file_path and file_type
    2. Read file content
    3. Chunk document (default: 1000 chars, 200 overlap)
    4. Generate embeddings for each chunk using Ollama
    5. Store in Qdrant knowledge_base collection
    6. Return embedding statistics

    Args:
        request: EmbedDocumentRequest with file details

    Returns:
        EmbedResponse with embedding results
    """
    try:
        logger.info(f"Embed request for: {request.file_path} ({request.file_type})")

        # Call the document tool
        result = await embed_document(
            file_path=request.file_path,
            file_type=request.file_type,
            collection_name=request.collection_name,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            metadata=request.metadata
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to embed document")
            )

        return EmbedResponse(
            success=True,
            file_path=result["file_path"],
            file_hash=result["file_hash"],
            total_chunks=result["total_chunks"],
            embedded_chunks=result["embedded_chunks"],
            collection=result["collection"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in embed endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to embed document: {str(e)}")


@router.post("/upload-and-embed")
async def upload_and_embed(
    file: UploadFile = File(...),
    collection_name: str = Form("knowledge_base"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """
    Upload a document and embed it.

    This endpoint accepts a file upload, saves it temporarily,
    embeds it, and returns the results.

    Args:
        file: Uploaded file
        collection_name: Qdrant collection name
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        Embedding results
    """
    try:
        import tempfile
        import shutil

        # Validate file type
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        if file_ext not in ['txt', 'md', 'json', 'pdf']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported: txt, md, json, pdf"
            )

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_file_path = tmp_file.name

        logger.info(f"Uploaded file saved to: {tmp_file_path}")

        # Embed document
        result = await embed_document(
            file_path=tmp_file_path,
            file_type=file_ext,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata={
                "original_filename": file.filename,
                "uploaded": True
            }
        )

        # Clean up temporary file
        try:
            Path(tmp_file_path).unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temporary file: {e}")

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to embed document")
            )

        return {
            "success": True,
            "filename": file.filename,
            "file_hash": result["file_hash"],
            "total_chunks": result["total_chunks"],
            "embedded_chunks": result["embedded_chunks"],
            "collection": result["collection"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload-and-embed endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload and embed: {str(e)}")


# ============================================================================
# Search Documents
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    query: str = Form(...),
    collection_name: str = Form("knowledge_base"),
    limit: int = Form(10),
    score_threshold: float = Form(0.7)
):
    """
    Search for similar documents in the knowledge base.

    Uses semantic search to find relevant document chunks.

    Args:
        query: Search query text
        collection_name: Qdrant collection to search
        limit: Number of results to return
        score_threshold: Minimum similarity score

    Returns:
        Search results with scores
    """
    try:
        logger.info(f"Search request: '{query}' in {collection_name}")

        # Search using the document tool
        results = await search_embedded_documents(
            query=query,
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        search_results = [
            SearchResult(
                id=str(result["id"]),
                score=result["score"],
                file_path=result.get("file_path"),
                content=result["content"],
                chunk_index=result.get("chunk_index"),
                metadata=result["metadata"]
            )
            for result in results
        ]

        return SearchResponse(
            query=query,
            results=search_results,
            count=len(search_results)
        )

    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")


@router.get("/collections")
async def list_collections():
    """
    List all Qdrant collections and their stats.

    Returns:
        List of collections with metadata
    """
    try:
        from qdrant_client import QdrantClient
        from config import settings

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Get all collections
        collections = client.get_collections().collections

        collection_info = []
        for collection in collections:
            info = client.get_collection(collection.name)
            collection_info.append({
                "name": collection.name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status
            })

        return {
            "collections": collection_info,
            "total": len(collection_info)
        }

    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")
