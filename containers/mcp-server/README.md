# AI Stack - MCP Server

Model Context Protocol server providing 17 tools for database and memory access.

## 🎯 Overview

The MCP server acts as a bridge between AI agents (like Claude) and your AI Stack data. It provides structured access to:

- **12 Database Tools**: Reminders, tasks, events, notes
- **5 Memory Tools**: OpenMemory search and retrieval

## 🛠️ Tools Available

### Database Tools (12)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_reminders_today` | Get all reminders for today | None |
| `get_reminders_upcoming` | Get reminders in next N days | `days` (default: 7) |
| `search_reminders` | Search reminders by text | `query` |
| `get_events_today` | Get all events for today | None |
| `get_events_upcoming` | Get events in next N days | `days` (default: 7) |
| `get_tasks_by_status` | Get tasks by status | `status` (todo, in_progress, done, etc.) |
| `get_tasks_due_soon` | Get tasks due in next N days | `days` (default: 7) |
| `search_notes` | Search notes by content | `query` |
| `get_recent_notes` | Get recently modified notes | `limit` (default: 10) |
| `get_reminder_categories` | Get all categories with counts | None |
| `get_day_summary` | Summary of today's activities | None |
| `get_week_summary` | Summary of this week's activities | None |

### Memory Tools (5)

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_memories` | Semantic search across memories | `query`, `sector` (optional), `limit` (default: 10) |
| `get_recent_memories` | Get recently created memories | `limit` (default: 10), `sector` (optional) |
| `get_conversation_context` | Get all memories from a conversation | `conversation_id` (UUID) |
| `get_memory_by_id` | Get full details of a memory | `memory_id` (UUID) |
| `get_related_memories` | Get linked memories | `memory_id` (UUID), `max_depth` (default: 2) |

## 🚀 Building and Running

### Build Docker Image

```bash
cd /mnt/user/appdata/ai_stack/containers/mcp-server
./build.sh
```

This creates the image: `mcp-server-ai-stack:latest`

### Run Container (Manual Testing)

```bash
# Set environment variables (optional)
export POSTGRES_PASSWORD=your_secure_password

# Run container
./run.sh
```

### Deploy via unRAID

Use the `my-mcp-server.xml` template in the unRAID web UI.

**Important:** Build the image first using `build.sh` before installing the template!

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | postgres-ai-stack | PostgreSQL hostname |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | aistack | Database name |
| `POSTGRES_USER` | aistack_user | Database username |
| `POSTGRES_PASSWORD` | *(required)* | Database password |
| `QDRANT_HOST` | qdrant-ai-stack | Qdrant hostname |
| `QDRANT_PORT` | 6333 | Qdrant port |
| `OLLAMA_HOST` | ollama-ai-stack | Ollama hostname |
| `OLLAMA_PORT` | 11434 | Ollama port |
| `DEFAULT_USER_ID` | 00000000-0000-0000-0000-000000000001 | Single-user UUID |

### Dependencies

- **PostgreSQL**: Must be running with migrations applied
- **Qdrant**: Must have `memories` collection created (768 dimensions)
- **Ollama**: Must have `nomic-embed-text` model pulled

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│         AI Agent (Claude, etc.)         │
└─────────────────────────────────────────┘
                    ↓
            MCP Protocol (stdio)
                    ↓
┌─────────────────────────────────────────┐
│           MCP Server (Python)           │
│  ┌───────────────────────────────────┐  │
│  │  Tool Router                      │  │
│  │  ├─ Database Tools (12)           │  │
│  │  └─ Memory Tools (5)              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↓              ↓              ↓
   PostgreSQL       Qdrant         Ollama
   (asyncpg)    (qdrant-client)   (httpx)
```

## 🔍 How Tools Work

### Example: Search Memories

1. **User asks**: "What did I learn about Docker?"
2. **MCP tool called**: `search_memories(query="Docker")`
3. **Server generates embedding** via Ollama (nomic-embed-text)
4. **Qdrant vector search** finds similar memory vectors
5. **PostgreSQL query** retrieves full memory details
6. **Formatted result** returned to user

### Example: Get Day Summary

1. **User asks**: "What's on my schedule today?"
2. **MCP tool called**: `get_day_summary()`
3. **PostgreSQL aggregation** queries:
   - Reminders for today
   - Tasks due today
   - Events today
   - Tasks completed today
4. **Formatted summary** returned

## 🧪 Testing

### Test Database Connection

```bash
docker exec mcp-server-ai-stack python -c "
import asyncio
import asyncpg
import os

async def test():
    conn = await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=int(os.getenv('POSTGRES_PORT')),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )
    version = await conn.fetchval('SELECT version()')
    print(f'Connected to: {version}')
    await conn.close()

asyncio.run(test())
"
```

### Test Qdrant Connection

```bash
docker exec mcp-server-ai-stack python -c "
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    host=os.getenv('QDRANT_HOST'),
    port=int(os.getenv('QDRANT_PORT')),
)
collections = client.get_collections()
print(f'Qdrant collections: {collections}')
"
```

### Test Ollama Embedding

```bash
docker exec mcp-server-ai-stack python -c "
import asyncio
import httpx
import os

async def test():
    client = httpx.AsyncClient()
    base_url = f\"http://{os.getenv('OLLAMA_HOST')}:{os.getenv('OLLAMA_PORT')}\"
    response = await client.post(
        f'{base_url}/api/embeddings',
        json={'model': 'nomic-embed-text', 'prompt': 'test'},
    )
    data = response.json()
    embedding = data.get('embedding', [])
    print(f'Embedding dimensions: {len(embedding)}')
    await client.aclose()

asyncio.run(test())
"
```

Expected output: `Embedding dimensions: 768`

## 🐛 Troubleshooting

### "Cannot connect to PostgreSQL"

**Check:**
1. PostgreSQL container is running: `docker ps | grep postgres`
2. Network connectivity: `docker exec mcp-server-ai-stack ping postgres-ai-stack`
3. Password matches: Check both containers have same `POSTGRES_PASSWORD`
4. Database exists: `docker exec postgres-ai-stack psql -U aistack_user -l`

### "Qdrant collection not found"

**Solution:**
```bash
# Create memories collection
curl -X PUT "http://localhost:6333/collections/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }'
```

### "Ollama model not found"

**Solution:**
```bash
# Pull nomic-embed-text model
docker exec ollama-ai-stack ollama pull nomic-embed-text
```

### Container crashes on startup

**Check logs:**
```bash
docker logs mcp-server-ai-stack
```

**Common issues:**
- Missing environment variables
- Database not accessible
- Qdrant not running
- Ollama model not pulled

### "Tool returns no results"

**Check:**
1. Database has data: `docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT COUNT(*) FROM memories;"`
2. User ID matches: Default is `00000000-0000-0000-0000-000000000001`
3. Data is not archived: Check `is_archived` column in memories table

## 📝 Development

### Running Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5434
export POSTGRES_DB=aistack
export POSTGRES_USER=aistack_user
export POSTGRES_PASSWORD=your_password
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export OLLAMA_HOST=localhost
export OLLAMA_PORT=11434

# Run server
python server.py
```

### Adding New Tools

1. **Define tool function** in `server.py`:
```python
async def my_new_tool(param1: str) -> str:
    """Tool description."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Your logic here
        result = await conn.fetchval("SELECT ...")
    return result
```

2. **Add tool definition** to `TOOLS` list:
```python
Tool(
    name="my_new_tool",
    description="What this tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"],
    },
)
```

3. **Add to tool_map** in `call_tool()`:
```python
"my_new_tool": lambda: my_new_tool(arguments["param1"]),
```

4. **Rebuild image**: `./build.sh`

## 📚 Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Qdrant Client Documentation](https://qdrant.tech/documentation/quick-start/)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)

## 🔒 Security

- Server runs as non-root user (UID 1000)
- Database connections use connection pooling (2-10 connections)
- Passwords should be set via environment variables (never hardcoded)
- Single-user mode reduces attack surface
- All queries use parameterized statements (SQL injection prevention)

## 📊 Performance

- **Connection pooling**: 2-10 PostgreSQL connections
- **Async I/O**: All database and HTTP calls are non-blocking
- **Vector search**: Qdrant performs sub-100ms searches even with 100k+ memories
- **Caching**: Consider adding Redis for frequently accessed data

## 🎯 Future Enhancements

- [ ] Tool usage analytics
- [ ] Response caching (Redis)
- [ ] Batch operations support
- [ ] Streaming results for large queries
- [ ] Multi-user support
- [ ] Role-based access control
- [ ] Query optimization hints
- [ ] Custom tool registration via API

---

**MCP Server for AI Stack - Bridging AI agents with your personal knowledge base** 🤖
