# 🧠 AI Stack - Complete Local AI Assistant with OpenMemory

A comprehensive, 100% local AI assistant stack with long-term memory powered by [OpenMemory](https://github.com/CaviraOSS/OpenMemory), running entirely on your own hardware. No cloud dependencies, complete privacy, unified memory across all AI conversations.

> **Personal Use Project:** Designed for single-user deployment on unRAID servers. All components run locally with no external dependencies.

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

✅ **8 Core unRAID Container Templates** - Deploy with one click (+ optional Pydantic AI template for standalone install)
✅ **Intelligent Agent Layer** - Pydantic AI conversational middleware with specialized agents
✅ **OpenMemory Integration** - Official long-term memory system with MCP support
✅ **Database Schema** - Personal data management (tasks, reminders, events, notes, food log)
✅ **MCP Server** - 12 database tools for AI access
✅ **Qdrant Collections** - 768-dim vector storage for documents
✅ **Vault File Watcher** - Auto-embed Obsidian notes
✅ **ChatGPT Importer** - Import conversation history to OpenMemory
✅ **System Monitor** - Real-time health dashboard
✅ **Complete Documentation** - READMEs for every component  

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
- `my-n8n.xml`
- `my-anythingllm.xml`

**Optional - Install Separately:**
- `my-pydantic-agent.xml` ⭐ Intelligent agent layer (installed separately, see template for build instructions)

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
- **AnythingLLM**: http://your-server:3001
- **n8n**: http://your-server:5678
- **System Monitor**: `./scripts/monitor-system.sh`

## 🤖 Intelligent Agent System

AI Stack features a **multi-layer agent architecture** for intelligent, conversational task management:

### **Pydantic AI Agent Layer** (Current - Ready to Deploy)

Intelligent conversational middleware that sits between AnythingLLM and your tools:

- ✅ **Evaluates Every Request** - Understands intent, asks clarifying questions
- ✅ **Validates Before Execution** - Prevents errors, ensures data completeness
- ✅ **Smart Suggestions** - Offers intelligent defaults and recommendations
- ✅ **Conversation Memory** - Maintains context across multiple turns
- ✅ **Tool Orchestration** - Routes to n8n workflows or direct database operations

**Available Tools:**
- `create_task` - Task creation with validation and smart defaults
- `create_reminder` - Time-aware reminder creation
- `search_tasks` - Flexible task searching with filters
- `get_tasks_today` - Today's task overview
- `get_events_today` - Calendar integration
- `update_task` - Task modifications with context
- `log_food` - Food logging with meal suggestions

**See:** `docs/PYDANTIC_AI_AGENT_GUIDE.md` for deployment and usage

---

### **LangGraph Multi-Agent System** (Planned - Future Enhancement)

Advanced multi-agent orchestration with specialized domain experts:

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

**See:** `LANGGRAPH_MULTI_AGENT_PLAN.md` for full implementation roadmap

---

## 📦 What's Included

| Component | Status | Description |
|-----------|--------|-------------|
| **unRAID Templates** | ✅ Complete | 9 XML templates for easy deployment |
| **Pydantic AI Agent** | ✅ Complete | Intelligent conversational middleware, 650+ lines |
| **LangGraph Agents** | 📋 Planned | Multi-agent system with specialists (see plan) |
| **OpenMemory** | ✅ Integrated | Official long-term memory system with MCP |
| **Database Schema** | ✅ Complete | PostgreSQL for personal data (9 migrations) |
| **MCP Server** | ✅ Complete | 12 database tools, async, 550+ lines |
| **Qdrant Setup** | ✅ Complete | Document embeddings + verification |
| **Vault Watcher** | ✅ Complete | Bash + PowerShell, real-time |
| **ChatGPT Importer** | ✅ Complete | Import to OpenMemory |
| **System Monitor** | ✅ Complete | Real-time dashboard |
| **Documentation** | ✅ Complete | 4500+ lines across all READMEs |

## 📁 Repository Structure

```
ai_assistant_local_stack/
├── unraid-templates/          # 9 container templates
├── migrations/                # 9 SQL migrations
├── containers/
│   ├── mcp-server/           # MCP server source
│   └── pydantic-agent/       # Pydantic AI agent service
├── anythingllm-skills/        # Custom AnythingLLM skills
├── scripts/
│   ├── qdrant/               # Qdrant init & verification
│   ├── vault-watcher/        # File watcher (Bash + PS)
│   ├── python/               # Import/export tools
│   ├── setup-vault.sh        # Obsidian vault setup
│   └── monitor-system.sh     # System dashboard
├── config/                    # Configuration templates
└── docs/                      # Additional documentation
```

## 🔧 Key Technologies

- **AI Agents**: Pydantic AI 0.0.13 (current), LangGraph (planned)
- **Embedding Model**: nomic-embed-text (768 dimensions)
- **LLM**: Ollama llama3.2:3b (2GB, fast, local)
- **Vector DB**: Qdrant (cosine similarity)
- **Database**: PostgreSQL 16
- **Workflow Engine**: n8n (for complex multi-step operations)
- **Protocol**: MCP (Model Context Protocol)

## 📖 Documentation

Each component has detailed documentation:

### **AI Agents**
- **Pydantic AI Agent**: `docs/PYDANTIC_AI_AGENT_GUIDE.md` - Deployment and usage guide
- **Agent Service**: See `unraid-templates/my-pydantic-agent.xml` for standalone installation instructions
- **LangGraph Plan**: `LANGGRAPH_MULTI_AGENT_PLAN.md` - Multi-agent implementation roadmap
- **Implementation**: `PYDANTIC_AI_IMPLEMENTATION.md` - What was built and why

### **Core Components**
- **unRAID Templates**: `unraid-templates/README.md`
- **Database**: `migrations/README.md`
- **MCP Server**: `containers/mcp-server/README.md`
- **Qdrant**: `scripts/qdrant/README.md`
- **Vault Watcher**: `scripts/vault-watcher/README.md`
- **Architecture**: `COMPLETE_STRUCTURE.md`

## 🎯 Use Cases

### 1. Unified AI Memory
Import conversations from:
- ChatGPT (`scripts/python/import_chatgpt.py`)
- Claude (coming soon)
- Gemini (coming soon)

All memories searchable across platforms!

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

- **Total files created**: 40+
- **Lines of code**: 10,000+
- **Documentation**: 4,500+ lines
- **AI Agent tools**: 7 (current), 25+ (planned multi-agent)
- **MCP tools**: 17 (12 DB + 5 Memory)
- **Database tables**: 18
- **Vector dimensions**: 768
- **Containers**: 9 (8 core + 1 agent layer)

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
- [Pydantic AI](https://ai.pydantic.dev/) - Agent framework with type safety
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Multi-agent orchestration (planned)
- [OpenMemory](https://github.com/CaviraOSS/OpenMemory) - Long-term memory for AI agents
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Qdrant](https://qdrant.tech/) - Vector database
- [PostgreSQL](https://postgresql.org/) - Relational database
- [AnythingLLM](https://anythingllm.com/) - RAG chat interface
- [n8n](https://n8n.io/) - Workflow automation
- [Obsidian](https://obsidian.md/) - Note-taking app

---

**A complete, privacy-first AI assistant stack for personal use on unRAID.** 🔒✨

> **Note:** This is a personal project designed for single-user deployment. While the architecture is production-ready, it's optimized for individual use cases rather than multi-user scenarios.
