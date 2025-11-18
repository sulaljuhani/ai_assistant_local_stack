# AI Stack - n8n Workflows

This directory contains 18 n8n workflow JSON files that automate various aspects of the AI Stack.

## 🎯 Purpose

These workflows provide:
- Task, reminder, and event management APIs
- Automated data cleanup and maintenance
- OpenMemory integration (store, search, enrich)
- Vault file watching and embedding
- External service sync (Todoist, Google Calendar)
- Chat history imports (ChatGPT, Claude, Gemini)
- Hybrid sync strategy (realtime + scheduled)

## 📦 Workflow List

### Core Workflows (Tasks, Reminders, Events)

| File | Name | Trigger | Description |
|------|------|---------|-------------|
| `01-create-reminder.json` | Create Reminder | Webhook `/create-reminder` | Creates reminders in PostgreSQL |
| `02-create-task.json` | Create Task | Webhook `/create-task` | Creates tasks with status and priority |
| `03-create-event.json` | Create Event | Webhook `/create-event` | Creates calendar events |
| `04-fire-reminders.json` | Fire Reminders | Schedule (every 5min) | Checks for due reminders and fires them |
| `05-daily-summary.json` | Daily Summary | Schedule (8 AM daily) | Generates daily task/event summary |
| `06-expand-recurring-tasks.json` | Expand Recurring Tasks | Schedule (midnight) | Creates instances from recurring tasks |
| `08-cleanup-old-data.json` | Cleanup Old Data | Schedule (weekly 2 AM) | Archives old records, decays memory salience |

### Vault & Document Management

| File | Name | Trigger | Description |
|------|------|---------|-------------|
| `07-watch-vault.json` | Watch Vault - Re-embed Files | Webhook `/reembed-file` | Re-embeds changed vault files (realtime) |
| `15-watch-documents.json` | Watch Documents | Webhook `/embed-document` | Embeds general documents (txt, pdf, json, md) |
| `18-scheduled-vault-sync.json` | Scheduled Vault Sync | Schedule (every 12h) | Fallback sync for files missed by realtime watcher |

### OpenMemory Workflows

| File | Name | Trigger | Description |
|------|------|---------|-------------|
| `09-store-chat-turn.json` | Store Chat Turn | Webhook `/store-chat-turn` | Stores individual chat messages as memories |
| `10-search-and-summarize.json` | Search and Summarize Memories | Webhook `/search-memories` | Vector search with optional LLM summary |
| `11-enrich-memories.json` | Enrich Memories | Schedule (3 AM daily) | Analyzes frequently accessed memories |
| `12-sync-memory-to-vault.json` | Sync Memory to Vault | Schedule (every 6h) | Exports high-salience memories as MD files |

### External Service Sync

| File | Name | Trigger | Description |
|------|------|---------|-------------|
| `13-todoist-sync.json` | Todoist Sync | Schedule (every 15min) | Bidirectional sync with Todoist |
| `14-google-calendar-sync.json` | Google Calendar Sync | Schedule (every 15min) | Bidirectional sync with Google Calendar |

### Import Workflows

| File | Name | Trigger | Description |
|------|------|---------|-------------|
| `16-import-claude-export.json` | Import Claude Export | Webhook `/import-claude` | Imports Claude conversation exports |
| `17-import-gemini-export.json` | Import Gemini Export | Webhook `/import-gemini` | Imports Gemini (Google Takeout) exports |

## 🚀 Installation

### 1. Import Workflows into n8n

```bash
# Copy workflows to n8n data directory
cp n8n-workflows/*.json /mnt/user/appdata/n8n/

# Or use n8n UI: Settings > Import from file
```

### 2. Configure Credentials

In n8n UI, add credentials for:

- **PostgreSQL** (`postgres-ai-stack`)
  - Host: `postgres-ai-stack`
  - Port: `5432`
  - Database: `aistack`
  - User: `aistack_user`
  - Password: `<your-password>`

- **Todoist API** (`todoist-credentials`) *(optional)*
  - API Token: From Todoist settings

- **Google Calendar OAuth2** (`google-calendar-credentials`) *(optional)*
  - OAuth2 credentials from Google Cloud Console

### 3. Activate Workflows

In n8n UI, activate each workflow by clicking the toggle switch.

## 📖 Usage Examples

### Create a Reminder

```bash
curl -X POST http://n8n-ai-stack:5678/webhook/create-reminder \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Take medication",
    "description": "Take daily vitamins",
    "remind_at": "2025-11-18T09:00:00Z",
    "priority": "high",
    "category": "Health"
  }'
```

### Store Chat Turn (OpenMemory)

```bash
curl -X POST http://n8n-ai-stack:5678/webhook/store-chat-turn \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv-123",
    "conversation_title": "Docker Help",
    "content": "Docker containers provide isolated environments for applications",
    "source": "chat",
    "salience_score": 0.8
  }'
```

### Search Memories

```bash
curl -X POST http://n8n-ai-stack:5678/webhook/search-memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I set up Docker?",
    "limit": 10,
    "summarize": true
  }'
```

### Re-embed Vault File

```bash
curl -X POST http://n8n-ai-stack:5678/webhook/reembed-file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/mnt/user/appdata/ai_stack/vault/daily/2025-11-18.md",
    "relative_path": "daily/2025-11-18.md",
    "file_hash": "abc123...",
    "file_size": 1234
  }'
```

### Import Claude Export

```bash
curl -X POST http://n8n-ai-stack:5678/webhook/import-claude \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/mnt/user/appdata/ai_stack/imports/claude-export.json"
  }'
```

## 🔄 Workflow Dependencies

Workflows interact with:

- **PostgreSQL** - All workflows
- **Qdrant** - Memory and document workflows
- **Ollama** - Embedding generation and LLM summaries
- **File System** - Vault and document workflows
- **External APIs** - Todoist, Google Calendar (optional)

## ⚙️ Configuration

### Environment Variables (for n8n container)

The workflows expect these services to be accessible:

- `postgres-ai-stack:5432` - PostgreSQL
- `qdrant-ai-stack:6333` - Qdrant
- `ollama-ai-stack:11434` - Ollama
- `redis-ai-stack:6379` - Redis (for n8n queue)

### Webhook Security

For production, consider adding:
- API keys to webhook paths
- IP whitelisting
- Rate limiting via nginx/reverse proxy

Example secure webhook:
```
/webhook/create-reminder?key=your-secret-key
```

## 🐛 Troubleshooting

### Workflow Execution Failed

1. **Check logs**: n8n UI > Executions tab
2. **Verify credentials**: Settings > Credentials
3. **Test connectivity**:
   ```bash
   docker exec n8n-ai-stack curl http://postgres-ai-stack:5432
   docker exec n8n-ai-stack curl http://qdrant-ai-stack:6333/collections
   docker exec n8n-ai-stack curl http://ollama-ai-stack:11434/api/tags
   ```

### Webhook Not Responding

- Check n8n container is running: `docker ps | grep n8n`
- Verify webhook is active in n8n UI
- Check firewall/port mapping: Port 5678 should be open

### Embedding Generation Slow

- Verify Ollama has `nomic-embed-text` model pulled
- Check GPU availability (if using GPU acceleration)
- Monitor Ollama logs: `docker logs ollama-ai-stack`

### PostgreSQL Connection Refused

- Verify PostgreSQL container is running
- Check password in credentials
- Test connection: `docker exec postgres-ai-stack psql -U aistack_user -d aistack`

## 📊 Performance Notes

- **Fire Reminders**: Runs every 5 minutes, low impact
- **Todoist/Calendar Sync**: Every 15 minutes, minimal API calls
- **Daily Summary**: Once daily at 8 AM
- **Cleanup**: Weekly, may take 1-5 minutes
- **Enrich Memories**: Daily at 3 AM, processes 20 memories
- **Scheduled Vault Sync**: Every 12 hours, scans recent files only

## 🔒 Security Considerations

- **Single-user mode**: All operations use default UUID
- **File access**: Workflows have read/write access to `/mnt/user/appdata/ai_stack/vault`
- **External APIs**: Todoist and Google Calendar credentials stored in n8n
- **Webhooks**: No authentication by default - add API keys for production

## 🎯 Integration Points

### MCP Server Integration

AnythingLLM and Claude Desktop can call these n8n webhooks via:
- MCP tools that make HTTP requests
- AnythingLLM custom skills (see `anythingllm-skills/`)

### Vault Watcher Integration

The file watcher scripts (`scripts/vault-watcher/`) trigger workflow 07:
```bash
# File watcher calls this webhook when file changes
curl -X POST http://n8n-ai-stack:5678/webhook/reembed-file \
  -d '{"file_path": "...", "file_hash": "..."}'
```

### Hybrid Sync Strategy

**Realtime**: Workflow 07 (triggered by file watcher)
**Scheduled**: Workflow 18 (every 12h, scans for missed files)

This ensures 100% coverage even if file watcher misses events.

## ✨ Features

✅ 18 complete workflows
✅ Webhook and scheduled triggers
✅ PostgreSQL, Qdrant, Ollama integration
✅ Bidirectional external service sync
✅ Hybrid sync strategy (realtime + scheduled)
✅ OpenMemory multi-sector storage
✅ Automatic memory enrichment
✅ Import from ChatGPT, Claude, Gemini
✅ Vector search with LLM summarization
✅ Automatic data cleanup and maintenance

---

**Complete n8n automation for the AI Stack** 🤖✨
