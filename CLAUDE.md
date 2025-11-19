# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**AI Stack** is a production-ready, local AI assistant system for single-user deployment on unRAID servers. It provides 100% local operation with unified memory across AI conversations (ChatGPT, Claude, Gemini), semantic search, task/reminder/event management, and multi-agent conversational AI.

**Key Facts:**
- **Status:** Production Ready (Security audited, all critical issues resolved)
- **Architecture:** Multi-agent LangGraph system with FastAPI backend
- **Recent Change:** Migrated from n8n workflows to native Python (Nov 2025)
- **Deployment:** 8 Docker containers on shared bridge network
- **Privacy:** 100% local, no cloud dependencies

---

## Quick Start Commands

### System Management

```bash
# Start full stack
docker-compose up -d

# View LangGraph logs
docker logs langgraph-agents -f

# System health check
./scripts/monitor-system.sh

# API health
curl http://localhost:8080/health
```

### Database Operations

```bash
# Connect to PostgreSQL
docker exec -it postgres-ai-stack psql -U aistack_user -d aistack

# Run migrations
cd migrations && ./run-migrations.sh

# Memory statistics
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT * FROM get_memory_stats();"
```

### Development

```bash
# View API docs
# Swagger: http://localhost:8080/docs
# ReDoc: http://localhost:8080/redoc

# View scheduled jobs
curl http://localhost:8080/scheduler/jobs | jq

# Test API endpoints
cd tests && ./test-webhooks.sh

# Local development (LangGraph only)
cd containers/langgraph-agents
pip install -r requirements.txt
export POSTGRES_PASSWORD=your_password
export LLM_PROVIDER=ollama
python main.py
```

---

## Architecture Overview

### System Architecture

```
User Interfaces (AnythingLLM, API)
           ↓
LangGraph Multi-Agent System (FastAPI)
    ├── Food Agent
    ├── Task Agent
    └── Event Agent
           ↓
    Tool Layer (30+ tools)
    ├── Database (asyncpg)
    ├── Vector (Qdrant)
    ├── Memory (OpenMemory)
    └── Documents
           ↓
APScheduler (10 background jobs)
           ↓
Data Layer (PostgreSQL, Qdrant, Redis)
External Services (Ollama, OpenMemory)
```

### Key Components

**LangGraph Agents** (`/containers/langgraph-agents/`)
- **main.py** - FastAPI application entry point
- **config.py** - Pydantic settings (all environment variables)
- **routers/** - 21 REST API endpoints organized by domain
- **services/** - 10 scheduled background jobs (APScheduler)
- **tools/** - 30+ agent tools (database, vector, hybrid, memory)
- **graph/** - LangGraph workflow, state, routing, checkpointing
- **agents/** - Specialized agents (food, task, event)
- **prompts/** - System prompts for each agent

**MCP Server** (`/containers/mcp-server/`)
- **server.py** - Model Context Protocol server (12 database tools for Claude Desktop)

**Migrations** (`/migrations/`)
- 10 SQL files defining PostgreSQL schema
- `run-migrations.sh` - Automated migration runner

**Scripts** (`/scripts/`)
- Qdrant initialization and verification
- Obsidian vault file watchers (Bash/PowerShell)
- System monitoring and maintenance

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| AI Framework | LangGraph | 0.2.50 | Multi-agent orchestration |
| Web Framework | FastAPI | 0.115.0 | REST API |
| Scheduler | APScheduler | 3.10.4 | Background jobs |
| Validation | Pydantic | 2.9.2 | Type-safe models |
| LLM | Ollama | - | Local inference (llama3.2:3b) |
| Embeddings | nomic-embed-text | - | 768 dimensions |
| Database | PostgreSQL | 16 | Structured data |
| Vector DB | Qdrant | - | Semantic search |
| Cache/State | Redis | 7 | Conversation state |
| Memory | OpenMemory | - | Long-term memory (MCP) |

**Key Python packages:** `langgraph`, `langchain`, `fastapi`, `uvicorn`, `pydantic`, `asyncpg`, `redis`, `qdrant-client`, `apscheduler`

---

## Directory Structure

```
/mnt/user/appdata/ai_stack/
├── containers/
│   ├── langgraph-agents/          # ⭐ MAIN APPLICATION
│   │   ├── main.py                # FastAPI entry point
│   │   ├── config.py              # Environment configuration
│   │   ├── routers/               # REST endpoints (21)
│   │   ├── services/              # Background jobs (10)
│   │   ├── tools/                 # Agent tools (30+)
│   │   ├── graph/                 # LangGraph workflow
│   │   ├── agents/                # Specialized agents (3)
│   │   ├── prompts/               # System prompts
│   │   └── utils/                 # Shared utilities
│   └── mcp-server/                # MCP server (12 tools)
├── migrations/                     # SQL schema (10 files)
├── scripts/                        # Utilities & maintenance
├── unraid-templates/               # Docker templates (8)
├── docs/                           # Documentation (30+ files)
├── tests/                          # Test scripts
├── archive/n8n-workflows/          # ⚠️ DEPRECATED (migrated to Python)
└── .env                            # Environment config
```

---

## Key Architectural Patterns

### 1. Multi-Agent System

**Pattern:** State machine with hybrid routing (keywords + LLM)

```
Request → Hybrid Router → Agent Selection → Tool Execution → Response
```

**Agents:**
- **Food Agent** - Food logging specialist
- **Task Agent** - Task management specialist
- **Event Agent** - Calendar specialist

**State Management:**
- Messages pruned to last 20 (prevents memory bloat)
- Redis checkpointing with 24-hour TTL
- Thread-based isolation

**Key Files:**
- `graph/workflow.py` - Main workflow definition
- `graph/routing.py` - Hybrid routing logic
- `agents/` - Agent implementations

### 2. REST API Layer

**Pattern:** Router-based with dependency injection

**Endpoint Organization:**
- `/api/tasks/*` - CRUD operations
- `/api/reminders/*` - CRUD operations
- `/api/events/*` - CRUD operations
- `/api/vault/*` - Document embedding
- `/api/documents/*` - File management
- `/api/memory/*` - Memory operations
- `/api/import/*` - Chat history imports

**Key Files:**
- `main.py` - App initialization
- `routers/` - Domain-specific endpoints

### 3. Scheduled Jobs

**Pattern:** Cron-based background tasks (APScheduler)

**10 Scheduled Jobs:**
1. Fire reminders (every 5 min)
2. Daily summary (8 AM)
3. Expand recurring tasks (midnight)
4. Cleanup old data (Sunday 2 AM)
5. Health check (every 5 min)
6. Vault sync (every 12 hours)
7. Enrich memories (3 AM)
8. Memory vault export (every 6 hours)
9. Todoist sync (every 15 min, if configured)
10. Google Calendar sync (every 15 min, if configured)

**Key Files:**
- `services/scheduler.py` - Job registration
- `services/` - Job implementations

### 4. Tool Layer

**Pattern:** LangChain @tool decorator with async execution

**Tool Categories:**
- **Database** (23 tools) - Direct SQL queries via asyncpg
- **Vector** (6 tools) - Qdrant semantic search
- **Hybrid** (4 tools) - Combined DB + vector
- **Memory** (5 tools) - OpenMemory integration
- **Documents** (4 tools) - File processing

### 5. Configuration

**Pattern:** Pydantic Settings with environment variables

All configuration via `.env` file:
- LLM provider (Ollama/OpenAI)
- Database connections
- State management
- CORS settings
- External integrations

**Key File:** `config.py`

---

## Important Conventions

### Single-User Design

**Hardcoded User UUID:** `00000000-0000-0000-0000-000000000001`

This is a **personal project** designed for single-user deployment. Do NOT implement multi-tenancy. All database queries filter by this user ID.

### Security Patterns

**All security issues resolved (see `/docs/reports/PRODUCTION_READINESS_REPORT.md`)**

**Critical Rules:**
1. **ALWAYS** use parameterized queries:
   ```python
   # ✅ CORRECT
   query = "SELECT * FROM tasks WHERE user_id = $1"
   await conn.fetch(query, user_id)

   # ❌ WRONG (SQL injection)
   query = f"SELECT * FROM tasks WHERE user_id = '{user_id}'"
   ```

2. **ALWAYS** validate inputs with Pydantic:
   ```python
   class CreateTaskRequest(BaseModel):
       title: str = Field(min_length=1, max_length=500)
   ```

3. **NEVER** commit secrets or `.env` files

4. **ALWAYS** use environment variables for configuration

5. Generic errors to users, detailed logs internally:
   ```python
   try:
       # operation
   except Exception as e:
       logger.error("Detailed error", exc_info=True)
       raise HTTPException(status_code=500, detail="Generic message")
   ```

### Error Handling

**Pattern:** Try-catch with structured logging

Log detailed errors, return generic messages to users.

### Database Queries

**Pattern:** Parameterized queries only (SQL injection protection)

All queries use `$1, $2` placeholders with parameter arrays.

### Memory Sectors

**Pattern:** Multi-dimensional classification

Memories classified into 5 sectors:
- **Semantic** - Facts, definitions
- **Episodic** - Events, experiences
- **Procedural** - How-to, instructions
- **Emotional** - Preferences, feelings
- **Reflective** - Insights, learnings

One memory can belong to multiple sectors.

### File Naming

- SQL migrations: `NNN_descriptive_name.sql` (numbered)
- Python modules: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

---

## Common Tasks

### Adding a New API Endpoint

1. Create Pydantic model in `/routers/{domain}.py`:
   ```python
   class CreateFooRequest(BaseModel):
       name: str = Field(min_length=1)
   ```

2. Add endpoint:
   ```python
   @router.post("/api/foo/create")
   async def create_foo(request: CreateFooRequest):
       # Implementation
   ```

3. Register router in `main.py`:
   ```python
   from routers import foo_router
   app.include_router(foo_router)
   ```

4. Add database function in `tools/database.py` if needed
5. Update documentation

### Adding a Scheduled Job

1. Create job function in `/services/{service}.py`:
   ```python
   async def my_job():
       logger.info("Job started")
       # Implementation
   ```

2. Register in `/services/scheduler.py`:
   ```python
   scheduler.add_job(my_job, 'cron', hour=3, minute=0, id='my_job')
   ```

3. Test manually:
   ```python
   await my_job()
   ```

### Adding an Agent Tool

1. Create tool in `/tools/{category}.py`:
   ```python
   @tool
   async def my_tool(param: str) -> Dict:
       """Tool description for LLM"""
       # Implementation
       return result
   ```

2. Add to agent's tool list in `/agents/{agent}_agent.py`:
   ```python
   TOOLS = [existing_tool, my_tool]
   ```

3. Update agent system prompt to mention capability

### Modifying Database Schema

1. Create migration file:
   ```bash
   cd migrations
   touch 011_add_feature.sql
   ```

2. Write SQL with IF NOT EXISTS:
   ```sql
   CREATE TABLE IF NOT EXISTS new_table (
       id UUID PRIMARY KEY,
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

3. Test migration:
   ```bash
   docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < 011_add_feature.sql
   ```

4. Update `run-migrations.sh`

### Debugging Agent Behavior

1. Check logs:
   ```bash
   docker logs langgraph-agents -f --tail=100
   ```

2. Enable debug logging in `.env`:
   ```bash
   LOG_LEVEL=DEBUG
   ```

3. Inspect system prompt:
   ```bash
   cat containers/langgraph-agents/prompts/{agent}_agent.txt
   ```

4. Test tool directly in Python console

5. Check Redis state:
   ```bash
   docker exec redis-ai-stack redis-cli
   KEYS checkpoint:*
   GET checkpoint:{session_id}:latest
   ```

---

## Troubleshooting

### Container Won't Start

```bash
# View logs
docker logs {container-name} --tail=50

# Check port conflicts
netstat -tulpn | grep {port}

# Verify environment
docker exec {container} env | grep POSTGRES
```

### Database Connection Failed

```bash
# Test connection
docker exec postgres-ai-stack pg_isready

# Manual connection
docker exec -it postgres-ai-stack psql -U aistack_user -d aistack
```

### Agent Not Responding

1. Check Ollama is running:
   ```bash
   docker exec ollama-ai-stack ollama list
   ```

2. Check API health:
   ```bash
   curl http://localhost:8080/health
   ```

3. Check Redis:
   ```bash
   docker exec redis-ai-stack redis-cli ping
   ```

4. View logs:
   ```bash
   docker logs langgraph-agents --tail=100
   ```

### Vector Search No Results

```bash
# Check collections exist
curl http://localhost:6333/collections

# Verify point count
curl http://localhost:6333/collections/memories | jq '.result.points_count'

# Check embedding model
docker exec ollama-ai-stack ollama list | grep nomic

# Test embedding generation (should return 768)
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}' | jq '.embedding | length'
```

### Scheduled Jobs Not Running

```bash
# View scheduler status
curl http://localhost:8080/scheduler/jobs | jq

# Check job logs
docker logs langgraph-agents | grep "Job"

# Verify APScheduler running
docker exec langgraph-agents ps aux | grep python
```

---

## Important Notes for Future Instances

### 1. n8n is Deprecated

The `/archive/n8n-workflows/` directory contains **archived workflows** migrated to Python. Do NOT use n8n. All automation is now in REST endpoints and scheduled jobs.

### 2. 100% Local Operation

Do NOT add cloud dependencies. All processing must be local. Optional integrations (Todoist, Google Calendar) are sync-only.

### 3. Security is Critical

All security issues audited and fixed. When making changes:
- ALWAYS use parameterized queries
- ALWAYS validate with Pydantic
- NEVER commit secrets
- ALWAYS use environment variables

### 4. LLM Provider Flexibility

Code supports both Ollama and OpenAI:
```python
from utils.llm import get_llm
llm = get_llm(temperature=0.7)  # Uses configured provider
```

### 5. Documentation Required

Every new feature needs:
- Pydantic validation model
- Docstring
- README update
- Usage example

### 6. Testing Strategy

Integration testing via scripts preferred. Add tests to `/tests/test-webhooks.sh` for new endpoints.

### 7. Performance Considerations

- State pruning prevents bloat (20 messages max)
- Hybrid routing reduces LLM calls (keywords first)
- Database has indexes on common queries
- Qdrant uses cosine similarity for speed

---

## Configuration

### Critical Environment Variables

Located in `.env` (copy from `.env.example`):

```bash
# Database (REQUIRED)
POSTGRES_PASSWORD=CHANGE_ME  # ⚠️ Must be 12+ characters

# LLM Provider
LLM_PROVIDER=ollama  # or "openai"
OLLAMA_BASE_URL=http://ollama-ai-stack:11434
OLLAMA_MODEL=llama3.2:3b

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3001

# State Management
STATE_PRUNING_ENABLED=true
STATE_MAX_MESSAGES=20
STATE_TTL_SECONDS=86400

# External Integrations (optional)
TODOIST_API_TOKEN=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

See `.env.example` for all 50+ options with documentation.

---

## Resources

### Primary Documentation
- **README.md** - Start here
- **containers/langgraph-agents/ARCHITECTURE.md** - Detailed architecture
- **docs/N8N_TO_PYTHON_MIGRATION_PLAN.md** - Migration details
- **docs/reports/PRODUCTION_READINESS_REPORT.md** - Security audit
- **docs/INDEX.md** - Documentation index

### API Documentation
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- Scheduler: `http://localhost:8080/scheduler/jobs`

### External Resources
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Qdrant Docs](https://qdrant.tech/documentation/)

---

## Project Statistics

- **Python Code:** 35+ files, 12,000+ lines
- **SQL Migrations:** 10 files, 1,232 lines
- **Documentation:** 30+ files, 20,000+ lines
- **Containers:** 8 Docker containers
- **API Endpoints:** 21 REST endpoints
- **Scheduled Jobs:** 10 background jobs
- **Agent Tools:** 30+ tools
- **Security Issues:** 0 (all resolved)

---

**This is a production-ready, security-audited AI assistant stack. When working on this codebase: read the relevant README first, check existing patterns, maintain security standards, document changes, and test thoroughly.**
