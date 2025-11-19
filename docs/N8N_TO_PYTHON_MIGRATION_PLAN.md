# n8n to Python Migration Plan

## Overview
This document outlines the complete migration strategy from n8n workflows to native Python tools and services. The migration will consolidate all workflow automation into the LangGraph multi-agent system and scheduled Python services.

## Migration Goals
1. **Eliminate n8n dependency** - Remove n8n service entirely
2. **Improve performance** - Native Python is faster than n8n's node-based execution
3. **Better maintainability** - Single codebase in Python
4. **Enhanced security** - Centralized validation and security patterns
5. **Simplified deployment** - One less service to manage

---

## Current State Analysis

### n8n Workflows Inventory (21 workflows)

#### Category 1: Task Management (7 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `01-create-reminder.json` | Webhook `/create-reminder` | FastAPI endpoint `/api/reminders/create` |
| `02-create-task.json` | Webhook `/create-task` | FastAPI endpoint `/api/tasks/create` |
| `03-create-event.json` | Webhook `/create-event` | FastAPI endpoint `/api/events/create` |
| `04-fire-reminders.json` | Schedule (every 5 min) | APScheduler job every 5 min |
| `05-daily-summary.json` | Schedule (8 AM daily) | APScheduler cron "0 8 * * *" |
| `06-expand-recurring-tasks.json` | Schedule (midnight) | APScheduler cron "0 0 * * *" |
| `08-cleanup-old-data.json` | Schedule (weekly 2 AM) | APScheduler cron "0 2 * * 0" |

#### Category 2: Vault & Documents (3 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `07-watch-vault.json` | Webhook `/reembed-file` | FastAPI endpoint `/api/vault/reembed` |
| `15-watch-documents.json` | Webhook `/embed-document` | FastAPI endpoint `/api/documents/embed` |
| `18-scheduled-vault-sync.json` | Schedule (every 12h) | APScheduler job every 12h |

#### Category 3: OpenMemory (4 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `09-store-chat-turn.json` | Webhook `/store-chat-turn` | FastAPI endpoint `/api/memory/store` |
| `10-search-and-summarize.json` | Webhook `/search-memories` | FastAPI endpoint `/api/memory/search` |
| `11-enrich-memories.json` | Schedule (3 AM daily) | APScheduler cron "0 3 * * *" |
| `12-sync-memory-to-vault.json` | Schedule (every 6h) | APScheduler job every 6h |

#### Category 4: External Services (2 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `13-todoist-sync.json` | Schedule (every 15 min) | APScheduler job every 15 min |
| `14-google-calendar-sync.json` | Schedule (every 15 min) | APScheduler job every 15 min |

#### Category 5: Imports (4 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `16-import-claude-export.json` | Webhook `/import-claude` | FastAPI endpoint `/api/import/claude` |
| `17-import-gemini-export.json` | Webhook `/import-gemini` | FastAPI endpoint `/api/import/gemini` |
| `19-import-chatgpt-export.json` | Webhook `/import-chatgpt` | FastAPI endpoint `/api/import/chatgpt` |
| `19-food-log.json` (variants) | Webhook `/log-food` | Already exists: `/api/food/log` |

#### Category 6: System Maintenance (2 workflows)
| Workflow | Trigger | Migration Target |
|----------|---------|------------------|
| `20-automated-backups.json` | Schedule | APScheduler job |
| `21-health-check.json` | Schedule | APScheduler job |

---

## New Python Architecture

### Directory Structure
```
containers/langgraph-agents/
├── tools/
│   ├── database.py           # Existing - enhanced with new operations
│   ├── vector.py             # Existing - enhanced
│   ├── hybrid.py             # Existing
│   ├── memory.py             # NEW - OpenMemory operations
│   ├── documents.py          # NEW - Document embedding
│   ├── integrations.py       # NEW - Todoist, Google Calendar
│   └── maintenance.py        # NEW - System maintenance tasks
├── services/
│   ├── scheduler.py          # NEW - APScheduler configuration
│   ├── reminders.py          # NEW - Reminder firing service
│   ├── sync_service.py       # NEW - External sync services
│   └── backup_service.py     # NEW - Backup operations
├── routers/
│   ├── tasks.py              # NEW - Task endpoints
│   ├── reminders.py          # NEW - Reminder endpoints
│   ├── events.py             # NEW - Event endpoints
│   ├── memory.py             # NEW - Memory endpoints
│   ├── documents.py          # NEW - Document endpoints
│   ├── imports.py            # NEW - Import endpoints
│   └── vault.py              # NEW - Vault endpoints
├── middleware/
│   └── validation.py         # NEW - Centralized input validation
└── main.py                   # UPDATED - Register new routers & scheduler
```

### Technology Stack
- **FastAPI** - Replace n8n webhooks with REST endpoints
- **APScheduler** - Replace n8n schedules with Python scheduler
- **Pydantic** - Input validation and serialization
- **asyncpg** - PostgreSQL operations (existing)
- **qdrant-client** - Vector operations (existing)
- **httpx** - External API calls (Todoist, Google Calendar)

---

## Migration Steps (Detailed)

### Phase 1: Foundation Setup

#### Step 1.1: Install Dependencies
Add to `requirements.txt`:
```
apscheduler==3.10.4
httpx==0.27.0
python-multipart==0.0.9
```

#### Step 1.2: Create Validation Middleware
**File:** `containers/langgraph-agents/middleware/validation.py`

Port the validation logic from `n8n-workflows/utils/input-validation.js` to Python:
- Type validation
- Length constraints
- Range validation
- Enum validation
- Regex patterns
- Sanitization

#### Step 1.3: Create Scheduler Service
**File:** `containers/langgraph-agents/services/scheduler.py`

Configure APScheduler with:
- AsyncIOScheduler
- Job persistence (SQLite or Redis)
- Error handling and logging
- Job monitoring

---

### Phase 2: Task Management Migration

#### Step 2.1: Create Task Router
**File:** `containers/langgraph-agents/routers/tasks.py`

Endpoints:
- `POST /api/tasks/create` - Create task (from workflow 02)
- `PUT /api/tasks/{task_id}` - Update task
- `DELETE /api/tasks/{task_id}` - Delete task
- `GET /api/tasks` - List tasks with filters

Logic from `02-create-task.json`:
1. Validate input (title, description, status, priority, due_date, category)
2. Get category ID from database
3. Insert task with parameterized query
4. Return created task

#### Step 2.2: Create Reminder Router
**File:** `containers/langgraph-agents/routers/reminders.py`

Endpoints:
- `POST /api/reminders/create` - Create reminder (from workflow 01)
- `PUT /api/reminders/{reminder_id}` - Update reminder
- `DELETE /api/reminders/{reminder_id}` - Delete reminder
- `GET /api/reminders` - List reminders

Logic from `01-create-reminder.json`:
1. Validate input (title, description, remind_at, priority, category)
2. Verify remind_at is future datetime
3. Insert reminder
4. Return created reminder

#### Step 2.3: Create Event Router
**File:** `containers/langgraph-agents/routers/events.py`

Endpoints:
- `POST /api/events/create` - Create event (from workflow 03)
- `PUT /api/events/{event_id}` - Update event
- `DELETE /api/events/{event_id}` - Delete event
- `GET /api/events` - List events

Logic from `03-create-event.json`:
1. Validate input (title, description, start_time, end_time, location)
2. Verify start_time < end_time
3. Check for time conflicts (optional)
4. Insert event
5. Return created event

#### Step 2.4: Create Reminder Firing Service
**File:** `containers/langgraph-agents/services/reminders.py`

Function: `fire_reminders()`

Logic from `04-fire-reminders.json`:
1. Query reminders WHERE remind_at <= NOW() AND is_completed = FALSE
2. For each reminder:
   - Log reminder fired
   - Mark as completed
   - Send notification (future: integrate with notification service)
3. Return count of fired reminders

Schedule: Every 5 minutes

#### Step 2.5: Create Daily Summary Service
**File:** `containers/langgraph-agents/services/reminders.py`

Function: `generate_daily_summary()`

Logic from `05-daily-summary.json`:
1. Get today's tasks
2. Get today's events
3. Get today's reminders
4. Format summary
5. Send notification (future: integrate with notification service)

Schedule: Daily at 8 AM

#### Step 2.6: Create Recurring Task Expansion Service
**File:** `containers/langgraph-agents/services/reminders.py`

Function: `expand_recurring_tasks()`

Logic from `06-expand-recurring-tasks.json`:
1. Query tasks WHERE is_recurring = TRUE
2. For each recurring task:
   - Calculate next occurrence based on recurrence_pattern
   - Create new task instance
   - Update last_expanded timestamp
3. Return count of expanded tasks

Schedule: Daily at midnight

#### Step 2.7: Create Data Cleanup Service
**File:** `containers/langgraph-agents/services/maintenance.py`

Function: `cleanup_old_data()`

Logic from `08-cleanup-old-data.json`:
1. Archive completed tasks older than 90 days
2. Archive completed reminders older than 90 days
3. Archive past events older than 365 days
4. Decay memory salience (reduce by 10% for memories not accessed in 30 days)
5. Return cleanup statistics

Schedule: Weekly on Sunday at 2 AM

---

### Phase 3: Vault & Document Migration

#### Step 3.1: Create Document Tools
**File:** `containers/langgraph-agents/tools/documents.py`

Tools:
- `embed_document()` - Generate embedding for document
- `reembed_file()` - Re-embed changed file
- `sync_vault_files()` - Sync all vault files

#### Step 3.2: Create Vault Router
**File:** `containers/langgraph-agents/routers/vault.py`

Endpoints:
- `POST /api/vault/reembed` - Re-embed file (from workflow 07)
- `POST /api/vault/sync` - Trigger full sync

Logic from `07-watch-vault.json`:
1. Receive file_path, file_hash
2. Check if file_hash changed
3. Read file content
4. Generate embedding with Ollama
5. Upsert to Qdrant
6. Update database record

#### Step 3.3: Create Document Router
**File:** `containers/langgraph-agents/routers/documents.py`

Endpoints:
- `POST /api/documents/embed` - Embed document (from workflow 15)

Logic from `15-watch-documents.json`:
1. Receive file_path, file_type
2. Read file content (txt, pdf, json, md)
3. Extract text from PDF if needed
4. Chunk document
5. Generate embeddings
6. Upsert to Qdrant knowledge_base collection
7. Return document ID

#### Step 3.4: Create Scheduled Vault Sync Service
**File:** `containers/langgraph-agents/services/sync_service.py`

Function: `scheduled_vault_sync()`

Logic from `18-scheduled-vault-sync.json`:
1. List all files in vault directory
2. For each file:
   - Check file_hash
   - If changed, trigger reembed
3. Return sync statistics

Schedule: Every 12 hours

---

### Phase 4: OpenMemory Migration

#### Step 4.1: Create Memory Tools
**File:** `containers/langgraph-agents/tools/memory.py`

Tools:
- `store_chat_turn()` - Store conversation turn
- `search_memories()` - Search with optional summary
- `enrich_memory()` - Enrich frequently accessed memories
- `classify_memory_sectors()` - Multi-sector classification

#### Step 4.2: Create Memory Router
**File:** `containers/langgraph-agents/routers/memory.py`

Endpoints:
- `POST /api/memory/store` - Store chat turn (from workflow 09)
- `POST /api/memory/search` - Search memories (from workflow 10)

**Store Endpoint Logic** (from `09-store-chat-turn.json`):
1. Validate input (user_id, conversation_id, role, content)
2. Upsert conversation record
3. Classify content into sectors:
   - Semantic (facts, definitions)
   - Episodic (events, experiences)
   - Procedural (how-tos, steps)
   - Emotional (preferences, feelings)
   - Reflective (insights, patterns)
4. Create memory record
5. Generate embedding with Ollama (nomic-embed-text, 768 dims)
6. Insert sector metadata
7. Upsert vectors to Qdrant (one point per sector)
8. Return memory ID and sectors

**Search Endpoint Logic** (from `10-search-and-summarize.json`):
1. Validate input (query, user_id, limit, summarize)
2. Generate query embedding
3. Search Qdrant for similar memories
4. If summarize=true:
   - Concatenate top results
   - Send to LLM for summarization
   - Return summary + results
5. Else return raw results

#### Step 4.3: Create Memory Enrichment Service
**File:** `containers/langgraph-agents/services/memory_service.py`

Function: `enrich_memories()`

Logic from `11-enrich-memories.json`:
1. Query memories with high access_count (> 5) and not enriched recently
2. For each memory:
   - Analyze context and patterns
   - Extract key insights
   - Add enrichment metadata
   - Increase salience score
3. Return count of enriched memories

Schedule: Daily at 3 AM

#### Step 4.4: Create Memory to Vault Sync Service
**File:** `containers/langgraph-agents/services/memory_service.py`

Function: `sync_memory_to_vault()`

Logic from `12-sync-memory-to-vault.json`:
1. Query memories WHERE salience_score > 0.8
2. Group by conversation
3. For each high-salience conversation:
   - Format as Markdown
   - Include metadata (date, participants, topics)
   - Write to vault as `memory_export_{conversation_id}.md`
4. Return count of exported conversations

Schedule: Every 6 hours

---

### Phase 5: External Service Integration

#### Step 5.1: Create Integration Tools
**File:** `containers/langgraph-agents/tools/integrations.py`

Tools:
- `sync_todoist()` - Bidirectional Todoist sync
- `sync_google_calendar()` - Bidirectional Google Calendar sync

Dependencies:
```python
import httpx
from datetime import datetime, timezone
```

#### Step 5.2: Create Todoist Sync Service
**File:** `containers/langgraph-agents/services/sync_service.py`

Function: `sync_todoist()`

Logic from `13-todoist-sync.json`:
1. Fetch all Todoist tasks via API:
   ```python
   GET https://api.todoist.com/rest/v2/tasks
   Headers: Authorization: Bearer {TODOIST_API_KEY}
   ```
2. For each Todoist task:
   - Check if exists locally (by todoist_id)
   - If not, create local task
   - If exists and modified, update local task
3. Fetch local tasks modified since last sync
4. For each modified local task:
   - Push to Todoist API (POST/PATCH)
   - Update todoist_id mapping
5. Return sync statistics

Schedule: Every 15 minutes

Environment Variables:
```env
TODOIST_API_KEY=your_api_key_here
TODOIST_SYNC_ENABLED=true
```

#### Step 5.3: Create Google Calendar Sync Service
**File:** `containers/langgraph-agents/services/sync_service.py`

Function: `sync_google_calendar()`

Logic from `14-google-calendar-sync.json`:
1. Authenticate with Google Calendar API (OAuth2)
2. Fetch calendar events (next 30 days):
   ```python
   GET https://www.googleapis.com/calendar/v3/calendars/primary/events
   ```
3. For each Google event:
   - Check if exists locally (by google_event_id)
   - If not, create local event
   - If exists and modified, update local event
4. Fetch local events modified since last sync
5. For each modified local event:
   - Push to Google Calendar API
   - Update google_event_id mapping
6. Return sync statistics

Schedule: Every 15 minutes

Environment Variables:
```env
GOOGLE_CALENDAR_CREDENTIALS_PATH=/data/google_credentials.json
GOOGLE_CALENDAR_SYNC_ENABLED=true
```

---

### Phase 6: Import Workflows Migration

#### Step 6.1: Create Import Router
**File:** `containers/langgraph-agents/routers/imports.py`

Endpoints:
- `POST /api/import/claude` - Import Claude export (from workflow 16)
- `POST /api/import/gemini` - Import Gemini export (from workflow 17)
- `POST /api/import/chatgpt` - Import ChatGPT export (from workflow 19)

#### Step 6.2: Claude Import Logic
**Endpoint:** `POST /api/import/claude`

Logic from `16-import-claude-export.json`:
1. Accept file upload (multipart/form-data)
2. Parse JSON structure:
   ```json
   {
     "conversations": [
       {
         "name": "Conversation title",
         "chat_messages": [
           {"sender": "human", "text": "...", "created_at": "..."},
           {"sender": "assistant", "text": "...", "created_at": "..."}
         ]
       }
     ]
   }
   ```
3. For each conversation:
   - Create conversation record
   - For each message:
     - Store as memory via `store_chat_turn()`
     - Generate embedding
     - Classify sectors
4. Return import statistics

#### Step 6.3: Gemini Import Logic
**Endpoint:** `POST /api/import/gemini`

Logic from `17-import-gemini-export.json`:
1. Accept file upload (Google Takeout ZIP)
2. Extract Gemini conversations
3. Parse JSON structure (similar to Claude)
4. For each conversation:
   - Create conversation record
   - For each message:
     - Store as memory
     - Generate embedding
5. Return import statistics

#### Step 6.4: ChatGPT Import Logic
**Endpoint:** `POST /api/import/chatgpt`

Logic from `19-import-chatgpt-export.json`:
1. Accept file upload (conversations.json)
2. Parse JSON structure:
   ```json
   [
     {
       "title": "Conversation title",
       "mapping": {
         "message_id": {
           "message": {
             "author": {"role": "user"},
             "content": {"parts": ["text"]},
             "create_time": 1234567890
           }
         }
       }
     }
   ]
   ```
3. For each conversation:
   - Create conversation record
   - Traverse mapping tree
   - For each message:
     - Store as memory
     - Generate embedding
4. Return import statistics

---

### Phase 7: System Maintenance Migration

#### Step 7.1: Create Backup Service
**File:** `containers/langgraph-agents/services/backup_service.py`

Function: `automated_backup()`

Logic from `20-automated-backups.json`:
1. Create timestamp
2. Backup PostgreSQL:
   ```bash
   pg_dump -h postgres -U aistack_user aistack > backup_{timestamp}.sql
   ```
3. Backup Qdrant collections:
   - Export snapshots via Qdrant API
4. Backup configuration files
5. Compress backups
6. Upload to backup storage (local or S3)
7. Cleanup old backups (keep last 30 days)
8. Return backup statistics

Schedule: Daily at 3 AM

Environment Variables:
```env
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/data/backups
```

#### Step 7.2: Create Health Check Service
**File:** `containers/langgraph-agents/services/maintenance.py`

Function: `health_check()`

Logic from `21-health-check.json`:
1. Check PostgreSQL connection
2. Check Qdrant connection
3. Check Redis connection
4. Check Ollama connection
5. Check disk space
6. Check memory usage
7. If any check fails, send alert
8. Return health status

Schedule: Every 5 minutes

Add endpoint: `GET /health` for external monitoring

---

### Phase 8: Scheduler Registration

#### Step 8.1: Update Main Application
**File:** `containers/langgraph-agents/main.py`

Add scheduler initialization:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.scheduler import setup_scheduler

# Create scheduler
scheduler = AsyncIOScheduler()

# Register scheduled jobs
setup_scheduler(scheduler)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

#### Step 8.2: Create Scheduler Setup
**File:** `containers/langgraph-agents/services/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.reminders import fire_reminders, generate_daily_summary, expand_recurring_tasks
from services.maintenance import cleanup_old_data, health_check
from services.sync_service import scheduled_vault_sync, sync_todoist, sync_google_calendar
from services.memory_service import enrich_memories, sync_memory_to_vault
from services.backup_service import automated_backup

def setup_scheduler(scheduler: AsyncIOScheduler):
    # Fire reminders - every 5 minutes
    scheduler.add_job(fire_reminders, 'interval', minutes=5, id='fire_reminders')

    # Daily summary - 8 AM daily
    scheduler.add_job(generate_daily_summary, 'cron', hour=8, minute=0, id='daily_summary')

    # Expand recurring tasks - midnight daily
    scheduler.add_job(expand_recurring_tasks, 'cron', hour=0, minute=0, id='expand_recurring')

    # Cleanup old data - Sunday 2 AM
    scheduler.add_job(cleanup_old_data, 'cron', day_of_week='sun', hour=2, minute=0, id='cleanup')

    # Vault sync - every 12 hours
    scheduler.add_job(scheduled_vault_sync, 'interval', hours=12, id='vault_sync')

    # Memory enrichment - 3 AM daily
    scheduler.add_job(enrich_memories, 'cron', hour=3, minute=0, id='enrich_memories')

    # Memory to vault sync - every 6 hours
    scheduler.add_job(sync_memory_to_vault, 'interval', hours=6, id='memory_vault_sync')

    # Todoist sync - every 15 minutes (if enabled)
    if settings.todoist_sync_enabled:
        scheduler.add_job(sync_todoist, 'interval', minutes=15, id='todoist_sync')

    # Google Calendar sync - every 15 minutes (if enabled)
    if settings.google_calendar_sync_enabled:
        scheduler.add_job(sync_google_calendar, 'interval', minutes=15, id='gcal_sync')

    # Automated backups - 3 AM daily (if enabled)
    if settings.backup_enabled:
        scheduler.add_job(automated_backup, 'cron', hour=3, minute=0, id='backup')

    # Health check - every 5 minutes
    scheduler.add_job(health_check, 'interval', minutes=5, id='health_check')
```

---

### Phase 9: Integration Updates

#### Step 9.1: Update AnythingLLM Skills
**Files:** `anythingllm-skills/*.js`

Update webhook URLs:
```javascript
// OLD
const n8nUrl = 'http://n8n:5678/webhook/create-reminder';

// NEW
const pythonUrl = 'http://langgraph-agents:8000/api/reminders/create';
```

Files to update:
- `create-reminder.js` → `/api/reminders/create`
- `create-task.js` → `/api/tasks/create`
- `create-event.js` → `/api/events/create`
- `log-food.js` → `/api/food/log` (already exists)
- `store-memory.js` → `/api/memory/store`
- `search-memory.js` → `/api/memory/search`
- `import-chat-history.js` → `/api/import/{claude,gemini,chatgpt}`

#### Step 9.2: Update Vault Watcher
**File:** `scripts/vault-watcher/watch-vault.sh`

Update webhook URL:
```bash
# OLD
N8N_WEBHOOK="http://n8n-ai-stack:5678/webhook/reembed-file"

# NEW
PYTHON_ENDPOINT="http://langgraph-agents:8000/api/vault/reembed"

# Update curl command
curl -X POST "$PYTHON_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{\"file_path\": \"$FILE_PATH\", \"file_hash\": \"$FILE_HASH\"}"
```

#### Step 9.3: Remove n8n Tools from LangGraph
**File:** `containers/langgraph-agents/tools/n8n.py`

Delete this file entirely - no longer needed.

Update `containers/langgraph-agents/tools/__init__.py`:
```python
# Remove
from .n8n import trigger_n8n_workflow, log_food_with_embedding
```

---

### Phase 10: Infrastructure Updates

#### Step 10.1: Update Docker Compose
**File:** `docker-compose.yml`

Remove n8n service:
```yaml
# DELETE THIS SECTION
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n-ai-stack
    ...
```

Update LangGraph service environment (if needed):
```yaml
  langgraph-agents:
    environment:
      # Remove n8n variables
      # - N8N_BASE_URL=http://n8n:5678
      # - N8N_WEBHOOK_PATH=/webhook
```

#### Step 10.2: Update Unraid Templates
**File:** `unraid-templates/my-n8n.xml`

Archive or delete this file:
```bash
mv unraid-templates/my-n8n.xml unraid-templates/archived/my-n8n.xml
```

#### Step 10.3: Update Environment Variables
**File:** `.env`

Remove n8n variables:
```env
# DELETE THESE
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=changeme_secure_password
```

Add new variables:
```env
# Scheduler
SCHEDULER_ENABLED=true

# External sync (optional)
TODOIST_API_KEY=your_key_here
TODOIST_SYNC_ENABLED=false

GOOGLE_CALENDAR_CREDENTIALS_PATH=/data/google_credentials.json
GOOGLE_CALENDAR_SYNC_ENABLED=false

# Backups
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/data/backups
```

---

### Phase 11: Cleanup

#### Step 11.1: Delete n8n Workflows
```bash
# Archive workflows for reference
mkdir -p archives/n8n-workflows-$(date +%Y%m%d)
mv n8n-workflows/*.json archives/n8n-workflows-$(date +%Y%m%d)/

# Delete directory
rm -rf n8n-workflows/
```

#### Step 11.2: Delete n8n Documentation
Archive or update:
- `docs/N8N_WORKFLOW_SECURITY_FIX_GUIDE.md` → Archive
- Update architecture documentation to reflect Python-based system

#### Step 11.3: Clean Database
**Optional:** Delete n8n database (contains only workflow metadata, not user data)

```sql
-- Connect to PostgreSQL
DROP DATABASE IF EXISTS n8n;
```

---

### Phase 12: Testing

#### Step 12.1: Test All Endpoints
Create test script: `tests/test_migrated_endpoints.py`

Test each endpoint:
- Task CRUD operations
- Reminder CRUD operations
- Event CRUD operations
- Memory store/search
- Document embedding
- Vault reembed
- Import endpoints

#### Step 12.2: Test Scheduled Jobs
Manually trigger each scheduled job:
```python
# Test script
from services.reminders import fire_reminders
from services.maintenance import cleanup_old_data
# ... etc

async def test_scheduled_jobs():
    await fire_reminders()
    await generate_daily_summary()
    # ... test each job
```

Verify:
- Jobs execute without errors
- Database operations succeed
- Logs are generated
- Expected side effects occur

#### Step 12.3: Integration Testing
Test full workflows:
1. Create task via AnythingLLM → Verify in database
2. Create reminder → Wait for firing → Verify completion
3. Add file to vault → Trigger watcher → Verify embedding
4. Import conversation → Verify memories created
5. Scheduled sync → Verify external services updated

---

## Migration Checklist

### Pre-Migration
- [ ] Review all n8n workflows and document functionality
- [ ] Identify all webhook callers (AnythingLLM, vault watcher, etc.)
- [ ] Backup current n8n database
- [ ] Backup n8n workflow files

### Development
- [ ] Install new Python dependencies
- [ ] Create validation middleware
- [ ] Create scheduler service
- [ ] Migrate task management workflows (7)
- [ ] Migrate vault & document workflows (3)
- [ ] Migrate OpenMemory workflows (4)
- [ ] Migrate external service sync workflows (2)
- [ ] Migrate import workflows (4)
- [ ] Migrate system maintenance workflows (2)
- [ ] Register all scheduled jobs
- [ ] Update AnythingLLM skills
- [ ] Update vault watcher script
- [ ] Remove n8n tools from LangGraph

### Testing
- [ ] Test all new endpoints
- [ ] Test all scheduled jobs
- [ ] Test AnythingLLM integration
- [ ] Test vault watcher integration
- [ ] Test external service sync (if enabled)
- [ ] Load testing for performance
- [ ] Security audit (SQL injection, XSS, etc.)

### Deployment
- [ ] Update docker-compose.yml
- [ ] Update .env file
- [ ] Remove n8n service
- [ ] Restart stack
- [ ] Verify all services healthy
- [ ] Monitor logs for errors

### Post-Migration
- [ ] Delete n8n workflow files
- [ ] Delete n8n database (optional)
- [ ] Update documentation
- [ ] Archive n8n templates
- [ ] Monitor system for 48 hours
- [ ] Performance comparison (Python vs n8n)

---

## Risk Mitigation

### Rollback Plan
1. Keep n8n workflows archived
2. Keep n8n service configuration
3. Maintain database backup
4. Can restore n8n service in docker-compose
5. Revert AnythingLLM skills and vault watcher

### Monitoring
- Log all endpoint calls
- Track job execution times
- Monitor error rates
- Alert on failed scheduled jobs
- Compare performance metrics

### Validation
- Ensure data integrity (compare DB records before/after)
- Verify all embeddings regenerated correctly
- Confirm external sync working
- Validate import functionality

---

## Expected Benefits

### Performance
- **Faster execution:** Native Python vs Node-based n8n
- **Lower memory:** One less service running
- **Better resource utilization:** No webhook HTTP overhead

### Maintainability
- **Single codebase:** All logic in Python
- **Better IDE support:** Type hints, autocomplete
- **Easier debugging:** Python debugger vs n8n UI
- **Version control:** Python files vs JSON exports

### Security
- **Centralized validation:** Pydantic models
- **Consistent patterns:** No SQL injection risk
- **Better secrets management:** Environment variables
- **Audit trail:** Structured logging

### Development
- **Faster iteration:** Edit Python vs n8n UI
- **Better testing:** Unit tests for all functions
- **Code reuse:** Shared utilities across tools
- **Type safety:** Pydantic validation

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Foundation | Dependencies, validation, scheduler | 2-3 hours |
| Phase 2: Task Management | 7 workflows → Python | 4-6 hours |
| Phase 3: Vault & Documents | 3 workflows → Python | 3-4 hours |
| Phase 4: OpenMemory | 4 workflows → Python | 4-5 hours |
| Phase 5: External Services | 2 workflows → Python | 3-4 hours |
| Phase 6: Imports | 4 workflows → Python | 3-4 hours |
| Phase 7: Maintenance | 2 workflows → Python | 2-3 hours |
| Phase 8: Scheduler | Register all jobs | 1-2 hours |
| Phase 9: Integration Updates | AnythingLLM, vault watcher | 2-3 hours |
| Phase 10: Infrastructure | Docker, env vars | 1-2 hours |
| Phase 11: Cleanup | Delete n8n files | 1 hour |
| Phase 12: Testing | All endpoints and jobs | 4-6 hours |
| **Total** | | **30-42 hours** |

---

## Success Criteria

✅ All 21 n8n workflows migrated to Python
✅ All endpoints responding correctly
✅ All scheduled jobs running on time
✅ AnythingLLM skills working with new endpoints
✅ Vault watcher triggering embeddings
✅ External service sync functioning (if enabled)
✅ Import workflows processing correctly
✅ No n8n service in docker-compose
✅ No n8n workflow files in repository
✅ Documentation updated
✅ Performance metrics equal or better than n8n
✅ Zero data loss during migration

---

## Conclusion

This migration will:
1. **Simplify** the stack by removing n8n dependency
2. **Improve** performance with native Python execution
3. **Enhance** maintainability with single-language codebase
4. **Strengthen** security with centralized validation
5. **Enable** better testing and development workflows

The migration is comprehensive but achievable in 30-42 hours of focused development time. The modular approach allows for incremental migration and testing, reducing risk.
