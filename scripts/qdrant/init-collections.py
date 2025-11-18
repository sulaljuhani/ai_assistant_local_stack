#!/usr/bin/env python3
"""
AI Stack - Qdrant Collections Initialization (Python)
Creates vector database collections with 768 dimensions (nomic-embed-text)
"""

import os
import sys
from typing import Dict, List, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        OptimizersConfigDiff,
        HnswConfigDiff,
        PayloadSchemaType,
        PayloadIndexInfo,
    )
except ImportError:
    print("Error: qdrant-client not installed")
    print("Install with: pip install qdrant-client")
    sys.exit(1)

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBEDDING_DIMENSIONS = 768  # nomic-embed-text

# Collection configurations
COLLECTIONS = {
    "knowledge_base": {
        "description": "Documents, notes, tasks, reminders, events",
        "vector_size": EMBEDDING_DIMENSIONS,
        "distance": Distance.COSINE,
        "indexes": [
            ("user_id", PayloadSchemaType.KEYWORD),
            ("content_type", PayloadSchemaType.KEYWORD),
            ("created_at", PayloadSchemaType.DATETIME),
            ("file_hash", PayloadSchemaType.KEYWORD),
        ],
    },
    "memories": {
        "description": "OpenMemory multi-sector storage",
        "vector_size": EMBEDDING_DIMENSIONS,
        "distance": Distance.COSINE,
        "hnsw_config": {
            "m": 16,
            "ef_construct": 100,
        },
        "indexes": [
            ("user_id", PayloadSchemaType.KEYWORD),
            ("memory_id", PayloadSchemaType.KEYWORD),
            ("sector", PayloadSchemaType.KEYWORD),
            ("source", PayloadSchemaType.KEYWORD),
            ("salience_score", PayloadSchemaType.FLOAT),
            ("created_at", PayloadSchemaType.DATETIME),
            ("conversation_id", PayloadSchemaType.KEYWORD),
        ],
    },
}


def print_header():
    """Print script header."""
    print("=" * 60)
    print("  AI Stack - Qdrant Collections Setup (Python)")
    print("=" * 60)
    print(f"\nTarget: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"Embedding dimensions: {EMBEDDING_DIMENSIONS}\n")


def check_connection(client: QdrantClient) -> bool:
    """Check if Qdrant is accessible."""
    try:
        collections = client.get_collections()
        print("✓ Connected to Qdrant")
        return True
    except Exception as e:
        print(f"✗ Cannot connect to Qdrant: {e}")
        print("\nPlease ensure:")
        print("  1. Qdrant container is running")
        print(f"  2. Port {QDRANT_PORT} is accessible")
        print("  3. QDRANT_HOST and QDRANT_PORT are correct")
        return False


def create_collection(
    client: QdrantClient,
    name: str,
    config: Dict,
) -> bool:
    """Create a Qdrant collection with configuration."""
    print(f"\nCreating collection: {name}")
    print(f"  Description: {config['description']}")
    print(f"  Vector size: {config['vector_size']}")
    print(f"  Distance: {config['distance'].value}")

    try:
        # Check if collection exists
        existing = client.get_collections()
        if any(c.name == name for c in existing.collections):
            print(f"  ⚠ Collection '{name}' already exists, skipping creation")
            return True

        # Create collection
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=config["vector_size"],
                distance=config["distance"],
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=10000,
            ),
            hnsw_config=HnswConfigDiff(**config.get("hnsw_config", {}))
            if config.get("hnsw_config")
            else None,
        )

        print(f"  ✓ Collection created")
        return True

    except Exception as e:
        print(f"  ✗ Failed to create collection: {e}")
        return False


def create_indexes(
    client: QdrantClient,
    collection_name: str,
    indexes: List[tuple],
) -> bool:
    """Create payload indexes for a collection."""
    print(f"  Creating payload indexes ({len(indexes)} fields)...")

    success_count = 0
    for field_name, field_type in indexes:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type,
            )
            success_count += 1
        except Exception as e:
            # Index might already exist, continue
            if "already exists" not in str(e).lower():
                print(f"    ⚠ Warning: Failed to create index for {field_name}: {e}")

    print(f"  ✓ Created/verified {success_count}/{len(indexes)} indexes")
    return success_count > 0


def verify_collections(client: QdrantClient) -> None:
    """Verify and display collection information."""
    print("\n" + "=" * 60)
    print("  Collection Details")
    print("=" * 60 + "\n")

    try:
        collections = client.get_collections()

        for collection in collections.collections:
            if collection.name in COLLECTIONS:
                info = client.get_collection(collection.name)

                print(f"Collection: {collection.name}")
                print(f"  Vector size: {info.config.params.vectors.size}")
                print(f"  Distance: {info.config.params.vectors.distance.value}")
                print(f"  Points count: {info.points_count}")

                # Get indexed fields
                payload_schema = info.payload_schema or {}
                print(f"  Indexed fields: {len(payload_schema)}")
                if payload_schema:
                    for field, schema in payload_schema.items():
                        print(f"    - {field}: {schema.data_type}")
                print()

    except Exception as e:
        print(f"Error verifying collections: {e}")


def main():
    """Main execution."""
    print_header()

    # Initialize client
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    except Exception as e:
        print(f"✗ Failed to initialize Qdrant client: {e}")
        sys.exit(1)

    # Check connection
    if not check_connection(client):
        sys.exit(1)

    print("\nCreating collections with 768 dimensions (nomic-embed-text)...")

    # Create collections
    success = True
    for name, config in COLLECTIONS.items():
        if not create_collection(client, name, config):
            success = False
            continue

        # Create indexes
        if not create_indexes(client, name, config["indexes"]):
            print(f"  ⚠ Warning: Some indexes failed for {name}")

    # Verify
    verify_collections(client)

    # Final message
    print("=" * 60)
    if success:
        print("  Setup Complete!")
    else:
        print("  Setup Completed with Warnings")
    print("=" * 60 + "\n")

    print("Next steps:")
    print("  1. Pull Ollama model: docker exec ollama-ai-stack ollama pull nomic-embed-text")
    print("  2. Verify embedding dimensions match: 768")
    print("  3. Start importing data or begin using AnythingLLM")
    print()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
