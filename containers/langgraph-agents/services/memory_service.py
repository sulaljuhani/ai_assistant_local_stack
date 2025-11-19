"""
Memory Service

Scheduled jobs for memory enrichment and vault synchronization.

Replaces n8n workflows:
- 11-enrich-memories.json (daily 3 AM)
- 12-sync-memory-to-vault.json (every 6 hours)
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path
import os

from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Enrich Memories (Workflow 11)
# Schedule: Daily at 3 AM
# ============================================================================

async def enrich_memories() -> Dict[str, Any]:
    """
    Enrich frequently accessed memories with additional insights.

    Replaces n8n workflow: 11-enrich-memories.json

    Logic:
    1. Query memories with high access_count (>5) and not enriched recently
    2. For each memory:
       - Analyze context and patterns
       - Extract key insights
       - Add enrichment metadata
       - Increase salience score
    3. Return count of enriched memories

    Returns:
        Dict with enrichment statistics
    """
    try:
        pool = await get_db_pool()
        now = datetime.now()
        enrichment_cutoff = now - timedelta(days=7)  # Don't re-enrich within 7 days

        stats = {
            "memories_processed": 0,
            "memories_enriched": 0,
            "errors": [],
            "timestamp": now.isoformat()
        }

        async with pool.acquire() as conn:
            # Get candidates for enrichment
            candidates = await conn.fetch(
                """
                SELECT id, content, salience_score, access_count, last_accessed_at
                FROM memories
                WHERE access_count >= 5
                  AND (last_enriched_at IS NULL OR last_enriched_at < $1)
                  AND salience_score < 0.9
                ORDER BY access_count DESC
                LIMIT 100
                """,
                enrichment_cutoff
            )

            stats["memories_processed"] = len(candidates)

            if not candidates:
                logger.info("No memories found for enrichment")
                return stats

            logger.info(f"Processing {len(candidates)} memories for enrichment")

            for memory in candidates:
                try:
                    # Calculate enrichment boost based on access patterns
                    access_count = memory["access_count"]
                    current_salience = memory["salience_score"]

                    # Boost salience by 10% for frequently accessed memories
                    salience_boost = min(0.1, (access_count - 5) * 0.01)
                    new_salience = min(0.95, current_salience + salience_boost)

                    # Extract simple insights (could be enhanced with LLM analysis)
                    content_length = len(memory["content"])
                    enrichment_data = {
                        "access_count": access_count,
                        "content_length": content_length,
                        "last_accessed": memory["last_accessed_at"].isoformat() if memory["last_accessed_at"] else None,
                        "enriched_at": now.isoformat()
                    }

                    # Update memory with enrichment
                    await conn.execute(
                        """
                        UPDATE memories
                        SET
                            salience_score = $1,
                            enrichment_data = $2,
                            last_enriched_at = NOW(),
                            updated_at = NOW()
                        WHERE id = $3
                        """,
                        new_salience,
                        enrichment_data,
                        memory["id"]
                    )

                    stats["memories_enriched"] += 1

                    logger.debug(
                        f"Enriched memory {memory['id']}: "
                        f"salience {current_salience:.2f} -> {new_salience:.2f}"
                    )

                except Exception as e:
                    logger.error(f"Error enriching memory {memory['id']}: {e}")
                    stats["errors"].append({
                        "memory_id": memory["id"],
                        "error": str(e)
                    })

            logger.info(
                f"Memory enrichment complete: {stats['memories_enriched']} "
                f"of {stats['memories_processed']} enriched"
            )

            return stats

    except Exception as e:
        logger.error(f"Error during memory enrichment: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Sync Memory to Vault (Workflow 12)
# Schedule: Every 6 hours
# ============================================================================

async def sync_memory_to_vault() -> Dict[str, Any]:
    """
    Export high-salience memories to vault as Markdown files.

    Replaces n8n workflow: 12-sync-memory-to-vault.json

    Logic:
    1. Query memories WHERE salience_score > 0.8
    2. Group by conversation
    3. For each high-salience conversation:
       - Format as Markdown
       - Include metadata (date, participants, topics)
       - Write to vault as memory_export_{conversation_id}.md
    4. Return count of exported conversations

    Returns:
        Dict with export statistics
    """
    try:
        # Get vault path from environment or use default
        vault_path = os.getenv("VAULT_PATH", "/data/vault")
        memory_export_dir = os.path.join(vault_path, "memory_exports")

        # Create export directory if it doesn't exist
        Path(memory_export_dir).mkdir(parents=True, exist_ok=True)

        pool = await get_db_pool()

        stats = {
            "conversations_processed": 0,
            "conversations_exported": 0,
            "memories_exported": 0,
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }

        async with pool.acquire() as conn:
            # Get conversations with high-salience memories
            conversations = await conn.fetch(
                """
                SELECT DISTINCT c.id, c.title, c.source, c.created_at, c.updated_at
                FROM conversations c
                JOIN memories m ON c.id = m.conversation_id
                WHERE m.salience_score > 0.8
                ORDER BY c.updated_at DESC
                """
            )

            stats["conversations_processed"] = len(conversations)

            if not conversations:
                logger.info("No high-salience conversations found for export")
                return stats

            logger.info(f"Exporting {len(conversations)} conversations to vault")

            for conversation in conversations:
                try:
                    conv_id = conversation["id"]

                    # Get all high-salience memories for this conversation
                    memories = await conn.fetch(
                        """
                        SELECT
                            m.id,
                            m.role,
                            m.content,
                            m.salience_score,
                            m.created_at,
                            array_agg(ms.sector) as sectors
                        FROM memories m
                        LEFT JOIN memory_sectors ms ON m.id = ms.memory_id
                        WHERE m.conversation_id = $1
                          AND m.salience_score > 0.8
                        GROUP BY m.id, m.role, m.content, m.salience_score, m.created_at
                        ORDER BY m.created_at ASC
                        """,
                        conv_id
                    )

                    if not memories:
                        continue

                    # Format as Markdown
                    markdown_content = f"""# {conversation['title']}

**Conversation ID:** `{conv_id}`
**Source:** {conversation['source']}
**Created:** {conversation['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {conversation['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}
**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## High-Salience Memories ({len(memories)} messages)

"""

                    for memory in memories:
                        role_emoji = "👤" if memory["role"] == "user" else "🤖"
                        sectors = ", ".join(memory["sectors"]) if memory["sectors"] else "none"

                        markdown_content += f"""### {role_emoji} {memory['role'].title()} - {memory['created_at'].strftime('%Y-%m-%d %H:%M')}

**Salience:** {memory['salience_score']:.2f} | **Sectors:** {sectors}

{memory['content']}

---

"""

                    # Write to vault
                    export_filename = f"memory_export_{conv_id}.md"
                    export_path = os.path.join(memory_export_dir, export_filename)

                    with open(export_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)

                    stats["conversations_exported"] += 1
                    stats["memories_exported"] += len(memories)

                    logger.info(
                        f"Exported conversation {conv_id}: "
                        f"{len(memories)} memories to {export_filename}"
                    )

                except Exception as e:
                    logger.error(f"Error exporting conversation {conv_id}: {e}")
                    stats["errors"].append({
                        "conversation_id": conv_id,
                        "error": str(e)
                    })

            logger.info(
                f"Memory vault sync complete: {stats['conversations_exported']} "
                f"conversations, {stats['memories_exported']} memories exported"
            )

            return stats

    except Exception as e:
        logger.error(f"Error during memory vault sync: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
