# 🧠 AI Stack - Complete Local AI Assistant with OpenMemory

A comprehensive, 100% local AI assistant stack with long-term memory powered by [OpenMemory](https://github.com/CaviraOSS/OpenMemory), running entirely on your own hardware. No cloud dependencies, complete privacy, unified memory across all AI conversations.

> **Personal Use Project:** Designed for single-user deployment on unRAID servers. All components run locally with no external dependencies.
>
> ✅ **Production Ready** - Fully security audited, tested, and ready for deployment. See `docs/reports/PRODUCTION_READINESS_REPORT.md` for details.
>
> 🚀 **Major Update:** Migrated from n8n workflows to native Python FastAPI with APScheduler. All 21 workflows now implemented as REST endpoints and scheduled jobs.

## 🎯 What is This?

AI Stack combines multiple open-source tools into a unified system that:

- **Remembers everything** - Import ChatGPT, Claude, Gemini conversations into unified memory
- **Searches semantically** - Vector search across all your documents, notes, and conversations
- **Runs 100% locally** - No data leaves your machine, complete privacy
- **Integrates with Obsidian** - Auto-embed your notes for AI-powered search
- **Manages your life** - Tasks, reminders, events, all AI-accessible
- **Intelligent Agents** - Specialized AI agents with conversational interfaces for food, tasks, and planning

## ✨ What's Been Built

This repository contains a **complete, production-ready** AI Stack with:

✅ **8 Core unRAID Container Templates** - Deploy with one click
✅ **Custom WebUI** 🆕 - Modern React chat interface with dark mode, toast notifications, mobile support
✅ **LangGraph Multi-Agent System** - FastAPI service with specialized agents and 30+ tools
✅ **Python Automation Layer** - 21 REST endpoints + 10 scheduled jobs (migrated from n8n)
✅ **OpenMemory Integration** - Official long-term memory system with MCP support
✅ **Database Schema** - Personal data management (tasks, reminders, events, notes, food log)
✅ **MCP Server** - 12 database tools for AI access
✅ **Qdrant Collections** - 768-dim vector storage for documents
✅ **Vault File Watcher** - Auto-embed Obsidian notes
✅ **Chat History Importers** - Import from ChatGPT, Claude, Gemini
✅ **System Monitor** - Real-time health dashboard
✅ **Complete Documentation** - READMEs for every component
✅ **Production Ready** - Security audited, validated, and tested

## 🚀 Quick Start

### 1. Create Docker Network
```bash
docker network create ai-stack-network
```

### 2. Install Containers (unRAID)
Use templates in `unraid-templates/`:
- `my-postgres.xml`
- `my-qdrant.xml`
- `my-redis.xml`
- `my-ollama.xml`
- `my-openmemory.xml` ⭐ Official OpenMemory integration
- `my-mcp-server.xml`
- `my-langgraph-agents.xml` ⭐ Multi-agent system with automation
- `my-frontend.xml` (archived, not in use; see `archive/frontend`)
- `my-anythingllm.xml` (archived, not in use; AnythingLLM folders moved to `archive/`)

### 3. Initialize Database
```bash
cd migrations
./run-migrations.sh
```

### 4. Setup Qdrant
```bash
cd scripts/qdrant
./init-collections.sh
```

### 5. Pull Ollama Models
```bash
docker exec ollama-ai-stack ollama pull llama3.2:3b
docker exec ollama-ai-stack ollama pull nomic-embed-text
```

### 6. Setup Vault
```bash
./scripts/setup-vault.sh
```

### 7. Access Services
- **Frontend WebUI**: archived (see `archive/frontend`, not running currently)
- **AnythingLLM**: archived (see `archive/anythingllm-*`, not running currently)
- **LangGraph Agents API**: http://your-server:8000
  - Swagger docs: http://your-server:8000/docs
  - Scheduler status: http://your-server:8000/scheduler/jobs
- **System Monitor**: `./scripts/monitor-system.sh`

### OpenWebUI Integration
- OpenWebUI lives at `http://192.168.0.12:8084/` (Workspace → Functions).
- **Recommended:** use the pipe function in `openwebui/langgraph_pipe_FIXED.py` (single-user, model name "Sebastian"). In OpenWebUI create a Pipe Function, paste the file, set valves `LANGGRAPH_CHAT_URL=http://langgraph-agents:8000/chat`, `LANGGRAPH_WORKSPACE=default`, `LANGGRAPH_USER_ID=00000000-0000-0000-0000-000000000001`, add `LANGGRAPH_API_KEY` if you lock the API, and enable it so chat_id becomes the LangGraph session_id for continuity.
- **Adapter (currently running):** `openwebui-adapter` service in `docker-compose.yml` bridges OpenWebUI’s OpenAI client to LangGraph at `http://langgraph-agents:8000/chat`. Host port `${OPENWEBUI_ADAPTER_PORT:-8090}` maps to container `8080` on `ai-stack-network`.
- Adapter auth: `OPENWEBUI_ADAPTER_API_KEY` (defaults to `change_me` unless overridden). A local override exists at `openwebui/adapter/.env` with `OPENWEBUI_ADAPTER_API_KEY=9f02cb1950dc88965cf96358049a2b8551a4cc6a6c56ba19ecd54a8d2579ad0f` and `PORT=8090` for direct testing.
- Quick test against the adapter:
  ```bash
  curl -X POST http://localhost:8090/v1/chat/completions \
    -H "Authorization: Bearer <adapter_key>" \
    -H "Content-Type: application/json" \
    -d '{"model":"langgraph","messages":[{"role":"user","content":"Hello"}]}'
  ```

## 🤖 Intelligent Agent System

AI Stack features a **LangGraph multi-agent architecture** with specialized domain experts and complete automation:

### **LangGraph Multi-Agent System** (✅ Complete - Production Ready)

Advanced multi-agent orchestration with specialized domain experts, REST API, and background automation:

**Core Architecture:**
- 🤖 **4 Specialized Agents** - Food, Task, Event, Reminder experts
- 🌐 **21 REST API Endpoints** - Complete automation layer
- ⏰ **10 Scheduled Jobs** - Background processing with APScheduler
- 🔧 **30+ Tools** - Database operations, vector search, hybrid recommendations
- 🔒 **Type-Safe** - Pydantic validation on all inputs
- 📊 **Production Ready** - Tested, secure, fully documented

**Agent Flow Architecture:**

```
                    USER MESSAGE
                         ↓
                    ┌─────────┐
                    │  START  │
                    └─────────┘
                         ↓
         ┌───────────────────────────────┐
         │   ROUTING NODE (Hybrid)       │
         │  1. Keyword matching (fast)   │
         │  2. LLM routing (fallback)    │
         │  3. State pruning (20 msg)    │
         └───────────────────────────────┘
                         │
      ┌──────────────────┼──────────────────┐
      ↓                  ↓                  ↓
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  Food    │      │  Task    │      │  Event   │      │ Reminder │
│  Agent   │      │  Agent   │      │  Agent   │      │  Agent   │
│ (7 tools)│      │(23 tools)│      │(20 tools)│      │ (tools)  │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
      │                  │                  │                  │
      └──────────────────┴──────────────────┴──────────────────┘
                         ↓
              ┌────────────────────┐
              │ SHOULD_CONTINUE?   │
              │ • Handoff needed?  │
              │ • Domain shift?    │
              └────────────────────┘
                    │         │
          "route"   │         │  "end"
               ┌────┘         └────┐
               ↓                   ↓
         ROUTING NODE            END
         (loop back)        (response sent)
```

> 📊 **[Full Agent Flow Documentation](docs/LANGGRAPH_FLOW_DIAGRAM.md)** - Detailed architecture, routing strategies, state management, and performance characteristics

**REST API Endpoints:**
- `/api/tasks/*` - Task management (create, list, update, delete)
- `/api/reminders/*` - Reminder system (create, list, today)
- `/api/events/*` - Calendar events (create, list, today, week)
- `/api/vault/*` - Document embedding (reembed, sync, status)
- `/api/documents/*` - File uploads and search
- `/api/memory/*` - OpenMemory integration (store, search, stats)
- `/api/import/*` - Chat history imports (ChatGPT, Claude, Gemini)

**Scheduled Jobs:**
- Fire reminders (every 5 min)
- Daily summary (8 AM)
- Expand recurring tasks (midnight)
- Cleanup old data (Sunday 2 AM)
- Health check (every 5 min)
- Vault sync (every 12 hours)
- Enrich memories (3 AM)
- Memory vault export (every 6 hours)
- Todoist sync (every 15 min, conditional)
- Google Calendar sync (every 15 min, conditional)

---

#### **Food Agent** 🍽️
**Expertise:** Food logging, meal suggestions, dietary patterns

**Capabilities:**
- Log meals with full details (rating, location, ingredients, tags)
- Suggest meals based on history, ratings, and recency
- Analyze eating patterns and preferences
- Handle dietary restrictions and preferences
- Generate shopping lists from food history
- Semantic search: "Find something similar to Thai curry but not spicy"

**Tools:** `search_food_log`, `log_food_entry`, `update_food_entry`, `get_food_by_rating`, `analyze_food_patterns`, `vector_search_foods`, `get_food_recommendations`

---

#### **Task Agent** ✅
**Expertise:** Task management, planning, productivity

**Capabilities:**
- Create tasks with intelligent defaults
- Update and organize tasks
- Prioritize based on deadlines and importance
- Break down complex projects into subtasks
- Daily and weekly planning assistance
- Analyze productivity patterns

**Tools:** `search_tasks`, `create_task`, `update_task`, `get_tasks_by_priority`, `get_tasks_due_soon`, `add_task_dependency`, `get_task_dependencies`, `get_available_tasks`, `complete_task_with_unblock`, `add_checklist_item`, `check_checklist_item`, `get_task_with_checklist`, `get_tasks_with_incomplete_checklists`, `bulk_create_tasks`, `bulk_update_task_status`, `bulk_add_tags`, `bulk_set_priority`, `bulk_delete_tasks`, `bulk_move_to_project`, `unified_search`, `search_by_tags`, `advanced_task_filter`, `get_task_statistics`

---

#### **Event Agent** 📅
**Expertise:** Calendar management, scheduling, time blocking

**Capabilities:**
- Create calendar events
- Check for scheduling conflicts
- Suggest optimal meeting times
- Time block planning
- Coordinate reminders with events
- Balance work and personal time

**Tools:** `search_events`, `create_event`, `get_events_today`, `get_events_week`, `check_time_conflicts`, `unified_search`, `bulk_create_events`, `bulk_update_event_status`, `bulk_reschedule_events`, `bulk_add_attendees`, `bulk_delete_events`, `create_recurring_event`, `update_recurring_series`, `skip_recurring_instance`, `delete_recurring_series`, `get_recurring_series`, `search_by_attendees`, `search_by_location`, `advanced_event_filter`, `get_event_statistics`, `find_available_slots`, `suggest_meeting_times`, `bulk_check_conflicts`, `get_busy_free_times`

---

#### **Memory Agent** 📝 (Optional)
**Expertise:** Note-taking, knowledge organization, memory search

**Capabilities:**
- Store and organize notes
- Semantic search across memories
- Connect related concepts
- Retrieve relevant context
- Integrate with Obsidian vault
- Knowledge graph connections

**Tools (available if enabled):** `store_chat_turn`, `search_memories`, `vector_search_memories`, `embed_document`, `reembed_vault_file`, `search_embedded_documents`

---

### Planned Agents (to be implemented)

- **Note-Taking Agent** 🗒️ — Write, edit, and recall notes on demand; will orchestrate document embeddings and memory storage.
- **System Monitoring Agent** 🛡️ — Monitor AI Stack health (containers, DB/Qdrant/Ollama), surface issues proactively to the user.
- **unRAID Monitoring Agent** 🖥️ — Track unRAID host metrics and array health, alert on disk/network/container problems.
- **Home Assistant Monitoring Agent** 🏠 — Watch Home Assistant entities/automations and notify on sensor or automation anomalies.
- **Automatic Task Agent** ⏱️ — Coordinate with other agents to run pre-specified tasks on schedules or dates (e.g., generate daily summaries of database contents and save them to markdown files in a designated folder).

---

### **Agent Communication**

**State-Aware Handoffs:**
```
You: "Suggest something to eat"
Food Agent: "Thai curry? You loved it last time"

You: "Not Thai, something else I haven't had"
Food Agent: [Continues conversation with context]

You: "Create a task to buy groceries"
Food Agent: [Hands off to Task Agent with context]
Task Agent: "I see you were discussing food. Groceries for salmon?"
```

**Shared Knowledge:** All agents access the same databases and can collaborate when needed

**See:** `docs/N8N_TO_PYTHON_MIGRATION_PLAN.md` for full migration details

---

## 📦 What's Included

| Component | Status | Description |
|-----------|--------|-------------|
| **unRAID Templates** | ✅ Complete | 8 XML templates for easy deployment |
| **Custom WebUI** | ✅ Complete | React + TypeScript chat interface, mobile-responsive, dark mode |
| **LangGraph Agents** | ✅ Complete | Multi-agent system with 4 specialists, 30+ tools |
| **REST API Layer** | ✅ Complete | 21 endpoints for complete automation |
| **APScheduler Jobs** | ✅ Complete | 10 background jobs for maintenance & sync |
| **OpenMemory** | ✅ Integrated | Official long-term memory system with MCP |
| **Database Schema** | ✅ Complete | PostgreSQL for personal data (9 migrations) |
| **MCP Server** | ✅ Complete | 12 database tools, async, 550+ lines |
| **Qdrant Setup** | ✅ Complete | Document embeddings + verification |
| **Vault Watcher** | ✅ Complete | Bash + PowerShell, calls Python API |
| **Chat Importers** | ✅ Complete | ChatGPT, Claude, Gemini imports |
| **System Monitor** | ✅ Complete | Real-time dashboard |
| **Documentation** | ✅ Complete | 20,000+ lines across all docs |

## 📁 Repository Structure

```
ai_assistant_local_stack/
├── unraid-templates/          # 8 container templates
├── migrations/                # 9 SQL migrations
├── containers/
│   ├── langgraph-agents/     # LangGraph multi-agent system (FastAPI + APScheduler)
│   │   ├── routers/          # REST API endpoints (tasks, reminders, events, vault, memory, imports)
│   │   ├── services/         # Background services (scheduler, reminders, external sync, memory)
│   │   ├── tools/            # Agent tools (database, vector, hybrid, documents, memory)
│   │   ├── middleware/       # Validation with Pydantic models
│   │   └── graph/            # LangGraph workflow and agents
│   └── mcp-server/           # MCP server source
├── scripts/
│   ├── qdrant/               # Qdrant init & verification
│   ├── vault-watcher/        # File watcher (Bash + PS, calls Python API)
│   ├── python/               # Import/export tools
│   ├── setup-vault.sh        # Obsidian vault setup
│   └── monitor-system.sh     # System dashboard
├── archive/
│   ├── n8n-workflows/                        # Archived n8n workflows (migrated to Python)
│   ├── frontend/                             # Archived custom React WebUI (not in use)
│   ├── anythingllm-skills/                   # Archived AnythingLLM skills
│   └── anythingllm-skills-backup-20251121-153533/  # Archived backup
├── config/                    # Configuration templates
├── docker-compose.yml         # Full stack deployment
└── docs/                      # Additional documentation
    ├── CUSTOM_WEBUI_PLAN.md   # Frontend implementation plan
    └── N8N_TO_PYTHON_MIGRATION_PLAN.md  # Complete migration documentation
```

## 🗄️ Database Schema

The AI Stack uses PostgreSQL with 17 tables for managing personal data, memories, and system operations:

### Core User Data Tables

#### **tasks**
Task management with recurring support and external sync capabilities.
- `id` (UUID, PK) - Unique task identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `category_id` (UUID) - Optional category
- `title` (TEXT, NOT NULL) - Task title
- `description` (TEXT) - Detailed description
- `notes` (TEXT) - Additional notes
- `status` (TEXT, default: 'todo') - Current status
- `completed_at` (TIMESTAMPTZ) - Completion timestamp
- `due_date` (TIMESTAMPTZ) - Due date
- `start_date` (TIMESTAMPTZ) - Start date
- `duration_minutes` (INTEGER) - Estimated duration
- `priority` (INTEGER, default: 0) - Priority level
- `is_recurring` (BOOLEAN, default: false) - Recurring flag
- `recurrence_rule` (TEXT) - Recurrence pattern
- `recurrence_parent_id` (UUID) - Parent task for recurring instances
- `todoist_id` (TEXT) - Todoist integration ID
- `todoist_project_id` (TEXT) - Todoist project reference
- `todoist_section_id` (TEXT) - Todoist section reference
- `todoist_parent_id` (TEXT) - Todoist parent task
- `todoist_order` (INTEGER) - Todoist display order
- `todoist_sync_at` (TIMESTAMPTZ) - Last Todoist sync
- `depends_on` (UUID[]) - Task dependencies
- `blocks` (UUID[]) - Tasks blocked by this task
- `estimated_effort` (TEXT) - Effort estimate
- `actual_effort` (TEXT) - Actual time spent
- `energy_level` (TEXT) - Required energy level
- `context` (TEXT) - Task context
- `project` (TEXT) - Project association
- `tags` (TEXT[]) - Task tags
- `checklist` (JSONB) - Checklist items
- `metadata` (JSONB) - Additional metadata
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **reminders**
Reminder system with recurring support and multiple notification channels.
- `id` (UUID, PK) - Unique reminder identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `category_id` (UUID) - Optional category
- `title` (TEXT, NOT NULL) - Reminder title
- `description` (TEXT) - Detailed description
- `remind_at` (TIMESTAMPTZ, NOT NULL) - Reminder time
- `timezone` (TEXT, default: 'UTC') - Timezone
- `is_recurring` (BOOLEAN, default: false) - Recurring flag
- `recurrence_rule` (TEXT) - Recurrence pattern
- `recurrence_end_date` (TIMESTAMPTZ) - End date for recurrence
- `status` (TEXT, default: 'pending') - Current status
- `fired_at` (TIMESTAMPTZ) - When reminder was triggered
- `completed_at` (TIMESTAMPTZ) - Completion timestamp
- `snoozed_until` (TIMESTAMPTZ) - Snooze time
- `notification_sent` (BOOLEAN, default: false) - Notification flag
- `notification_channels` (TEXT[], default: ['system']) - Notification methods
- `notification_sound` (TEXT, default: 'default') - Sound preference
- `priority` (INTEGER, default: 0) - Priority level
- `tags` (TEXT[]) - Reminder tags
- `metadata` (JSONB) - Additional metadata
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps
- `is_completed` (BOOLEAN, default: false) - Completion flag

#### **events**
Calendar events with Google Calendar sync support.
- `id` (UUID, PK) - Unique event identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `category_id` (UUID) - Optional category
- `title` (TEXT, NOT NULL) - Event title
- `description` (TEXT) - Detailed description
- `location` (TEXT) - Event location
- `url` (TEXT) - Related URL
- `start_time` (TIMESTAMPTZ, NOT NULL) - Start time
- `end_time` (TIMESTAMPTZ, NOT NULL) - End time
- `timezone` (TEXT, default: 'UTC') - Timezone
- `is_all_day` (BOOLEAN, default: false) - All-day event flag
- `is_recurring` (BOOLEAN, default: false) - Recurring flag
- `recurrence_rule` (TEXT) - Recurrence pattern
- `recurrence_end_date` (TIMESTAMPTZ) - End date for recurrence
- `recurrence_parent_id` (UUID) - Parent event for recurring instances
- `google_calendar_id` (TEXT) - Google Calendar ID
- `google_event_id` (TEXT) - Google Event ID
- `google_sync_at` (TIMESTAMPTZ) - Last Google sync
- `google_sync_token` (TEXT) - Google sync token
- `attendees` (JSONB) - Event attendees
- `organizer` (TEXT) - Event organizer
- `reminders` (INTEGER[], default: [15]) - Reminder minutes before event
- `status` (TEXT, default: 'confirmed') - Event status
- `tags` (TEXT[]) - Event tags
- `metadata` (JSONB) - Additional metadata
- `conference_link` (TEXT) - Video conference link
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **food_log**
Food consumption tracking with preference ratings.
- `id` (UUID, PK) - Unique food log identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `food_name` (TEXT, NOT NULL) - Food/meal name
- `location` (TEXT, NOT NULL) - Where consumed
- `preference` (TEXT, NOT NULL) - Rating/preference
- `restaurant_name` (TEXT) - Restaurant name if applicable
- `description` (TEXT) - Detailed description
- `consumed_at` (TIMESTAMPTZ, default: NOW) - Consumption time
- `meal_type` (TEXT) - Breakfast, lunch, dinner, etc.
- `ingredients` (TEXT[]) - Ingredient list
- `tags` (TEXT[]) - Food tags
- `calories` (INTEGER) - Calorie count
- `notes` (TEXT) - Additional notes
- `embedding_generated` (BOOLEAN, default: false) - Vector embedding flag
- `last_recommended_at` (TIMESTAMPTZ) - Last recommendation time
- `merged_from_ids` (UUID[]) - Source IDs if merged
- `is_merged` (BOOLEAN, default: false) - Merge flag
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

### Knowledge Management Tables

#### **notes**
Obsidian vault integration with frontmatter and linking support.
- `id` (UUID, PK) - Unique note identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `category_id` (UUID) - Optional category
- `title` (TEXT, NOT NULL) - Note title
- `content` (TEXT, NOT NULL) - Note content
- `content_type` (TEXT, default: 'markdown') - Content format
- `file_path` (TEXT) - Vault file path
- `file_hash` (TEXT) - File hash for change detection
- `file_size` (INTEGER) - File size in bytes
- `folder` (TEXT) - Vault folder
- `tags` (TEXT[]) - Note tags
- `aliases` (TEXT[]) - Note aliases
- `frontmatter` (JSONB) - YAML frontmatter
- `links_to` (TEXT[]) - Outgoing links
- `backlinks` (TEXT[]) - Incoming links
- `is_embedded` (BOOLEAN, default: false) - Embedding status
- `embedded_at` (TIMESTAMPTZ) - Last embedding time
- `embedding_model` (TEXT, default: 'nomic-embed-text') - Model used
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps
- `file_modified_at` (TIMESTAMPTZ) - Last file modification

#### **documents**
Document management with embedding support.
- `id` (UUID, PK) - Unique document identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `category_id` (UUID) - Optional category
- `filename` (TEXT, NOT NULL) - Original filename
- `file_path` (TEXT, NOT NULL) - Storage path
- `file_hash` (TEXT, NOT NULL) - File hash
- `file_size` (INTEGER) - File size in bytes
- `mime_type` (TEXT) - MIME type
- `title` (TEXT) - Document title
- `extracted_text` (TEXT) - Extracted text content
- `page_count` (INTEGER) - Number of pages
- `status` (TEXT, default: 'pending') - Processing status
- `processed_at` (TIMESTAMPTZ) - Processing timestamp
- `error_message` (TEXT) - Processing errors
- `is_embedded` (BOOLEAN, default: false) - Embedding status
- `embedded_at` (TIMESTAMPTZ) - Last embedding time
- `embedding_model` (TEXT, default: 'nomic-embed-text') - Model used
- `tags` (TEXT[]) - Document tags
- `metadata` (JSONB) - Additional metadata
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **document_chunks**
Document chunk storage for vector search.
- `id` (UUID, PK) - Unique chunk identifier
- `document_id` (UUID, NOT NULL) - Parent document reference
- `note_id` (UUID) - Parent note reference (if from note)
- `chunk_index` (INTEGER, NOT NULL) - Chunk sequence number
- `chunk_text` (TEXT, NOT NULL) - Chunk content
- `chunk_size` (INTEGER) - Chunk size in characters
- `page_number` (INTEGER) - Source page number
- `section_title` (TEXT) - Section heading
- `preceding_context` (TEXT) - Context before chunk
- `following_context` (TEXT) - Context after chunk
- `qdrant_point_id` (TEXT) - Qdrant vector ID
- `embedding_model` (TEXT, default: 'nomic-embed-text') - Model used
- `created_at` (TIMESTAMPTZ) - Creation timestamp

### Memory System Tables

#### **memories**
Long-term memory storage with OpenMemory integration.
- `id` (SERIAL, PK) - Unique memory identifier
- `conversation_id` (UUID) - Source conversation
- `user_id` (UUID, NOT NULL) - Owner reference
- `role` (TEXT, NOT NULL) - Message role (user/assistant/system)
- `content` (TEXT, NOT NULL) - Memory content
- `summary` (TEXT) - Memory summary
- `salience_score` (FLOAT, default: 0.5) - Importance score
- `source` (TEXT, default: 'chat') - Memory source
- `access_count` (INTEGER, default: 0) - Access frequency
- `metadata` (JSONB, default: {}) - Additional metadata
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps
- `last_accessed_at` (TIMESTAMPTZ) - Last access time

#### **memory_sectors**
Multi-dimensional memory classification.
- `id` (SERIAL, PK) - Unique sector identifier
- `memory_id` (INTEGER, NOT NULL) - Memory reference
- `sector` (TEXT, NOT NULL) - Sector type (semantic/episodic/procedural/emotional/reflective)
- `weight` (FLOAT, default: 1.0) - Sector relevance weight
- `created_at` (TIMESTAMPTZ) - Creation timestamp

#### **memory_links**
Memory relationship graph.
- `id` (SERIAL, PK) - Unique link identifier
- `source_memory_id` (INTEGER, NOT NULL) - Source memory
- `target_memory_id` (INTEGER, NOT NULL) - Target memory
- `link_type` (TEXT, NOT NULL) - Relationship type
- `strength` (FLOAT, default: 0.5) - Link strength
- `metadata` (JSONB, default: {}) - Additional metadata
- `created_at` (TIMESTAMPTZ) - Creation timestamp

#### **conversations**
Conversation tracking for memory context.
- `id` (UUID, PK) - Unique conversation identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `title` (TEXT, default: 'Untitled Conversation') - Conversation title
- `source` (TEXT, default: 'chat') - Source platform
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **imported_chats**
Chat import tracking (ChatGPT, Claude, Gemini).
- `id` (SERIAL, PK) - Unique import identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `source` (TEXT, NOT NULL) - Import source platform
- `file_hash` (TEXT, NOT NULL) - Import file hash
- `filename` (TEXT) - Original filename
- `conversations_count` (INTEGER, default: 0) - Number of conversations imported
- `messages_count` (INTEGER, default: 0) - Number of messages imported
- `import_status` (TEXT, default: 'pending') - Import status
- `error_message` (TEXT) - Import errors
- `metadata` (JSONB, default: {}) - Additional metadata
- `imported_at` (TIMESTAMPTZ) - Import timestamp

### System Tables

#### **categories**
Categorization for tasks, reminders, events, documents.
- `id` (UUID, PK) - Unique category identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `name` (TEXT, NOT NULL) - Category name
- `color` (TEXT, default: '#3B82F6') - Display color
- `icon` (TEXT, default: '📁') - Display icon
- `type` (TEXT, default: 'general') - Category type
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **file_sync**
File synchronization tracking for vault watcher.
- `id` (UUID, PK) - Unique sync record identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `file_path` (TEXT, NOT NULL) - File path
- `file_type` (TEXT, NOT NULL) - File type
- `file_hash` (TEXT, NOT NULL) - File hash
- `last_synced_at` (TIMESTAMPTZ, default: NOW) - Last sync time
- `sync_status` (TEXT, default: 'synced') - Sync status
- `error_message` (TEXT) - Sync errors
- `note_id` (UUID) - Related note ID
- `document_id` (UUID) - Related document ID

#### **health_checks**
System health monitoring records.
- `id` (UUID, PK) - Unique health check identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `check_time` (TIMESTAMPTZ, default: NOW) - Check timestamp
- `total_services` (INTEGER, NOT NULL) - Total services checked
- `healthy_count` (INTEGER, NOT NULL) - Healthy services
- `down_count` (INTEGER, NOT NULL) - Down services
- `all_healthy` (BOOLEAN, NOT NULL) - Overall health status
- `details` (JSONB, NOT NULL) - Detailed health data
- `created_at` (TIMESTAMPTZ) - Creation timestamp

#### **backup_log**
Backup operation tracking.
- `id` (UUID, PK) - Unique backup identifier
- `user_id` (UUID, NOT NULL) - Owner reference
- `backup_type` (VARCHAR(50), NOT NULL) - Backup type
- `backup_date` (TIMESTAMPTZ, default: NOW) - Backup timestamp
- `status` (VARCHAR(20), NOT NULL) - Backup status
- `backup_path` (TEXT, NOT NULL) - Backup file path
- `file_size_mb` (NUMERIC) - Backup size in MB
- `duration_seconds` (INTEGER) - Backup duration
- `notes` (TEXT) - Additional notes
- `error_message` (TEXT) - Backup errors
- `created_at`, `updated_at` (TIMESTAMPTZ) - Timestamps

#### **users**
User management (single-user system).
- `id` (UUID, PK) - User identifier (hardcoded: `00000000-0000-0000-0000-000000000001`)
- Additional columns available but not actively used in single-user context

### View: **food_recommendations**
Virtual view for food recommendation queries.
- `id` (UUID) - Food log ID
- `food_name` (TEXT) - Food/meal name
- `description` (TEXT) - Description
- `preference` (TEXT) - Rating
- `consumed_at` (TIMESTAMPTZ) - Last consumption
- `days_since_eaten` (INTEGER) - Days since last eaten
- `location` (TEXT) - Location
- `restaurant_name` (TEXT) - Restaurant
- `ingredients` (TEXT[]) - Ingredients
- `tags` (TEXT[]) - Tags

**Total:** 17 tables + 1 view | 350+ columns | 50+ indexes | 20+ functions

## 🔧 Key Technologies

- **AI Agents**: LangGraph + LangChain for multi-agent orchestration
- **API Framework**: FastAPI with async support
- **Scheduler**: APScheduler for background jobs
- **Validation**: Pydantic for type-safe data models
- **Embedding Model**: nomic-embed-text (768 dimensions)
- **LLM**: Ollama llama3.2:3b (2GB, fast, local)
- **Vector DB**: Qdrant (cosine similarity)
- **Database**: PostgreSQL 16 with asyncpg
- **State Management**: Redis for conversation persistence
- **Protocol**: MCP (Model Context Protocol)

## 📖 Documentation

### **📋 Quick Navigation**

| Category | Document | Description |
|----------|----------|-------------|
| **🚀 Getting Started** | [README.md](README.md) | Project overview and quick start |
| | [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Step-by-step deployment instructions |
| | [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| **🤖 AI Agents** | [LangGraph Flow Diagram](docs/LANGGRAPH_FLOW_DIAGRAM.md) | Visual agent architecture and routing |
| | [LangGraph Multi-Agent Plan](docs/LANGGRAPH_MULTI_AGENT_PLAN.md) | Multi-agent system design |
| | [LangGraph Architecture](containers/langgraph-agents/ARCHITECTURE.md) | Technical implementation details |
| | [Prompt Guide](containers/langgraph-agents/PROMPT_GUIDE.md) | Agent prompt management |
| | [N8N to Python Migration](docs/N8N_TO_PYTHON_MIGRATION_PLAN.md) | Migration documentation |
| **🔌 API & Integration** | [API Documentation](docs/API_DOCUMENTATION.md) | REST API reference |
| | | Swagger: http://localhost:8080/docs |
| | [OpenWebUI Integration](openwebui/README.md) | OpenWebUI setup guide |
| | [OpenWebUI Quick Start](openwebui/QUICK_START.md) | Fast setup instructions |
| | [OpenWebUI Adapter](openwebui/adapter/README.md) | Adapter service details |
| | [Integration FAQ](docs/INTEGRATION_FAQ.md) | Common integration questions |
| **🗄️ Data & Storage** | [Database Migrations](migrations/README.md) | PostgreSQL schema and migrations |
| | [Qdrant Setup](scripts/qdrant/README.md) | Vector database initialization |
| | [MCP Server](containers/mcp-server/README.md) | Database tools via MCP |
| | [Vault Watcher](scripts/vault-watcher/README.md) | Obsidian file monitoring |
| **🏗️ Architecture** | [Container Architecture](unraid-templates/CONTAINER_ARCHITECTURE.md) | System architecture overview |
| | [Complete Structure](docs/review/COMPLETE_STRUCTURE.md) | Full system architecture |
| | [unRAID Templates](unraid-templates/README.md) | Container deployment templates |
| **📊 Reports & Analysis** | [Production Readiness](docs/reports/PRODUCTION_READINESS_REPORT.md) | Security audit and deployment status |
| | [Code Review Report](docs/reports/CODE_REVIEW_REPORT.md) | Comprehensive codebase analysis |
| | [Security Audit](docs/review/SECURITY_AUDIT_FINDINGS.md) | Security findings and fixes |
| | [Duplication Analysis](docs/reports/DUPLICATION_ANALYSIS.md) | Code quality assessment |
| **🔧 Development** | [OpenMemory Comparison](docs/OPENMEMORY_COMPARISON.md) | Memory system analysis |
| | [Testing Guide](tests/README.md) | Test scripts and usage |
| | [Code Review Summary](docs/review/CODE_REVIEW_SUMMARY.md) | Review findings summary |
| | [Q&A](docs/review/ANSWERS_TO_YOUR_QUESTIONS.md) | Technical questions answered |

### **📂 Archived Documentation**
Historical documentation moved to `docs/archive/`:
- Phase implementation plans (PHASE_1-4)
- Gaps analysis documents
- Food feature documentation
- Pydantic AI implementation docs
- n8n security guides
- Custom WebUI plans
- Pre-deployment checklists

LangGraph implementation summaries in `containers/langgraph-agents/archive/`:
- Tool integration summaries
- Event tools implementation plans
- Refactoring documentation

> **💡 Tip:** Start with [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for setup, [LANGGRAPH_FLOW_DIAGRAM.md](docs/LANGGRAPH_FLOW_DIAGRAM.md) to understand agents, and [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) when you need help.

## 🎯 Use Cases

### 1. Unified AI Memory
Import conversations from multiple platforms via REST API:
- ChatGPT: `POST /api/import/chatgpt` with export file
- Claude: `POST /api/import/claude` with export file
- Gemini: `POST /api/import/gemini` with export file

All memories automatically classified into sectors (semantic, episodic, procedural, emotional, reflective) and searchable across platforms!

### 2. Obsidian Integration
- Edit notes in Obsidian
- Auto-embedded on save
- Search semantically via OpenMemory/OpenWebUI (AnythingLLM archived)
- Ask: "What did I write about Docker?"

### 3. Intelligent Personal Assistant
**Conversational AI that understands context:**
```
You: "Add a task"
Agent: "What task would you like to add?"

You: "Call dentist"
Agent: "When do you need to do this? Is it urgent?"

You: "Urgent, not sure when"
Agent: "Since it's urgent, I'd suggest:
       - Due: End of this week
       - Priority: High
       - Reminder: Tomorrow morning
       Sound good?"
```

**Features:**
- Smart task creation with validation
- Context-aware reminders
- Daily planning assistance
- Food logging with meal suggestions
- Calendar integration
- All accessible via conversational interface

## 🛠️ Development

Built with:
- Python 3.11 (MCP server, importers)
- Bash (Linux scripts)
- PowerShell (Windows scripts)
- SQL (PostgreSQL schema)
- Docker (containerization)

## 📊 Statistics

- **Total files**: 100+
- **Python code**: 35+ files, 12,000+ lines (including routers, services, middleware)
- **Bash scripts**: 10 files, 1,969 lines
- **SQL migrations**: 10 files, 1,232 lines
- **REST API endpoints**: 21 endpoints across 7 routers
- **Scheduled jobs**: 10 background jobs with APScheduler
- **Documentation**: 30+ files, 20,000+ lines
- **AI Agent tools**: 30+ tools (database, vector, hybrid, documents, memory)
- **LangGraph agents**: 4 specialized agents (Food, Task, Event, Memory)
- **MCP tools**: 12 database tools
- **Database tables**: 18+
- **Database indexes**: 50+
- **Database functions**: 20+
- **Vector dimensions**: 768
- **Containers**: 8 (7 core + 1 agent layer)
- **Security issues resolved**: 7 (all critical issues fixed)
- **n8n workflows migrated**: 21 → archived (now Python)

## 🔒 Privacy & Personal Use

**100% local. Zero cloud dependencies. Single-user design.**

- **Personal Project**: Built for single-user deployment on unRAID
- **Complete Privacy**: All data stays on your hardware
- **No Cloud**: No external API calls (unless you choose to add them)
- **No Telemetry**: Zero tracking or data collection
- **Full Control**: You own everything - data, models, infrastructure

## 📄 License

MIT License

## 🙏 Credits

Built with:
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Multi-agent orchestration
- [LangChain](https://www.langchain.com/) - Agent framework and tools
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Advanced Python Scheduler
- [Pydantic](https://docs.pydantic.dev/) - Data validation with type hints
- [OpenMemory](https://github.com/CaviraOSS/OpenMemory) - Long-term memory for AI agents
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Qdrant](https://qdrant.tech/) - Vector database
- [PostgreSQL](https://postgresql.org/) - Relational database
- [AnythingLLM](https://anythingllm.com/) - RAG chat interface (archived here, not currently used)
- [Obsidian](https://obsidian.md/) - Note-taking app

---

**A complete, privacy-first AI assistant stack for personal use on unRAID.** 🔒✨

> **Note:** This is a personal project designed for single-user deployment. While the architecture is production-ready, it's optimized for individual use cases rather than multi-user scenarios.
