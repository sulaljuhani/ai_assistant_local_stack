#!/usr/bin/env python3
"""
AI Stack - ChatGPT Conversation Importer
Imports ChatGPT conversations.json export into OpenMemory
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

try:
    import asyncpg
    import httpx
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install asyncpg httpx qdrant-client")
    sys.exit(1)

# Configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5434")),
    "database": os.getenv("POSTGRES_DB", "aistack"),
    "user": os.getenv("POSTGRES_USER", "aistack_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
}

QDRANT_CONFIG = {
    "host": os.getenv("QDRANT_HOST", "localhost"),
    "port": int(os.getenv("QDRANT_PORT", "6333")),
}

OLLAMA_URL = f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
DEFAULT_USER_ID = UUID(os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001"))

# Statistics
stats = {
    "conversations": 0,
    "messages": 0,
    "memories_created": 0,
    "duplicates_skipped": 0,
    "errors": 0,
}


async def generate_embedding(text: str, http_client: httpx.AsyncClient) -> List[float]:
    """Generate embedding using Ollama."""
    try:
        response = await http_client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"  Warning: Embedding generation failed: {e}")
        return []


def classify_sectors(content: str) -> List[str]:
    """Classify memory into sectors using keyword matching."""
    content_lower = content.lower()
    sectors = []

    # Semantic: Facts, definitions, explanations
    if any(kw in content_lower for kw in ["is", "are", "means", "definition", "concept", "explain"]):
        sectors.append("semantic")

    # Episodic: Events, experiences
    if any(kw in content_lower for kw in ["i did", "we did", "you did", "worked on", "tried", "fixed", "yesterday", "today"]):
        sectors.append("episodic")

    # Procedural: How-tos, steps
    if any(kw in content_lower for kw in ["how to", "step", "first", "then", "next", "install", "configure", "setup"]):
        sectors.append("procedural")

    # Emotional: Preferences, feelings
    if any(kw in content_lower for kw in ["prefer", "like", "hate", "love", "frustrat", "enjoy", "feel"]):
        sectors.append("emotional")

    # Reflective: Insights, patterns
    if any(kw in content_lower for kw in ["realize", "understand", "pattern", "insight", "learn", "notice"]):
        sectors.append("reflective")

    # Default to semantic if nothing matched
    return sectors if sectors else ["semantic"]


async def check_duplicate(file_hash: str, conn: asyncpg.Connection) -> bool:
    """Check if file has already been imported."""
    result = await conn.fetchval(
        "SELECT 1 FROM imported_chats WHERE file_hash = $1",
        file_hash
    )
    return result is not None


async def parse_chatgpt_export(file_path: Path) -> List[Dict]:
    """Parse ChatGPT conversations.json export."""
    print(f"📖 Reading file: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: Expected array of conversations")
        return []

    conversations = []

    for conv in data:
        try:
            messages = []

            # Parse mapping structure
            mapping = conv.get("mapping", {})
            for key, value in mapping.items():
                if not value.get("message"):
                    continue

                msg = value["message"]
                author = msg.get("author", {})
                role = author.get("role", "unknown")

                content_data = msg.get("content", {})
                if content_data.get("content_type") != "text":
                    continue

                parts = content_data.get("parts", [])
                if not parts or not parts[0]:
                    continue

                content = "\n".join(str(p) for p in parts if p)

                create_time = msg.get("create_time")
                timestamp = datetime.fromtimestamp(create_time) if create_time else None

                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                })

            if messages:
                conversations.append({
                    "id": conv.get("id", str(uuid4())),
                    "title": conv.get("title", "Untitled"),
                    "create_time": datetime.fromtimestamp(conv.get("create_time", 0)) if conv.get("create_time") else None,
                    "update_time": datetime.fromtimestamp(conv.get("update_time", 0)) if conv.get("update_time") else None,
                    "messages": messages,
                })

        except Exception as e:
            print(f"  Warning: Failed to parse conversation: {e}")
            stats["errors"] += 1

    print(f"✓ Parsed {len(conversations)} conversations")
    return conversations


async def import_conversation(
    conv: Dict,
    conn: asyncpg.Connection,
    qdrant: QdrantClient,
    http_client: httpx.AsyncClient,
) -> None:
    """Import a single conversation into OpenMemory."""
    try:
        # Create conversation record
        conv_id = await conn.fetchval("""
            INSERT INTO conversations (user_id, title, source, external_id, started_at, ended_at, message_count)
            VALUES ($1, $2, 'chatgpt', $3, $4, $5, $6)
            RETURNING id
        """, DEFAULT_USER_ID, conv["title"], conv["id"], conv.get("create_time"), conv.get("update_time"), len(conv["messages"]))

        stats["conversations"] += 1

        # Process each message
        for msg in conv["messages"]:
            if msg["role"] == "system":
                continue  # Skip system messages

            content = msg["content"]
            if len(content.strip()) < 10:  # Skip very short messages
                continue

            stats["messages"] += 1

            # Create memory record
            memory_id = await conn.fetchval("""
                INSERT INTO memories (user_id, content, memory_type, source, source_reference, conversation_id, event_timestamp)
                VALUES ($1, $2, 'explicit', 'chatgpt', $3, $4, $5)
                RETURNING id
            """, DEFAULT_USER_ID, content, conv["id"], conv_id, msg.get("timestamp"))

            # Classify sectors
            sectors = classify_sectors(content)

            # Generate embedding
            embedding = await generate_embedding(content, http_client)

            if not embedding:
                print(f"  ⚠ Skipping embedding for memory {memory_id}")
                continue

            # Insert sectors and embeddings
            for sector in sectors:
                # Insert sector
                await conn.execute("""
                    INSERT INTO memory_sectors (memory_id, sector, confidence)
                    VALUES ($1, $2, 0.8)
                    ON CONFLICT (memory_id, sector) DO NOTHING
                """, memory_id, sector)

                # Insert into Qdrant
                point_id = f"{memory_id}_{sector}"
                try:
                    qdrant.upsert(
                        collection_name="memories",
                        points=[PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload={
                                "user_id": str(DEFAULT_USER_ID),
                                "memory_id": str(memory_id),
                                "sector": sector,
                                "content": content[:500],  # Limit payload size
                                "salience_score": 0.5,
                                "source": "chatgpt",
                                "conversation_id": str(conv_id),
                                "created_at": datetime.now().isoformat(),
                            }
                        )]
                    )

                    # Update sector with Qdrant point ID
                    await conn.execute("""
                        UPDATE memory_sectors
                        SET qdrant_point_id = $1
                        WHERE memory_id = $2 AND sector = $3
                    """, point_id, memory_id, sector)

                except Exception as e:
                    print(f"  ⚠ Qdrant insert failed for {point_id}: {e}")

            stats["memories_created"] += 1

    except Exception as e:
        print(f"  ✗ Failed to import conversation '{conv.get('title', 'Unknown')}': {e}")
        stats["errors"] += 1


async def main():
    """Main execution."""
    if len(sys.argv) < 2:
        print("Usage: python import_chatgpt.py <conversations.json>")
        print("\nExample:")
        print("  python import_chatgpt.py /path/to/conversations.json")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print("═" * 60)
    print("  AI Stack - ChatGPT Import")
    print("═" * 60)
    print()

    # Calculate file hash
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    # Connect to PostgreSQL
    print("📡 Connecting to database...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)

    # Check for duplicate import
    if await check_duplicate(file_hash, conn):
        print("⚠ This file has already been imported (duplicate detected)")
        print("  Aborting to prevent duplicates")
        await conn.close()
        sys.exit(0)

    # Initialize Qdrant
    print("📡 Connecting to Qdrant...")
    qdrant = QdrantClient(**QDRANT_CONFIG)

    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)

    # Parse export file
    conversations = await parse_chatgpt_export(file_path)

    if not conversations:
        print("✗ No conversations found in export")
        await conn.close()
        await http_client.aclose()
        sys.exit(1)

    # Import conversations
    print(f"\n🚀 Importing {len(conversations)} conversations...")
    print()

    start_time = datetime.now()

    for i, conv in enumerate(conversations, 1):
        print(f"[{i}/{len(conversations)}] {conv['title'][:50]}...", end=" ")
        await import_conversation(conv, conn, qdrant, http_client)
        print("✓")

    # Record import
    await conn.execute("""
        INSERT INTO imported_chats (user_id, source, file_path, file_name, file_hash, conversations_count, messages_count, memories_created)
        VALUES ($1, 'chatgpt', $2, $3, $4, $5, $6, $7)
    """, DEFAULT_USER_ID, str(file_path), file_path.name, file_hash, stats["conversations"], stats["messages"], stats["memories_created"])

    # Cleanup
    await conn.close()
    await http_client.aclose()

    elapsed = (datetime.now() - start_time).total_seconds()

    # Print summary
    print()
    print("═" * 60)
    print("  Import Complete!")
    print("═" * 60)
    print(f"\nConversations: {stats['conversations']}")
    print(f"Messages: {stats['messages']}")
    print(f"Memories created: {stats['memories_created']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print()


if __name__ == "__main__":
    asyncio.run(main())
