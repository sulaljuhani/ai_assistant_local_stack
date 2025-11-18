# AI Stack - Qdrant Initialization Scripts

Scripts for setting up Qdrant vector database collections with correct dimensions for nomic-embed-text (768 dims).

## 📋 Overview

These scripts create and configure two Qdrant collections:

1. **knowledge_base** - Documents, notes, tasks, reminders, events
2. **memories** - OpenMemory multi-sector storage

Both collections use:
- **Vector dimensions:** 768 (nomic-embed-text)
- **Distance metric:** Cosine similarity
- **Payload indexes:** Optimized for filtering

## 🚀 Quick Start

### Method 1: Bash Script (Recommended)

```bash
cd /mnt/user/appdata/ai_stack/scripts/qdrant

# Set Qdrant connection (optional, defaults to localhost:6333)
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# Run initialization
./init-collections.sh
```

### Method 2: Python Script

```bash
# Install qdrant-client if not already installed
pip install qdrant-client

# Run initialization
python3 init-collections.py
```

### Method 3: Docker Exec (unRAID)

```bash
# From unRAID host
docker exec qdrant-ai-stack sh -c "
  curl -X PUT 'http://localhost:6333/collections/knowledge_base' \
    -H 'Content-Type: application/json' \
    -d '{\"vectors\": {\"size\": 768, \"distance\": \"Cosine\"}}'
"

docker exec qdrant-ai-stack sh -c "
  curl -X PUT 'http://localhost:6333/collections/memories' \
    -H 'Content-Type: application/json' \
    -d '{\"vectors\": {\"size\": 768, \"distance\": \"Cosine\"}}'
"
```

## 📊 Collection Schemas

### knowledge_base Collection

**Purpose:** Store embeddings for documents, notes, tasks, reminders, and events.

**Configuration:**
```json
{
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "optimizers_config": {
    "indexing_threshold": 10000
  }
}
```

**Indexed Fields:**
- `user_id` (keyword) - Filter by user
- `content_type` (keyword) - note, document_chunk, task, reminder, event
- `created_at` (datetime) - Temporal filtering
- `file_hash` (keyword) - Deduplication

**Example Point:**
```json
{
  "id": "note_uuid_123",
  "vector": [0.123, -0.456, ..., 0.789],  // 768 dimensions
  "payload": {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "content_type": "note",
    "title": "Docker Commands Reference",
    "text": "Docker volume commands...",
    "file_path": "references/docker.md",
    "file_hash": "sha256_abc123...",
    "created_at": "2025-11-18T10:30:00Z"
  }
}
```

### memories Collection

**Purpose:** Store OpenMemory embeddings with multi-sector classification.

**Configuration:**
```json
{
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "optimizers_config": {
    "indexing_threshold": 10000,
    "default_segment_number": 2
  },
  "hnsw_config": {
    "m": 16,
    "ef_construct": 100
  }
}
```

**Indexed Fields:**
- `user_id` (keyword) - Filter by user
- `memory_id` (keyword) - Link to PostgreSQL memory record
- `sector` (keyword) - semantic, episodic, procedural, emotional, reflective
- `source` (keyword) - anythingllm, chatgpt, claude, gemini
- `salience_score` (float) - Importance filtering
- `created_at` (datetime) - Temporal filtering
- `conversation_id` (keyword) - Group by conversation

**Example Point:**
```json
{
  "id": "memory_uuid_456_semantic",  // Format: {memory_id}_{sector}
  "vector": [0.234, -0.567, ..., 0.890],  // 768 dimensions
  "payload": {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "memory_id": "memory_uuid_456",
    "sector": "semantic",
    "content": "Python list comprehensions are faster than for loops",
    "salience_score": 0.85,
    "access_count": 5,
    "source": "chatgpt",
    "conversation_id": "conv_uuid_789",
    "created_at": "2025-11-18T14:20:00Z",
    "tags": ["python", "performance", "programming"]
  }
}
```

## ✅ Verification

### Run Verification Script

```bash
./verify-collections.sh
```

**Checks:**
- ✓ Qdrant connection
- ✓ Collections exist
- ✓ Vector dimensions = 768
- ✓ Distance metric = Cosine
- ✓ Indexed fields created
- ✓ Ollama nomic-embed-text model available
- ✓ Test embedding generation

### Manual Verification

```bash
# List all collections
curl http://localhost:6333/collections

# Get knowledge_base details
curl http://localhost:6333/collections/knowledge_base

# Get memories details
curl http://localhost:6333/collections/memories

# Count points in each collection
curl http://localhost:6333/collections/knowledge_base | jq '.result.points_count'
curl http://localhost:6333/collections/memories | jq '.result.points_count'
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | localhost | Qdrant server hostname |
| `QDRANT_PORT` | 6333 | Qdrant HTTP API port |
| `OLLAMA_HOST` | localhost | Ollama server hostname (for verification) |
| `OLLAMA_PORT` | 11434 | Ollama API port (for verification) |

### For unRAID Users

When using unRAID, use container hostnames:

```bash
export QDRANT_HOST=qdrant-ai-stack
export OLLAMA_HOST=ollama-ai-stack
```

## 📝 What Gets Created

### knowledge_base Collection

| Setting | Value |
|---------|-------|
| Vector size | 768 |
| Distance | Cosine |
| Indexing threshold | 10,000 points |
| Indexed fields | 4 (user_id, content_type, created_at, file_hash) |

### memories Collection

| Setting | Value |
|---------|-------|
| Vector size | 768 |
| Distance | Cosine |
| Indexing threshold | 10,000 points |
| HNSW m | 16 |
| HNSW ef_construct | 100 |
| Default segments | 2 |
| Indexed fields | 7 (user_id, memory_id, sector, source, salience_score, created_at, conversation_id) |

## 🐛 Troubleshooting

### "Cannot connect to Qdrant"

**Check:**
1. Qdrant container is running: `docker ps | grep qdrant`
2. Port is accessible: `curl http://localhost:6333/collections`
3. Network connectivity: `docker network inspect ai-stack-network`

**Fix:**
```bash
# Start Qdrant container
docker start qdrant-ai-stack

# Or via unRAID template
```

### "Collection already exists"

This is **not an error**. The scripts detect existing collections and skip creation.

To **recreate** collections (WARNING: deletes all data):
```bash
# Delete collections
curl -X DELETE http://localhost:6333/collections/knowledge_base
curl -X DELETE http://localhost:6333/collections/memories

# Re-run initialization
./init-collections.sh
```

### "Wrong vector dimensions"

If you see dimensions other than 768, you may have created collections before setting up nomic-embed-text.

**Fix:**
```bash
# Delete and recreate
curl -X DELETE http://localhost:6333/collections/knowledge_base
curl -X DELETE http://localhost:6333/collections/memories

# Ensure nomic-embed-text is pulled
docker exec ollama-ai-stack ollama pull nomic-embed-text

# Verify dimensions
docker exec ollama-ai-stack sh -c "
  curl -s -X POST http://localhost:11434/api/embeddings \
    -d '{\"model\":\"nomic-embed-text\",\"prompt\":\"test\"}' \
    | jq '.embedding | length'
"
# Should output: 768

# Re-run initialization
./init-collections.sh
```

### "Payload indexes not created"

Indexes are created automatically. To verify:

```bash
curl http://localhost:6333/collections/memories | jq '.result.payload_schema'
```

If missing, re-run the script. Existing indexes will be skipped.

### "Python script fails with import error"

**Install qdrant-client:**
```bash
pip install qdrant-client

# Or use the bash script instead
./init-collections.sh
```

## 🔍 Testing Embeddings

### Test Embedding Generation

```bash
# Generate test embedding
curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "This is a test"
  }' | jq '.embedding | length'
```

**Expected output:** `768`

### Test Vector Search

```bash
# Insert a test point
curl -X PUT "http://localhost:6333/collections/memories/points" \
  -H "Content-Type: application/json" \
  -d '{
    "points": [{
      "id": "test_001",
      "vector": [0.1, 0.2, ...],  // 768 dimensions
      "payload": {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "memory_id": "test",
        "sector": "semantic",
        "content": "Test memory"
      }
    }]
  }'

# Search for similar points
curl -X POST "http://localhost:6333/collections/memories/points/search" \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ...],  // 768 dimensions
    "limit": 5
  }'
```

## 📚 Advanced Configuration

### Optimize for Large Datasets (100k+ points)

Edit the initialization script to use higher thresholds:

```json
{
  "optimizers_config": {
    "indexing_threshold": 50000,
    "memmap_threshold": 100000
  },
  "hnsw_config": {
    "m": 32,
    "ef_construct": 200
  }
}
```

### Add Custom Payload Indexes

```bash
# Add custom index
curl -X PUT "http://localhost:6333/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "custom_field",
    "field_schema": "keyword"
  }'
```

### Enable Quantization (for large collections)

```bash
# Enable scalar quantization
curl -X PUT "http://localhost:6333/collections/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "quantization_config": {
      "scalar": {
        "type": "int8",
        "quantile": 0.99,
        "always_ram": true
      }
    }
  }'
```

## 🎯 Next Steps

After running initialization:

1. ✅ **Verify setup**: Run `./verify-collections.sh`
2. ✅ **Pull Ollama model**: `docker exec ollama-ai-stack ollama pull nomic-embed-text`
3. ✅ **Start importing data**:
   - Use n8n workflows to process vault files
   - Import ChatGPT/Claude conversations
   - Let AnythingLLM create embeddings automatically
4. ✅ **Monitor collection growth**:
   ```bash
   watch -n 5 'curl -s http://localhost:6333/collections | jq ".result.collections[] | {name, points_count}"'
   ```

## 📊 Performance Tips

- **Batch inserts**: Insert multiple points at once (100-1000 per request)
- **Use filters**: Always filter by `user_id` to reduce search space
- **Index frequently queried fields**: Add indexes for fields used in filters
- **Monitor memory**: Qdrant loads vectors into RAM for fast search
- **Use snapshots**: Regular backups via `POST /collections/{name}/snapshots`

## 📖 Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Vector Search Best Practices](https://qdrant.tech/documentation/tutorials/search-beginners/)
- [Payload Indexing](https://qdrant.tech/documentation/concepts/indexing/)
- [HNSW Parameters](https://qdrant.tech/documentation/concepts/indexing/#vector-index)
- [nomic-embed-text Model](https://ollama.com/library/nomic-embed-text)

---

**Qdrant collections ready for 768-dimensional embeddings with nomic-embed-text** 🔍
