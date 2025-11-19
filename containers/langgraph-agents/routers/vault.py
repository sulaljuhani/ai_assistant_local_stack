"""
Vault Router

API endpoints for Obsidian vault file management and embedding.
Replaces n8n workflow: 07-watch-vault.json
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from middleware.validation import ReembedFileRequest, SuccessResponse
from tools.documents import reembed_vault_file
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/vault", tags=["vault"])


# Response models
class ReembedResponse(BaseModel):
    """Re-embed response model"""
    success: bool
    skipped: bool = False
    reason: Optional[str] = None
    file_path: str
    file_hash: str
    total_chunks: Optional[int] = None
    embedded_chunks: Optional[int] = None
    collection: Optional[str] = None


# ============================================================================
# Re-embed Vault File
# ============================================================================

@router.post("/reembed", response_model=ReembedResponse)
async def reembed_file(request: ReembedFileRequest):
    """
    Re-embed a vault file if it has changed.

    Replaces n8n workflow: 07-watch-vault.json

    This endpoint is called by the vault watcher script when a file changes.

    Logic:
    1. Receive file_path and optional file_hash
    2. Calculate current file hash
    3. If hash changed (or force=True), re-embed the file:
       - Read file content
       - Generate embeddings
       - Store in Qdrant 'vault' collection
       - Update database record
    4. Return embedding results

    Args:
        request: ReembedFileRequest with file_path, file_hash, force

    Returns:
        ReembedResponse with embedding status
    """
    try:
        logger.info(f"Re-embed request for: {request.file_path}")

        # Call the document tool
        result = await reembed_vault_file(
            file_path=request.file_path,
            file_hash=request.file_hash,
            force=request.force
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to re-embed file")
            )

        # Check if skipped
        if result.get("skipped"):
            return ReembedResponse(
                success=True,
                skipped=True,
                reason=result.get("reason"),
                file_path=result["file_path"],
                file_hash=result["file_hash"]
            )

        # Return embedding results
        return ReembedResponse(
            success=True,
            file_path=result["file_path"],
            file_hash=result["file_hash"],
            total_chunks=result.get("total_chunks"),
            embedded_chunks=result.get("embedded_chunks"),
            collection=result.get("collection")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reembed endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to re-embed file: {str(e)}")


@router.post("/sync")
async def trigger_vault_sync():
    """
    Manually trigger a full vault sync.

    This will schedule an immediate vault sync job.

    Returns:
        Success message
    """
    try:
        from services.scheduler import trigger_job

        trigger_job('vault_sync')

        logger.info("Manually triggered vault sync")

        return {
            "success": True,
            "message": "Vault sync triggered successfully"
        }

    except Exception as e:
        logger.error(f"Error triggering vault sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger vault sync: {str(e)}")


@router.get("/status")
async def get_vault_status():
    """
    Get vault embedding status.

    Returns statistics about embedded vault files.

    Returns:
        Vault status information
    """
    try:
        from utils.db import get_db_pool

        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Get total files
            total_files = await conn.fetchval(
                "SELECT COUNT(*) FROM vault_files"
            )

            # Get recently embedded files
            recent_files = await conn.fetch(
                """
                SELECT file_path, file_hash, last_embedded, chunk_count
                FROM vault_files
                ORDER BY last_embedded DESC
                LIMIT 10
                """
            )

            # Get total chunks
            total_chunks = await conn.fetchval(
                "SELECT SUM(chunk_count) FROM vault_files"
            ) or 0

            return {
                "total_files": total_files,
                "total_chunks": total_chunks,
                "recent_files": [
                    {
                        "file_path": row["file_path"],
                        "file_hash": row["file_hash"],
                        "last_embedded": row["last_embedded"].isoformat(),
                        "chunk_count": row["chunk_count"]
                    }
                    for row in recent_files
                ]
            }

    except Exception as e:
        logger.error(f"Error getting vault status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get vault status: {str(e)}")
