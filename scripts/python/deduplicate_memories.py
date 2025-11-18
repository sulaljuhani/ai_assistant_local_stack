#!/usr/bin/env python3
"""
AI Stack - Memory Deduplication System
Finds and removes duplicate memories based on content similarity
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Set, Tuple
from uuid import UUID

try:
    import asyncpg
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install asyncpg qdrant-client")
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

DEFAULT_USER_ID = UUID(os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001"))

# Similarity threshold (0.95 = 95% similar)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))

# Statistics
stats = {
    "memories_scanned": 0,
    "duplicates_found": 0,
    "duplicates_archived": 0,
    "errors": 0,
}


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


async def get_memory_vectors(
    qdrant: QdrantClient,
    user_id: UUID
) -> Dict[str, Tuple[List[float], str]]:
    """
    Get all memory vectors from Qdrant.
    Returns dict mapping point_id to (vector, memory_id)
    """
    vectors = {}

    try:
        # Scroll through all points in memories collection
        offset = None
        while True:
            result = qdrant.scroll(
                collection_name="memories",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=str(user_id))
                        )
                    ]
                ),
                limit=100,
                with_vectors=True,
                offset=offset
            )

            points, offset = result

            if not points:
                break

            for point in points:
                memory_id = point.payload.get("memory_id")
                if memory_id:
                    vectors[point.id] = (point.vector, memory_id)

            if offset is None:
                break

        return vectors

    except Exception as e:
        print(f"Error getting vectors from Qdrant: {e}")
        return {}


async def find_duplicates(
    vectors: Dict[str, Tuple[List[float], str]],
    threshold: float = 0.95
) -> List[Tuple[str, str, float]]:
    """
    Find duplicate memories based on vector similarity.
    Returns list of (point_id1, point_id2, similarity_score) tuples.
    """
    duplicates = []
    point_ids = list(vectors.keys())

    print(f"\n🔍 Comparing {len(point_ids)} vectors...")
    print(f"   Similarity threshold: {threshold * 100:.0f}%")

    # Compare all pairs of vectors
    for i in range(len(point_ids)):
        for j in range(i + 1, len(point_ids)):
            point_id1 = point_ids[i]
            point_id2 = point_ids[j]

            vec1, mem_id1 = vectors[point_id1]
            vec2, mem_id2 = vectors[point_id2]

            # Skip if same memory (different sectors)
            if mem_id1 == mem_id2:
                continue

            similarity = calculate_cosine_similarity(vec1, vec2)

            if similarity >= threshold:
                duplicates.append((point_id1, point_id2, similarity))
                stats["duplicates_found"] += 1

        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"   Progress: {i + 1}/{len(point_ids)} vectors processed...")

    return duplicates


async def archive_duplicate_memory(
    conn: asyncpg.Connection,
    memory_id: str,
    reason: str
) -> bool:
    """Archive a duplicate memory."""
    try:
        await conn.execute("""
            UPDATE memories
            SET is_archived = TRUE,
                metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                    'archived_reason', $2,
                    'archived_at', $3
                ),
                updated_at = NOW()
            WHERE id = $1 AND is_archived = FALSE
        """, memory_id, reason, datetime.now().isoformat())

        return True

    except Exception as e:
        print(f"  ✗ Error archiving memory {memory_id}: {e}")
        stats["errors"] += 1
        return False


async def process_duplicates(
    conn: asyncpg.Connection,
    vectors: Dict[str, Tuple[List[float], str]],
    duplicates: List[Tuple[str, str, float]],
    auto_archive: bool = False
) -> None:
    """Process found duplicates."""
    if not duplicates:
        print("\n✅ No duplicates found!")
        return

    print(f"\n📊 Found {len(duplicates)} duplicate pairs")
    print()

    # Group duplicates by memory
    memory_groups: Dict[str, List[Tuple[str, float]]] = {}

    for point_id1, point_id2, similarity in duplicates:
        _, mem_id1 = vectors[point_id1]
        _, mem_id2 = vectors[point_id2]

        if mem_id1 not in memory_groups:
            memory_groups[mem_id1] = []
        if mem_id2 not in memory_groups:
            memory_groups[mem_id2] = []

        memory_groups[mem_id1].append((mem_id2, similarity))
        memory_groups[mem_id2].append((mem_id1, similarity))

    # Process each duplicate
    archived: Set[str] = set()

    for point_id1, point_id2, similarity in duplicates:
        _, mem_id1 = vectors[point_id1]
        _, mem_id2 = vectors[point_id2]

        # Skip if already archived
        if mem_id1 in archived or mem_id2 in archived:
            continue

        # Get memory details
        mem1 = await conn.fetchrow("""
            SELECT id, content, created_at, access_count, salience_score
            FROM memories
            WHERE id = $1 AND is_archived = FALSE
        """, mem_id1)

        mem2 = await conn.fetchrow("""
            SELECT id, content, created_at, access_count, salience_score
            FROM memories
            WHERE id = $1 AND is_archived = FALSE
        """, mem_id2)

        if not mem1 or not mem2:
            continue

        print(f"Duplicate pair (similarity: {similarity * 100:.1f}%):")
        print(f"  1. [{mem1['id'][:8]}...] {mem1['content'][:80]}...")
        print(f"     Created: {mem1['created_at']}, Access count: {mem1['access_count']}, Salience: {mem1['salience_score']}")
        print(f"  2. [{mem2['id'][:8]}...] {mem2['content'][:80]}...")
        print(f"     Created: {mem2['created_at']}, Access count: {mem2['access_count']}, Salience: {mem2['salience_score']}")

        # Determine which to keep
        # Keep the one with higher access count, or higher salience, or older
        if mem1['access_count'] > mem2['access_count']:
            keep, archive = mem1, mem2
        elif mem1['access_count'] < mem2['access_count']:
            keep, archive = mem2, mem1
        elif mem1['salience_score'] > mem2['salience_score']:
            keep, archive = mem1, mem2
        elif mem1['salience_score'] < mem2['salience_score']:
            keep, archive = mem2, mem1
        elif mem1['created_at'] < mem2['created_at']:
            keep, archive = mem1, mem2
        else:
            keep, archive = mem2, mem1

        print(f"  → Keep: {keep['id'][:8]}..., Archive: {archive['id'][:8]}...")

        if auto_archive:
            reason = f"Duplicate of {keep['id']} (similarity: {similarity:.2f})"
            success = await archive_duplicate_memory(conn, archive['id'], reason)
            if success:
                archived.add(archive['id'])
                stats["duplicates_archived"] += 1
                print(f"  ✓ Archived {archive['id'][:8]}...")
        else:
            print(f"  ⚠ Run with --auto-archive to automatically archive duplicates")

        print()

    print(f"\n✅ Processed {len(duplicates)} duplicate pairs")
    if auto_archive:
        print(f"   Archived {stats['duplicates_archived']} duplicate memories")


async def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Stack - Memory Deduplication")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                       help=f"Similarity threshold (default: {SIMILARITY_THRESHOLD})")
    parser.add_argument("--auto-archive", action="store_true",
                       help="Automatically archive duplicates (otherwise just report)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run - don't actually archive anything")

    args = parser.parse_args()

    if args.dry_run:
        args.auto_archive = False

    print("═" * 60)
    print("  AI Stack - Memory Deduplication")
    print("═" * 60)
    print()
    print(f"Similarity threshold: {args.threshold * 100:.0f}%")
    print(f"Auto-archive: {'Yes' if args.auto_archive else 'No (report only)'}")
    print()

    # Connect to PostgreSQL
    print("📡 Connecting to database...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)

    # Connect to Qdrant
    print("📡 Connecting to Qdrant...")
    try:
        qdrant = QdrantClient(**QDRANT_CONFIG)
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        await conn.close()
        sys.exit(1)

    # Get all memory vectors
    print("📥 Fetching memory vectors...")
    vectors = await get_memory_vectors(qdrant, DEFAULT_USER_ID)
    stats["memories_scanned"] = len(vectors)
    print(f"   Found {len(vectors)} memory vectors")

    if len(vectors) == 0:
        print("\n⚠ No memories found")
        await conn.close()
        sys.exit(0)

    # Find duplicates
    duplicates = await find_duplicates(vectors, args.threshold)

    # Process duplicates
    await process_duplicates(conn, vectors, duplicates, args.auto_archive)

    # Cleanup
    await conn.close()

    # Print summary
    print()
    print("═" * 60)
    print("  Deduplication Complete!")
    print("═" * 60)
    print(f"\nMemories scanned: {stats['memories_scanned']}")
    print(f"Duplicates found: {stats['duplicates_found']} pairs")
    print(f"Duplicates archived: {stats['duplicates_archived']}")
    print(f"Errors: {stats['errors']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
