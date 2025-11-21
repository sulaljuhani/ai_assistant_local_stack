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
- `my-frontend.xml` 🆕 Custom WebUI (alternative to AnythingLLM)
- `my-anythingllm.xml` (optional, can use frontend instead)

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
- **Frontend WebUI** 🆕: http://your-server:3001 (Custom React chat interface)
- **AnythingLLM** (optional): http://your-server:3001 (if using AnythingLLM instead)
- **LangGraph Agents API**: http://your-server:8000
  - Swagger docs: http://your-server:8000/docs
  - Scheduler status: http://your-server:8000/scheduler/jobs
- **System Monitor**: `./scripts/monitor-system.sh`

## 🤖 Intelligent Agent System

AI Stack features a **LangGraph multi-agent architecture** with specialized domain experts and complete automation:

### **LangGraph Multi-Agent System** (✅ Complete - Production Ready)

Advanced multi-agent orchestration with specialized domain experts, REST API, and background automation:

**Core Architecture:**
- 🤖 **4 Specialized Agents** - Food, Task, Event, Memory experts
- 🌐 **21 REST API Endpoints** - Complete automation layer
- ⏰ **10 Scheduled Jobs** - Background processing with APScheduler
- 🔧 **30+ Tools** - Database operations, vector search, hybrid recommendations
- 🔒 **Type-Safe** - Pydantic validation on all inputs
- 📊 **Production Ready** - Tested, secure, fully documented

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

**Tools:** 7 specialized tools (DB queries + vector search + hybrid recommendations)

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

**Tools:** 7 task-specific tools (CRUD operations + pattern analysis)

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

**Tools:** 6 calendar tools (event management + conflict detection)

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

**Tools:** 5 memory tools (OpenMemory + Qdrant + note management)

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
├── frontend/                  # 🆕 Custom WebUI (React + TypeScript)
│   ├── src/                   # Source code (components, API, contexts)
│   ├── Dockerfile             # Production build
│   ├── nginx.conf             # Nginx SPA configuration
│   └── README.md              # Frontend documentation
├── containers/
│   ├── langgraph-agents/     # LangGraph multi-agent system (FastAPI + APScheduler)
│   │   ├── routers/          # REST API endpoints (tasks, reminders, events, vault, memory, imports)
│   │   ├── services/         # Background services (scheduler, reminders, external sync, memory)
│   │   ├── tools/            # Agent tools (database, vector, hybrid, documents, memory)
│   │   ├── middleware/       # Validation with Pydantic models
│   │   └── graph/            # LangGraph workflow and agents
│   └── mcp-server/           # MCP server source
├── anythingllm-skills/        # Custom AnythingLLM skills (updated to call Python API)
├── scripts/
│   ├── qdrant/               # Qdrant init & verification
│   ├── vault-watcher/        # File watcher (Bash + PS, calls Python API)
│   ├── python/               # Import/export tools
│   ├── setup-vault.sh        # Obsidian vault setup
│   └── monitor-system.sh     # System dashboard
├── archive/
│   └── n8n-workflows/        # Archived n8n workflows (migrated to Python)
├── config/                    # Configuration templates
├── docker-compose.yml         # Full stack deployment
└── docs/                      # Additional documentation
    ├── CUSTOM_WEBUI_PLAN.md   # Frontend implementation plan
    └── N8N_TO_PYTHON_MIGRATION_PLAN.md  # Complete migration documentation
```

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

> **📋 [Complete Documentation Index](docs/INDEX.md)** - Navigate all documentation by topic

Each component has detailed documentation:

### **AI Agents & Migration**
- **LangGraph Agents**: `containers/langgraph-agents/README.md` - Multi-agent system overview
- **n8n to Python Migration**: `docs/N8N_TO_PYTHON_MIGRATION_PLAN.md` - Complete migration documentation
- **API Documentation**: Visit http://your-server:8080/docs for interactive Swagger docs
- **Original Plan**: `docs/LANGGRAPH_MULTI_AGENT_PLAN.md` - Initial implementation roadmap

### **Core Components**
- **unRAID Templates**: `unraid-templates/README.md`
- **Database**: `migrations/README.md`
- **MCP Server**: `containers/mcp-server/README.md`
- **Qdrant**: `scripts/qdrant/README.md`
- **Vault Watcher**: `scripts/vault-watcher/README.md`
- **Architecture**: `docs/review/COMPLETE_STRUCTURE.md`

### **Reports & Analysis**
- **Production Readiness**: `docs/reports/PRODUCTION_READINESS_REPORT.md` - Security audit and deployment checklist
- **Code Review**: `docs/reports/CODE_REVIEW_REPORT.md` - Comprehensive codebase analysis
- **Duplication Analysis**: `docs/reports/DUPLICATION_ANALYSIS.md` - Code quality assessment

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
- Search semantically in AnythingLLM
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
- [AnythingLLM](https://anythingllm.com/) - RAG chat interface
- [Obsidian](https://obsidian.md/) - Note-taking app

---

**A complete, privacy-first AI assistant stack for personal use on unRAID.** 🔒✨

> **Note:** This is a personal project designed for single-user deployment. While the architecture is production-ready, it's optimized for individual use cases rather than multi-user scenarios.
