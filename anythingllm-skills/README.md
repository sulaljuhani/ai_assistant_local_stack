# AI Stack - AnythingLLM Custom Skills

This directory contains 6 custom JavaScript skills for AnythingLLM that enable the AI to interact with the AI Stack system via the Python FastAPI backend.

## 🎯 Purpose

These skills allow AnythingLLM to:
- Create reminders, tasks, and events
- Store important information as memories
- Search through stored memories and past conversations
- Import chat history from other AI platforms (ChatGPT, Claude, Gemini)

All skills call the LangGraph Agents REST API (Python FastAPI with APScheduler).

## 📦 Skills List

| File | Skill Name | Description |
|------|------------|-------------|
| `create-reminder.js` | create-reminder | Creates reminders with date/time |
| `create-task.js` | create-task | Creates tasks with optional due dates |
| `create-event.js` | create-event | Creates calendar events with start/end times |
| `search-memory.js` | search-memory | Searches stored memories using vector similarity |
| `store-memory.js` | store-memory | Stores important information as memories |
| `import-chat-history.js` | import-chat-history | Imports chat exports from various platforms |

## 🚀 Installation

### 1. Copy Skills to AnythingLLM

AnythingLLM loads custom skills from its data directory:

```bash
# For unRAID
cp anythingllm-skills/*.js /mnt/user/appdata/anythingllm/custom-skills/

# For Docker
docker cp anythingllm-skills/. anythingllm-ai-stack:/app/server/storage/custom-skills/
```

### 2. Configure Environment Variables

In your AnythingLLM container, set:

```bash
# LangGraph Agents API URL
LANGGRAPH_API_URL=http://langgraph-agents:8080

# Optional: User ID for memory operations (defaults to 'anythingllm')
USER_ID=your-user-id
```

### 3. Restart AnythingLLM

```bash
docker restart anythingllm-ai-stack
```

### 4. Verify Installation

In AnythingLLM chat:
1. Go to Workspace Settings
2. Navigate to "Agent Skills"
3. You should see all 6 custom skills listed
4. Enable the skills you want to use

## 📖 Usage Examples

### Create a Reminder

**User**: "Remind me to take my medication at 9 AM tomorrow"

**AI**: Uses `create-reminder` skill
```json
{
  "title": "Take medication",
  "remind_at": "2025-11-19T09:00:00Z",
  "priority": "high",
  "category": "Health"
}
```

**Result**: ✅ Reminder created and will fire at 9 AM

---

### Create a Task

**User**: "Add 'Fix Docker configuration' to my todo list"

**AI**: Uses `create-task` skill
```json
{
  "title": "Fix Docker configuration",
  "priority": "high",
  "category": "DevOps"
}
```

**Result**: ✅ Task added to database and synced to Todoist (if configured)

---

### Create an Event

**User**: "Schedule a team meeting tomorrow at 2 PM for 1 hour"

**AI**: Uses `create-event` skill
```json
{
  "title": "Team Meeting",
  "start_time": "2025-11-19T14:00:00Z",
  "end_time": "2025-11-19T15:00:00Z",
  "category": "Work"
}
```

**Result**: 📅 Event created and synced to Google Calendar (if configured)

---

### Store a Memory

**User**: "Remember that I prefer Python over JavaScript for backend work"

**AI**: Uses `store-memory` skill
```json
{
  "content": "User prefers Python over JavaScript for backend development",
  "conversation_title": "Coding Preferences",
  "salience_score": 0.8
}
```

**Result**: 💾 Memory stored and classified (emotional sector)

---

### Search Memories

**User**: "What did I say about Docker configuration?"

**AI**: Uses `search-memory` skill
```json
{
  "query": "Docker configuration",
  "limit": 10
}
```

**Result**: 🔍 Returns relevant memories with similarity scores

---

### Import Chat History

**User**: "Import my ChatGPT conversations from /imports/chatgpt.json"

**AI**: Uses `import-chat-history` skill
```json
{
  "source": "chatgpt",
  "file_path": "/mnt/user/appdata/ai_stack/imports/chatgpt.json"
}
```

**Result**: ✅ Imports all conversations as searchable memories

## 🔧 Technical Details

### How Skills Work

1. **AnythingLLM Agent** decides when to use a skill based on user intent
2. **Skill handler** makes HTTP POST request to LangGraph Agents REST API
3. **FastAPI endpoint** processes the request:
   - Validates input with Pydantic models
   - Stores data in PostgreSQL using asyncpg
   - Generates embeddings via Ollama (for memories)
   - Stores vectors in Qdrant (for memories)
   - Triggers scheduled jobs via APScheduler
   - Syncs with external services (Todoist, Google Calendar)
4. **Result** is returned to AnythingLLM and shown to user

### Architecture

```
User → AnythingLLM → Custom Skill → Python FastAPI → PostgreSQL/Qdrant/Ollama
                                        ↓
                                   APScheduler (background jobs)
```

### REST API Endpoints

Skills call these Python FastAPI endpoints:

- `http://langgraph-agents:8080/api/reminders/create`
- `http://langgraph-agents:8080/api/tasks/create`
- `http://langgraph-agents:8080/api/events/create`
- `http://langgraph-agents:8080/api/memory/store`
- `http://langgraph-agents:8080/api/memory/search`
- `http://langgraph-agents:8080/api/import/chatgpt`
- `http://langgraph-agents:8080/api/import/claude`
- `http://langgraph-agents:8080/api/import/gemini`

**API Documentation**: http://your-server:8080/docs (Swagger/OpenAPI)

## ⚙️ Configuration

### Environment Variables

Set in AnythingLLM container:

```bash
# Required - LangGraph Agents API URL
LANGGRAPH_API_URL=http://langgraph-agents:8080

# Optional - User ID for memory operations
USER_ID=anythingllm  # Defaults to 'anythingllm' if not set
```

### Skill Parameters

Each skill defines:
- **name**: Unique identifier
- **description**: When the AI should use this skill
- **parameters**: Required and optional parameters
- **handler**: Async function that executes the skill
- **examples**: Sample prompts and expected calls

### Memory Sectors

Memories are automatically classified into sectors:

- **Semantic**: Facts, definitions, explanations
- **Episodic**: Events, experiences, what happened
- **Procedural**: How-to, steps, instructions
- **Emotional**: Preferences, feelings, likes/dislikes
- **Reflective**: Insights, patterns, learnings

Classification is done by Python code (`tools/memory.py`) using keyword matching and context analysis.

## 🐛 Troubleshooting

### Skill Not Appearing in AnythingLLM

1. Check file is in correct directory:
   ```bash
   docker exec anythingllm-ai-stack ls /app/server/storage/custom-skills/
   ```
2. Verify file has `.js` extension
3. Check for syntax errors in skill file
4. Restart AnythingLLM container

### Skill Execution Fails

1. **Check LangGraph Agents is running**:
   ```bash
   docker ps | grep langgraph-agents
   ```

2. **Verify API URL**:
   ```bash
   docker exec anythingllm-ai-stack env | grep LANGGRAPH_API_URL
   ```

3. **Test API manually**:
   ```bash
   curl -X POST http://langgraph-agents:8080/api/reminders/create \
     -H "Content-Type: application/json" \
     -d '{"title": "Test", "remind_at": "2025-11-20T09:00:00Z", "priority": "medium", "category": "General"}'
   ```

4. **Check API health**:
   ```bash
   curl http://langgraph-agents:8080/health
   ```

5. **View API docs**:
   - Open Swagger UI: http://your-server:8080/docs
   - Test endpoints interactively

### Memory Search Returns No Results

1. **Verify embeddings are being generated**:
   - Check Ollama has `nomic-embed-text` model
   - Test: `docker exec ollama-ai-stack ollama list`

2. **Check Qdrant has vectors**:
   ```bash
   curl http://localhost:6333/collections/memories
   ```

3. **Verify memories exist in PostgreSQL**:
   ```bash
   docker exec postgres-ai-stack psql -U aistack_user -d aistack \
     -c "SELECT COUNT(*) FROM memories;"
   ```

### Import Returns "Duplicate"

This is normal - the system detects duplicate imports via file hash to prevent re-importing the same data. If you need to re-import:

1. Delete from `imported_chats` table:
   ```sql
   DELETE FROM imported_chats WHERE file_hash = 'your-hash';
   ```
2. Run import again

## 📊 Performance

- **Reminder/Task/Event creation**: ~50-200ms
- **Memory storage**: ~500-1000ms (includes embedding generation)
- **Memory search**: ~200-500ms
- **Chat import**: ~1-5 seconds per conversation (depends on size)

## 🔒 Security

- Skills run within AnythingLLM's Node.js environment
- Network access limited to LangGraph Agents API
- No direct database access (goes through Python API)
- All inputs validated with Pydantic models
- User ID defaults to 'anythingllm' (single-user mode)
- SQL injection prevented by parameterized queries

## 🎯 Best Practices

### For Users

1. **Be specific** when asking AI to create reminders/tasks
   - ✅ "Remind me to call John at 2 PM tomorrow"
   - ❌ "Remind me about John"

2. **Provide context** when storing memories
   - ✅ "Remember that I fixed the network issue by recreating the bridge"
   - ❌ "Remember this fix"

3. **Use natural language** for search
   - ✅ "What did I say about Docker configuration?"
   - ✅ "Search my memories for project deadlines"

### For Developers

1. **Error handling**: All skills return `{ success: boolean, error?: string }`
2. **Validation**: Validate parameters before sending to webhook
3. **Timeouts**: Consider adding timeout to fetch() calls
4. **Logging**: Use console.log() for debugging (visible in AnythingLLM logs)

## ✨ Features

✅ 6 complete custom skills
✅ Natural language interface for all AI Stack features
✅ Automatic memory classification (5 sectors)
✅ Vector search with similarity scores
✅ Import from ChatGPT, Claude, Gemini
✅ Integration with Todoist and Google Calendar
✅ Error handling and user-friendly messages
✅ Example prompts for each skill

## 🔗 Related Components

- **LangGraph Agents**: `containers/langgraph-agents/` - Python FastAPI backend with multi-agent system
- **REST API Routers**: `containers/langgraph-agents/routers/` - Endpoint implementations
- **Background Services**: `containers/langgraph-agents/services/` - APScheduler jobs
- **MCP Server**: `containers/mcp-server/` - Alternative API for Claude Desktop
- **Database Schema**: `migrations/` - PostgreSQL tables
- **Qdrant Collections**: `scripts/qdrant/` - Vector storage initialization
- **Migration Documentation**: `docs/N8N_TO_PYTHON_MIGRATION_PLAN.md` - Full migration details

---

**Enable your AI to remember, recall, and manage your digital life** 🧠✨

> **Note**: These skills previously called n8n webhooks but have been migrated to call Python FastAPI endpoints for better performance, type safety, and maintainability.
