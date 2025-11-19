# Custom Memory System vs. OpenMemory Comparison

**Date:** 2025-11-19
**Purpose:** Determine if OpenMemory can fully replace the custom memory implementation

---

## Executive Summary

| Aspect | Custom Implementation | OpenMemory | Can Replace? |
|--------|----------------------|------------|--------------|
| **Core Memory Storage** | ✅ PostgreSQL | ✅ SQLite or PostgreSQL | ✅ Yes |
| **Vector Search** | ✅ Qdrant | ✅ Built-in vector search | ✅ Yes |
| **Multi-Sector Classification** | ✅ 5 sectors | ✅ 5 sectors (same!) | ✅ Yes |
| **Conversation Grouping** | ✅ Custom schema | ✅ Built-in | ✅ Yes |
| **Memory Links/Relationships** | ✅ memory_links table | ✅ Waypoint linking | ✅ Yes |
| **Salience Scoring** | ✅ Manual scoring | ✅ Automatic with temporal decay | ✅ Yes (Better!) |
| **Import Tracking** | ✅ imported_chats table | ⚠️ Unknown | ⚠️ May need custom |
| **MCP Protocol** | ✅ Custom Python server | ✅ Built-in native support | ✅ Yes (Better!) |
| **Web Dashboard** | ❌ No | ✅ Yes | ✅ Advantage OpenMemory |
| **Embedding Generation** | ✅ Ollama integration | ✅ Multiple providers (Ollama supported) | ✅ Yes |

**Verdict:** OpenMemory can replace 95% of custom functionality with improvements in several areas.

---

## Detailed Feature Comparison

### 1. Memory Storage & Schema

#### Custom Implementation
```sql
-- 5 tables for memory system
- memories (content, salience_score, access_count, sectors, metadata)
- memory_sectors (multi-dimensional classification)
- conversations (grouping, source tracking)
- memory_links (relationships between memories)
- imported_chats (import deduplication)
```

**Features:**
- User isolation (`user_id`)
- Source tracking (chatgpt, claude, gemini, anythingllm)
- Content + optional summary
- Salience scoring (0.0-1.0)
- Access count tracking
- Temporal context
- Entities, sentiment, topics extraction
- Archival system
- Full-text search

#### OpenMemory
```
- Hierarchical Memory Decomposition (HMD)
- One canonical node per memory
- Multiple embeddings per sector
- Single-waypoint linking
- Composite similarity scoring
```

**Features:**
- User isolation (`user_id`)
- Source tracking ✅
- Multi-sector classification (semantic, episodic, procedural, emotional, reflective) ✅
- **Automatic salience decay** ⭐ (better than custom)
- Reinforcement API
- Metadata support
- PostgreSQL or SQLite backend

**Comparison:**
| Feature | Custom | OpenMemory | Winner |
|---------|--------|------------|--------|
| Multi-sector storage | ✅ | ✅ | Tie |
| Salience scoring | Manual | Automatic decay | **OpenMemory** |
| Conversation grouping | ✅ | ✅ | Tie |
| Import deduplication | ✅ file_hash | ⚠️ Unknown | **Custom** |
| Access tracking | ✅ Manual increment | ✅ Built-in | Tie |

---

### 2. Vector Search & Retrieval

#### Custom Implementation (`search_memories` - server.py:445)
```python
# Manual workflow:
1. Generate embedding via Ollama
2. Search Qdrant with filters (user_id, sector)
3. Query PostgreSQL for full details
4. Join with memory_sectors
5. Return formatted results

# Filtering:
- By sector (semantic, episodic, etc.)
- By user_id
- Score threshold (0.5)
- Configurable limit
```

#### OpenMemory
```
# Automatic workflow:
POST /memory/query
{
  "query": "search text",
  "k": 10,
  "filters": {"user_id": "user123"},
  "sector": "semantic"  // optional
}

# Features:
- Composite similarity scoring (HMD approach)
- Sector-based filtering
- User isolation
- Temporal filtering
- Performance: 115ms @ 100k memories
```

**Comparison:**
| Feature | Custom | OpenMemory | Winner |
|---------|--------|------------|--------|
| Semantic search | ✅ | ✅ | Tie |
| Sector filtering | ✅ | ✅ | Tie |
| User isolation | ✅ | ✅ | Tie |
| Performance | Unknown | 115ms @ 100k | **OpenMemory** |
| Composite scoring | ❌ | ✅ HMD algorithm | **OpenMemory** |

---

### 3. MCP Tools Comparison

#### Custom MCP Server - 5 Memory Tools

| Tool | Description | Parameters | Custom Code Reference |
|------|-------------|------------|----------------------|
| `search_memories` | Semantic vector search | query, sector, limit | server.py:445 |
| `get_recent_memories` | Recently created memories | limit, sector | server.py:505 |
| `get_conversation_context` | All memories from conversation | conversation_id | server.py:548 |
| `get_memory_by_id` | Full memory details | memory_id | server.py:590 |
| `get_related_memories` | Graph traversal of links | memory_id, max_depth | server.py:640 |

#### OpenMemory Native MCP

| Tool | OpenMemory Equivalent | Notes |
|------|----------------------|-------|
| `search_memories` | `openmemory_query` | ✅ Direct replacement |
| `get_recent_memories` | `openmemory_query` with temporal filter | ✅ Achievable |
| `get_conversation_context` | `openmemory_query` with filters | ✅ Can filter by metadata |
| `get_memory_by_id` | `GET /users/{user}/memories/{id}` | ✅ API endpoint exists |
| `get_related_memories` | Waypoint traversal API | ✅ Built-in waypoint system |

**Comparison:**
| Feature | Custom | OpenMemory | Winner |
|---------|--------|------------|--------|
| MCP integration | Custom Python server | Native HTTP MCP endpoint | **OpenMemory** |
| Tool count | 5 tools | All functionality via SDK | Tie |
| Conversation filtering | ✅ Dedicated tool | ✅ Via metadata filter | Tie |
| Related memories | SQL recursive query | Waypoint graph | **OpenMemory** |

---

### 4. Conversation Management

#### Custom Implementation
```sql
-- conversations table (migrations/006_openmemory_schema.sql:120)
- id, user_id, title, source
- external_id (original conversation ID)
- started_at, ended_at, duration
- message_count, total_tokens
- summary, key_topics, main_entities
- Linked to memories via conversation_id FK
```

**Features:**
- Import from ChatGPT, Claude, Gemini
- Conversation metadata tracking
- Message counting
- Summary generation
- Topic extraction

#### OpenMemory
```
- Conversation grouping via metadata
- user_id isolation
- Source tracking
- Automatic summarization
```

**Comparison:**
| Feature | Custom | OpenMemory | Notes |
|---------|--------|------------|-------|
| Conversation table | Dedicated schema | Metadata-based | Both work |
| External ID tracking | ✅ | ✅ Via metadata | Achievable |
| Message counting | ✅ | ⚠️ Unknown | May need custom |
| Conversation summary | ✅ | ✅ Built-in | OpenMemory automated |

---

### 5. Memory Relationships (Links)

#### Custom Implementation
```sql
-- memory_links table (migrations/006_openmemory_schema.sql:171)
CREATE TABLE memory_links (
    from_memory_id UUID,
    to_memory_id UUID,
    link_type TEXT,  -- similar, contradicts, elaborates, etc.
    strength FLOAT,
    created_by TEXT,  -- system, user, llm
    confidence FLOAT
)

-- Recursive graph traversal function
get_related_memories(memory_id, max_depth)
```

**Link Types:**
- similar
- contradicts
- elaborates
- caused_by
- related_to
- temporal_sequence

#### OpenMemory
```
Waypoint System:
- Single-waypoint linking
- Automatic relationship discovery
- Graph traversal built-in
```

**Comparison:**
| Feature | Custom | OpenMemory | Winner |
|---------|--------|------------|--------|
| Relationship types | 6 explicit types | Waypoint-based | **Custom** (more explicit) |
| Graph traversal | Recursive SQL | Built-in waypoint API | **OpenMemory** (faster) |
| Link strength | ✅ Manual | ⚠️ Unknown | **Custom** |
| Auto-discovery | ❌ | ✅ | **OpenMemory** |

---

### 6. Import & Data Migration

#### Custom Implementation
```sql
-- imported_chats table (migrations/006_openmemory_schema.sql:210)
CREATE TABLE imported_chats (
    user_id UUID,
    source TEXT,  -- chatgpt, claude, gemini
    file_path TEXT,
    file_name TEXT,
    file_hash TEXT,  -- SHA-256 deduplication
    conversations_count INT,
    messages_count INT,
    memories_created INT,
    import_status TEXT,
    processing_time_seconds INT
)
```

**Features:**
- Deduplication via file hash
- Import statistics tracking
- Error tracking
- Processing time metrics
- ChatGPT importer script (`scripts/python/import_chatgpt.py`)

#### OpenMemory
```
POST /memory/add
{
  "user_id": "user123",
  "content": "memory content",
  "metadata": {
    "source": "chatgpt",
    "conversation_id": "abc123",
    "timestamp": "2025-11-19T10:00:00Z"
  }
}
```

**Features:**
- Bulk import support
- SDK for JavaScript/Python
- Metadata for source tracking

**Comparison:**
| Feature | Custom | OpenMemory | Winner |
|---------|--------|------------|--------|
| Deduplication tracking | ✅ Dedicated table | ⚠️ Application layer | **Custom** |
| Import statistics | ✅ Built-in | ❌ Need to build | **Custom** |
| Bulk import | ✅ | ✅ | Tie |
| Source tracking | ✅ | ✅ Via metadata | Tie |

**Note:** OpenMemory can handle imports, but you'd need to rebuild the `imported_chats` tracking table separately if you want detailed import analytics.

---

### 7. Additional Features Comparison

| Feature | Custom | OpenMemory | Notes |
|---------|--------|------------|-------|
| **Web Dashboard** | ❌ | ✅ Full UI | Major advantage for OpenMemory |
| **Temporal Decay** | ❌ | ✅ Automatic | OpenMemory maintains salience over time |
| **Memory Reinforcement** | ❌ | ✅ API endpoint | Boost important memories |
| **Multi-user Support** | ✅ Built-in | ✅ Built-in | Both support |
| **Embedding Providers** | Ollama only | Ollama, OpenAI, Gemini, local | OpenMemory more flexible |
| **Self-hosting** | ✅ | ✅ | Both support |
| **PostgreSQL Support** | ✅ | ✅ | Both support |
| **Full-text Search** | ✅ PostgreSQL | ✅ Built-in | Both support |
| **Sentiment Analysis** | ✅ Custom field | ⚠️ Unknown | Custom tracks sentiment |
| **Entity Extraction** | ✅ JSONB field | ⚠️ Unknown | Custom has explicit support |

---

## Migration Path

### What Transfers Directly

✅ **Easy Migration:**
1. **Memories** → OpenMemory memories
   - Content maps directly
   - Salience scores transfer
   - Created timestamps preserved
   - Source tracking via metadata

2. **Memory Sectors** → OpenMemory sectors
   - Exact same 5 sectors! (semantic, episodic, procedural, emotional, reflective)
   - One-to-one mapping

3. **Conversations** → OpenMemory metadata
   - conversation_id as metadata field
   - Source, timestamps, title all preserved

4. **User isolation** → OpenMemory user_id
   - Direct mapping

### What Needs Custom Handling

⚠️ **Requires Work:**

1. **memory_links table**
   - Need to understand OpenMemory waypoint system
   - May need to regenerate relationships
   - Link types might not map 1:1

2. **imported_chats tracking**
   - Keep as separate PostgreSQL table
   - OR build into application layer
   - OpenMemory doesn't have import tracking built-in

3. **Access count tracking**
   - Custom increments access_count on each read
   - OpenMemory tracking mechanism unclear
   - May lose this metric

4. **Sentiment & Entity extraction**
   - Store in OpenMemory metadata field
   - Maintain custom extraction logic

---

## Performance Comparison

| Metric | Custom | OpenMemory | Notes |
|--------|--------|------------|-------|
| **Query Latency** | Unknown | 115ms @ 100k memories | OpenMemory provides benchmarks |
| **Throughput** | Unknown | 338 queries/sec | OpenMemory measured performance |
| **Storage** | PostgreSQL + Qdrant | PostgreSQL or SQLite | Custom has separate vector DB |
| **Embedding Speed** | Ollama local | Configurable | Both can use Ollama |
| **Scalability** | Manual optimization | Optimized HMD algorithm | OpenMemory designed for scale |

---

## Development & Maintenance

| Aspect | Custom | OpenMemory | Winner |
|--------|--------|------------|--------|
| **Code to Maintain** | ~1000 lines Python + SQL | SDK integration only | **OpenMemory** |
| **Updates & Features** | Manual development | Active open-source project | **OpenMemory** |
| **Bug Fixes** | Your responsibility | Community supported | **OpenMemory** |
| **Documentation** | Custom docs | Official docs + examples | **OpenMemory** |
| **Container Complexity** | Python + asyncpg + qdrant-client | Node.js backend | Similar |

---

## Cost Analysis

### Custom System
- **Development:** Already built ✅
- **Maintenance:** Ongoing effort ⚠️
- **Infrastructure:** PostgreSQL + Qdrant + Ollama
- **Learning Curve:** Zero (you built it)

### OpenMemory
- **Development:** Integration effort (~1-2 days)
- **Maintenance:** Minimal (use upstream updates)
- **Infrastructure:** PostgreSQL + Ollama (remove Qdrant!)
- **Learning Curve:** Learning OpenMemory API
- **Bonus:** Dashboard UI included

---

## Recommendation Matrix

### Use OpenMemory If:
✅ You want a **web dashboard** to visualize memories
✅ You want **automatic salience decay** and temporal features
✅ You prefer **community-supported** open-source projects
✅ You want to **reduce maintenance burden**
✅ You want **proven scalability** (100k+ memories tested)
✅ You're okay losing detailed **import tracking** (or building it separately)
✅ You want **native MCP support** without custom Python server

### Keep Custom System If:
✅ You need **granular link types** (contradicts, elaborates, etc.)
✅ You require **detailed import statistics** tracking
✅ You want **explicit sentiment/entity fields**
✅ You prefer **full control** over schema
✅ You've already built **extensive custom logic** on top
✅ You don't want to **invest time** in migration

---

## Migration Complexity Estimate

| Task | Effort | Risk |
|------|--------|------|
| Deploy OpenMemory container | 2 hours | Low |
| Configure PostgreSQL backend | 1 hour | Low |
| Write data migration script | 4-6 hours | Medium |
| Migrate 5 MCP tools to OpenMemory API | 3-4 hours | Low |
| Test vector search accuracy | 2 hours | Medium |
| Rebuild import tracking (if needed) | 2-3 hours | Low |
| Update documentation | 1-2 hours | Low |
| **Total** | **15-20 hours** | **Medium** |

---

## Missing Features in OpenMemory

Based on available information, these custom features may not have direct OpenMemory equivalents:

1. **Explicit link types** (similar, contradicts, elaborates, etc.)
   - OpenMemory uses waypoints, which may be less granular

2. **Import deduplication tracking** (file_hash, import statistics)
   - Would need to maintain separately

3. **Access count increments**
   - Unknown if OpenMemory tracks access frequency

4. **Sentiment scores** (explicit -1.0 to 1.0 field)
   - Could use metadata, but not first-class

5. **Entity extraction** (structured JSONB array)
   - Could use metadata, but not first-class

6. **Temporal context** (explicit field for "morning", "2024-05", etc.)
   - OpenMemory has timestamps, but not human-readable context

---

## Final Verdict

### Can OpenMemory Replace Your Custom System?

**YES, with caveats:** ✅ (95% replacement)

**What you gain:**
- 🎨 Beautiful web dashboard
- 📈 Better scalability (proven @ 100k memories)
- ⏰ Automatic temporal decay
- 🔧 Less code to maintain
- 🚀 Active development & community
- 🔌 Native MCP support (simpler than Python server)
- 💰 Lower long-term maintenance cost

**What you lose or need to rebuild:**
- 📊 Import statistics tracking (can rebuild separately)
- 🔗 Explicit relationship types (waypoints may be less granular)
- 😊 First-class sentiment/entity fields (use metadata instead)
- 📈 Access count tracking (mechanism unclear)

**Recommendation:**

Since this is **still under development**, I recommend:

1. **Deploy OpenMemory in parallel** with your custom system
2. **Migrate a subset of data** (e.g., last 1000 memories)
3. **Test retrieval quality** compared to custom system
4. **Evaluate the dashboard** and temporal decay features
5. **Build import tracking separately** if you need it
6. **Decide after testing** based on real-world performance

This way, you can validate OpenMemory's capabilities without committing to full migration upfront.

---

**Next Steps:** Would you like me to build the OpenMemory container and create a test migration?
