# AI Stack - Container Architecture

## 🏗️ Container Dependency Diagram

```
                                ┌──────────────────────────────┐
                                │   USER (Browser/Obsidian)    │
                                └──────────────────────────────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        │                     │                     │
                        ▼                     ▼                     ▼
              ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐
              │  AnythingLLM    │   │      n8n        │   │   Obsidian   │
              │   (Port 3001)   │   │  (Port 5678)    │   │  (External)  │
              │                 │   │                 │   │              │
              │ • Chat UI       │   │ • Workflows     │   │ • Vault edit │
              │ • RAG engine    │   │ • Automation    │   │ • MD files   │
              │ • Custom skills │   │ • Webhooks      │   │              │
              └─────────────────┘   └─────────────────┘   └──────────────┘
                        │                     │                     │
                        └─────────────────────┼─────────────────────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        │                     │                     │
                        ▼                     ▼                     ▼
              ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐
              │   MCP Server    │   │     Ollama      │   │    Redis     │
              │   (Port 8081)   │   │  (Port 11434)   │   │ (Port 6379)  │
              │                 │   │                 │   │              │
              │ • 12 DB tools   │   │ • llama3.2:3b   │   │ • Cache      │
              │ • 5 Memory tools│   │ • nomic-embed   │   │ • Queue      │
              └─────────────────┘   └─────────────────┘   └──────────────┘
                        │                                         │
                        │                                         │
                        ▼                                         │
              ┌─────────────────────────────────────────┐         │
              │          Data Layer (Network)           │◄────────┘
              └─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │    Qdrant    │ │  File System │
│ (Port 5434)  │ │ (Port 6333)  │ │   (Volumes)  │
│              │ │              │ │              │
│ • aistack DB │ │ • knowledge_ │ │ • vault/     │
│ • n8n DB     │ │   base       │ │ • documents/ │
│ • memories   │ │ • memories   │ │ • memory_    │
│ • reminders  │ │   (768 dims) │ │   vault/     │
│ • tasks      │ │              │ │ • chat_      │
│ • events     │ │              │ │   exports/   │
└──────────────┘ └──────────────┘ └──────────────┘
```

## 🔗 Container Communication Matrix

| Container | Connects To | Purpose |
|-----------|-------------|---------|
| **anythingllm** | ollama | LLM inference, embeddings |
| | qdrant | Vector search (RAG) |
| | n8n (webhooks) | Create reminders/tasks |
| | mcp-server (optional) | Advanced queries |
| **n8n** | postgres | Workflow storage |
| | redis | Queue, cache |
| | ollama | Embeddings for imports |
| | qdrant | Store/search vectors |
| | File system | Watch vault, documents |
| **mcp-server** | postgres | Query DB tables |
| | qdrant | Search memories |
| | ollama | Generate embeddings |
| **ollama** | None | Self-contained |
| **postgres** | None | Data storage |
| **qdrant** | None | Vector storage |
| **redis** | None | Cache storage |

## 📦 Container Sizes & Resources

| Container | Image Size | Volume Size | RAM Usage | CPU Usage |
|-----------|-----------|-------------|-----------|-----------|
| **postgres** | ~230 MB | ~500 MB - 5 GB | 50-200 MB | Low |
| **qdrant** | ~100 MB | ~100 MB - 10 GB | 100-500 MB | Low-Med |
| **redis** | ~40 MB | ~10-100 MB | 20-100 MB | Low |
| **ollama** | ~600 MB | **5-20 GB** | **2-8 GB** | **High** |
| **mcp-server** | ~200 MB | ~10 MB | 50-100 MB | Low |
| **n8n** | ~400 MB | ~100 MB - 1 GB | 100-300 MB | Low-Med |
| **anythingllm** | ~500 MB | ~500 MB - 5 GB | 200-500 MB | Med |
| **TOTAL** | ~2 GB | **6-41 GB** | **2.5-9.5 GB** | Varies |

**Note:** Ollama models are the largest consumers:
- llama3.2:3b: ~2 GB
- nomic-embed-text: ~274 MB
- Additional models add 2-5 GB each

## 🔀 Data Flow Examples

### Example 1: User asks "What are my tasks today?"

```
User → AnythingLLM
        ↓
    [Generate query embedding]
        ↓
    Ollama (nomic-embed-text)
        ↓
    [Search similar memories + tasks]
        ↓
    Qdrant (vector search)
        ↓
    [Retrieve full task details]
        ↓
    MCP Server → PostgreSQL
        ↓
    [Construct context]
        ↓
    Ollama (llama3.2:3b) → Generate response
        ↓
    AnythingLLM → User
```

### Example 2: Import ChatGPT conversations

```
User → Drop conversations.json in chat_exports/
        ↓
    n8n (file watcher triggers)
        ↓
    [Parse JSON, extract messages]
        ↓
    [For each message:]
        ├─ Insert to PostgreSQL (memories table)
        ├─ Classify sector (semantic/episodic/etc.)
        ├─ Generate embedding via Ollama
        └─ Store vector in Qdrant (memories collection)
        ↓
    [Create conversation record]
        ↓
    PostgreSQL (conversations table)
        ↓
    [Optional: Export to markdown]
        ↓
    File System (memory_vault/)
```

### Example 3: Vault file change triggers re-embedding

```
User → Edit note in Obsidian
        ↓
    File System (/vault/project-notes.md changed)
        ↓
    n8n (file watcher detects change)
        ↓
    [Calculate file hash]
        ↓
    [Check if different from stored hash]
        ↓
    Qdrant (lookup by file_hash)
        ↓
    [Hash different → Re-embed]
        ↓
    Ollama (nomic-embed-text) → New embedding
        ↓
    Qdrant (update/insert vector)
        ↓
    PostgreSQL (update file_sync table with new hash)
```

### Example 4: Create reminder via chat

```
User → "Remind me tomorrow at 9am to call dentist"
        ↓
    AnythingLLM (custom skill: create-reminder.js)
        ↓
    [Extract: time=9am, date=tomorrow, message=call dentist]
        ↓
    n8n (webhook: /create-reminder)
        ↓
    PostgreSQL (INSERT INTO reminders)
        ↓
    Response → AnythingLLM → User: "✓ Reminder set"

...next day at 9am...

    n8n (cron: fire-reminders, runs every minute)
        ↓
    PostgreSQL (SELECT reminders WHERE time = NOW())
        ↓
    [Found: "call dentist"]
        ↓
    Notification → User
```

## 🌐 Network Configuration

### Bridge Network: `ai-stack-network`

All containers join this network, enabling communication via container names.

**Example DNS resolution:**
```bash
# From n8n container
ping postgres-ai-stack      → Resolves to 172.18.0.2
ping qdrant-ai-stack        → Resolves to 172.18.0.3
ping ollama-ai-stack        → Resolves to 172.18.0.4
```

### Port Mappings

| Service | Container Port | Host Port | Protocol |
|---------|---------------|-----------|----------|
| PostgreSQL | 5432 | 5434 | TCP |
| Qdrant | 6333 | 6333 | HTTP |
| Redis | 6379 | 6379 | TCP |
| Ollama | 11434 | 11434 | HTTP |
| MCP Server | 8081 | 8081 | HTTP |
| n8n | 5678 | 5678 | HTTP |
| AnythingLLM | 3001 | 3001 | HTTP |

## 🔒 Security Considerations

### Internal Network
- All inter-container communication uses internal network
- No external access needed except Web UIs (n8n, AnythingLLM)

### Exposed Ports
- **Publicly accessible:** 5678 (n8n), 3001 (AnythingLLM)
- **Internal only:** 5434, 6333, 6379, 11434, 8081
- **Recommendation:** Use reverse proxy (Traefik, Nginx) for HTTPS

### Secrets Management
- Store passwords in unRAID container configs
- Use same password across related containers
- Change default passwords before production

### Data Privacy
- All data stays on local server
- No external API calls (100% local)
- Ollama models run entirely offline

## 🚀 Startup Sequence

**Recommended order for minimal downtime:**

1. **Start data layer** (no dependencies):
   - postgres-ai-stack
   - qdrant-ai-stack
   - redis-ai-stack

   Wait 10 seconds for health checks

2. **Start AI layer** (depends on data layer):
   - ollama-ai-stack

   Wait for models to load (~30 seconds)

3. **Start application layer** (depends on all above):
   - mcp-server-ai-stack
   - n8n-ai-stack
   - anythingllm-ai-stack

   Wait for service initialization (~30 seconds)

**Total startup time:** ~2 minutes

## 📊 Monitoring Points

### Health Check Endpoints

```bash
# PostgreSQL
docker exec postgres-ai-stack pg_isready

# Qdrant
curl http://localhost:6333/collections

# Redis
docker exec redis-ai-stack redis-cli ping

# Ollama
curl http://localhost:11434/api/tags

# MCP Server
curl http://localhost:8081/health

# n8n
curl http://localhost:5678/healthz

# AnythingLLM
curl http://localhost:3001/api/system/check
```

### Log Locations

```bash
docker logs postgres-ai-stack
docker logs qdrant-ai-stack
docker logs redis-ai-stack
docker logs ollama-ai-stack
docker logs mcp-server-ai-stack
docker logs n8n-ai-stack
docker logs anythingllm-ai-stack
```

---

**Architecture designed for unRAID servers with independent container management** 🏗️
