"""
Imports Router

API endpoints for importing chat history exports from various AI services.

Replaces n8n workflows:
- 16-import-claude-export.json (Claude conversation exports)
- 17-import-gemini-export.json (Gemini/Google Takeout exports)
- 19-import-chatgpt-export.json (ChatGPT conversation exports)
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import json
from datetime import datetime

from middleware.validation import ImportChatExportRequest
from tools.memory import store_chat_turn
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/import", tags=["imports"])


# Response models
class ImportResponse(BaseModel):
    """Import response model"""
    success: bool
    conversations_imported: int
    messages_imported: int
    errors: List[str]
    timestamp: str


# ============================================================================
# Import Claude Export
# ============================================================================

@router.post("/claude", response_model=ImportResponse)
async def import_claude_export(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    default_salience: float = Form(0.3)
):
    """
    Import Claude conversation export.

    Replaces n8n workflow: 16-import-claude-export.json

    Expected JSON structure:
    {
      "conversations": [
        {
          "uuid": "conv-id",
          "name": "Conversation title",
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:00:00Z",
          "chat_messages": [
            {
              "uuid": "msg-id",
              "text": "Message content",
              "sender": "human" | "assistant",
              "created_at": "2024-01-01T00:00:00Z"
            }
          ]
        }
      ]
    }

    Args:
        file: Claude export JSON file
        user_id: User ID to associate memories with
        default_salience: Default salience score for imported memories

    Returns:
        Import statistics
    """
    try:
        # Read and parse JSON
        content = await file.read()
        data = json.loads(content)

        stats = {
            "conversations_imported": 0,
            "messages_imported": 0,
            "errors": []
        }

        if "conversations" not in data:
            raise HTTPException(
                status_code=400,
                detail="Invalid Claude export format: missing 'conversations' key"
            )

        conversations = data["conversations"]
        logger.info(f"Importing {len(conversations)} Claude conversations for user {user_id}")

        # Process each conversation
        for conv in conversations:
            try:
                conversation_id = conv.get("uuid")
                conversation_title = conv.get("name", "Untitled Conversation")
                messages = conv.get("chat_messages", [])

                if not messages:
                    continue

                # Store each message as a memory
                for msg in messages:
                    try:
                        # Map sender to role
                        sender = msg.get("sender", "human")
                        role = "user" if sender == "human" else "assistant"

                        # Store chat turn
                        result = await store_chat_turn(
                            user_id=user_id,
                            role=role,
                            content=msg.get("text", ""),
                            conversation_id=conversation_id,
                            conversation_title=conversation_title,
                            source="claude",
                            salience_score=default_salience,
                            metadata={
                                "imported": True,
                                "original_message_id": msg.get("uuid"),
                                "original_created_at": msg.get("created_at")
                            }
                        )

                        if result.get("success"):
                            stats["messages_imported"] += 1
                        else:
                            stats["errors"].append(
                                f"Failed to import message {msg.get('uuid')}: {result.get('error')}"
                            )

                    except Exception as e:
                        logger.error(f"Error importing message: {e}")
                        stats["errors"].append(f"Message error: {str(e)}")

                stats["conversations_imported"] += 1
                logger.debug(f"Imported Claude conversation: {conversation_id}")

            except Exception as e:
                logger.error(f"Error importing conversation: {e}")
                stats["errors"].append(f"Conversation error: {str(e)}")

        logger.info(
            f"Claude import complete: {stats['conversations_imported']} conversations, "
            f"{stats['messages_imported']} messages"
        )

        return ImportResponse(
            success=True,
            conversations_imported=stats["conversations_imported"],
            messages_imported=stats["messages_imported"],
            errors=stats["errors"],
            timestamp=datetime.utcnow().isoformat()
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error importing Claude export: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")


# ============================================================================
# Import Gemini Export
# ============================================================================

@router.post("/gemini", response_model=ImportResponse)
async def import_gemini_export(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    default_salience: float = Form(0.3)
):
    """
    Import Gemini (Google Takeout) conversation export.

    Replaces n8n workflow: 17-import-gemini-export.json

    Expected JSON structure (similar to Claude):
    {
      "conversations": [
        {
          "id": "conv-id",
          "title": "Conversation title",
          "messages": [
            {
              "role": "user" | "model",
              "text": "Message content",
              "timestamp": "2024-01-01T00:00:00Z"
            }
          ]
        }
      ]
    }

    Args:
        file: Gemini export JSON file
        user_id: User ID to associate memories with
        default_salience: Default salience score for imported memories

    Returns:
        Import statistics
    """
    try:
        # Read and parse JSON
        content = await file.read()
        data = json.loads(content)

        stats = {
            "conversations_imported": 0,
            "messages_imported": 0,
            "errors": []
        }

        # Handle different possible formats
        conversations = []
        if "conversations" in data:
            conversations = data["conversations"]
        elif isinstance(data, list):
            conversations = data
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid Gemini export format"
            )

        logger.info(f"Importing {len(conversations)} Gemini conversations for user {user_id}")

        # Process each conversation
        for conv in conversations:
            try:
                conversation_id = conv.get("id") or conv.get("conversation_id")
                conversation_title = conv.get("title") or conv.get("name", "Untitled Conversation")
                messages = conv.get("messages", [])

                if not messages:
                    continue

                # Store each message as a memory
                for msg in messages:
                    try:
                        # Map role
                        msg_role = msg.get("role", "user")
                        role = "assistant" if msg_role == "model" else "user"

                        # Get content (try different field names)
                        content = msg.get("text") or msg.get("content") or msg.get("message", "")

                        if not content:
                            continue

                        # Store chat turn
                        result = await store_chat_turn(
                            user_id=user_id,
                            role=role,
                            content=content,
                            conversation_id=conversation_id,
                            conversation_title=conversation_title,
                            source="gemini",
                            salience_score=default_salience,
                            metadata={
                                "imported": True,
                                "original_timestamp": msg.get("timestamp")
                            }
                        )

                        if result.get("success"):
                            stats["messages_imported"] += 1
                        else:
                            stats["errors"].append(
                                f"Failed to import message: {result.get('error')}"
                            )

                    except Exception as e:
                        logger.error(f"Error importing message: {e}")
                        stats["errors"].append(f"Message error: {str(e)}")

                stats["conversations_imported"] += 1
                logger.debug(f"Imported Gemini conversation: {conversation_id}")

            except Exception as e:
                logger.error(f"Error importing conversation: {e}")
                stats["errors"].append(f"Conversation error: {str(e)}")

        logger.info(
            f"Gemini import complete: {stats['conversations_imported']} conversations, "
            f"{stats['messages_imported']} messages"
        )

        return ImportResponse(
            success=True,
            conversations_imported=stats["conversations_imported"],
            messages_imported=stats["messages_imported"],
            errors=stats["errors"],
            timestamp=datetime.utcnow().isoformat()
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error importing Gemini export: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")


# ============================================================================
# Import ChatGPT Export
# ============================================================================

@router.post("/chatgpt", response_model=ImportResponse)
async def import_chatgpt_export(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    default_salience: float = Form(0.3)
):
    """
    Import ChatGPT conversation export.

    Replaces n8n workflow: 19-import-chatgpt-export.json

    Expected JSON structure:
    [
      {
        "id": "conv-id",
        "title": "Conversation title",
        "create_time": 1234567890,
        "mapping": {
          "message_id": {
            "id": "message_id",
            "message": {
              "id": "message_id",
              "author": {"role": "user" | "assistant"},
              "content": {"content_type": "text", "parts": ["Message text"]},
              "create_time": 1234567890
            }
          }
        }
      }
    ]

    Args:
        file: ChatGPT export JSON file
        user_id: User ID to associate memories with
        default_salience: Default salience score for imported memories

    Returns:
        Import statistics
    """
    try:
        # Read and parse JSON
        content = await file.read()
        data = json.loads(content)

        stats = {
            "conversations_imported": 0,
            "messages_imported": 0,
            "errors": []
        }

        # ChatGPT exports are typically a list of conversations
        if not isinstance(data, list):
            data = [data]

        logger.info(f"Importing {len(data)} ChatGPT conversations for user {user_id}")

        # Process each conversation
        for conv in data:
            try:
                conversation_id = conv.get("id") or conv.get("conversation_id")
                conversation_title = conv.get("title", "Untitled Conversation")
                mapping = conv.get("mapping", {})

                if not mapping:
                    continue

                # Traverse the mapping tree to extract messages in order
                messages = []
                for msg_id, msg_data in mapping.items():
                    if msg_data and "message" in msg_data:
                        message = msg_data["message"]
                        if message and message.get("content"):
                            messages.append(message)

                # Sort by create_time if available
                messages.sort(key=lambda m: m.get("create_time", 0))

                # Store each message as a memory
                for msg in messages:
                    try:
                        # Get role
                        author = msg.get("author", {})
                        role = author.get("role", "user")

                        # Get content
                        content_obj = msg.get("content", {})
                        parts = content_obj.get("parts", [])

                        if not parts:
                            continue

                        # Join all parts (usually just one)
                        content_text = "\n".join(str(part) for part in parts if part)

                        if not content_text:
                            continue

                        # Store chat turn
                        result = await store_chat_turn(
                            user_id=user_id,
                            role=role,
                            content=content_text,
                            conversation_id=conversation_id,
                            conversation_title=conversation_title,
                            source="chatgpt",
                            salience_score=default_salience,
                            metadata={
                                "imported": True,
                                "original_message_id": msg.get("id"),
                                "original_create_time": msg.get("create_time")
                            }
                        )

                        if result.get("success"):
                            stats["messages_imported"] += 1
                        else:
                            stats["errors"].append(
                                f"Failed to import message {msg.get('id')}: {result.get('error')}"
                            )

                    except Exception as e:
                        logger.error(f"Error importing message: {e}")
                        stats["errors"].append(f"Message error: {str(e)}")

                stats["conversations_imported"] += 1
                logger.debug(f"Imported ChatGPT conversation: {conversation_id}")

            except Exception as e:
                logger.error(f"Error importing conversation: {e}")
                stats["errors"].append(f"Conversation error: {str(e)}")

        logger.info(
            f"ChatGPT import complete: {stats['conversations_imported']} conversations, "
            f"{stats['messages_imported']} messages"
        )

        return ImportResponse(
            success=True,
            conversations_imported=stats["conversations_imported"],
            messages_imported=stats["messages_imported"],
            errors=stats["errors"],
            timestamp=datetime.utcnow().isoformat()
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error importing ChatGPT export: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")


# ============================================================================
# Get Import Status
# ============================================================================

@router.get("/status/{user_id}")
async def get_import_status(user_id: str):
    """
    Get import statistics for a user.

    Args:
        user_id: User ID

    Returns:
        Import statistics by source
    """
    try:
        from utils.db import get_db_pool

        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Get counts by source
            stats = await conn.fetch(
                """
                SELECT
                    source,
                    COUNT(*) as count,
                    COUNT(DISTINCT conversation_id) as conversations
                FROM memories
                WHERE user_id = $1
                  AND metadata->>'imported' = 'true'
                GROUP BY source
                ORDER BY count DESC
                """,
                user_id
            )

            return {
                "user_id": user_id,
                "imports": [
                    {
                        "source": row["source"],
                        "messages": row["count"],
                        "conversations": row["conversations"]
                    }
                    for row in stats
                ]
            }

    except Exception as e:
        logger.error(f"Error getting import status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get import status: {str(e)}")
