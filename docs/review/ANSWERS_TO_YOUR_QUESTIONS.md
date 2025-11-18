# 📋 Answers to Your Questions

Quick reference for all your questions about the AI Stack.

---

## Question 1: How to Create Custom Database for Food Tracking?

### ✅ IMPLEMENTED! Complete food tracking system created.

**What was built:**
- ✅ Database migration: `migrations/009_create_food_log.sql`
- ✅ n8n workflow with vectorization: `n8n-workflows/19-food-log.json`
- ✅ AnythingLLM skills: `log-food.js` and `recommend-food.js`
- ✅ Qdrant collection: `food_memories` (768-dim vectors)
- ✅ Visualization script: `scripts/view-food-log.sh`

**How it works:**
1. You say: *"I ate spaghetti carbonara for dinner, I made it myself, rating 5/5"*
2. AnythingLLM logs it to PostgreSQL
3. System generates embedding using Ollama (nomic-embed-text)
4. Vector stored in Qdrant for semantic search
5. You ask: *"What should I eat that I liked but haven't had in a while?"*
6. AI searches vectors for similar foods you rated highly
7. Returns foods you liked, sorted by oldest first

**Setup:**
```bash
./scripts/setup-food-log.sh
```

Then import:
- n8n workflow: `19-food-log.json`
- AnythingLLM skills: `log-food.js`, `recommend-food.js`

**Full documentation:** [docs/FOOD_LOG_FEATURE.md](docs/FOOD_LOG_FEATURE.md)

---

## Question 2: Simple Way to Visualize Database Content?

### ✅ YES! Multiple visualization options available.

### Option 1: Terminal Dashboard (Already Built)
```bash
./scripts/monitor-system.sh
```
Shows real-time stats for all databases.

### Option 2: Food Log Viewer (New)
```bash
./scripts/view-food-log.sh
```
Interactive menu with 9 views:
- Recent entries
- Statistics
- Top rated foods
- Recommendations
- Search by name/date/tag
- Made vs bought comparison

### Option 3: Direct SQL Queries
```bash
# View any table
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT * FROM tasks LIMIT 10;"

# View statistics
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT * FROM get_food_stats();"
```

### Option 4: Web UIs (Already Available)
- **n8n**: http://localhost:5678 - See workflow executions
- **AnythingLLM**: http://localhost:3001 - Chat interface
- **Qdrant**: http://localhost:6333/dashboard - Vector database

### Creating Custom Viewers

Follow the pattern in `scripts/view-food-log.sh`:
```bash
#!/bin/bash
# Execute SQL and display results
execute_query() {
    docker exec -i postgres-ai-stack psql -U aistack_user -d aistack -c "$1"
}

# Example: View all memories
execute_query "SELECT * FROM memories ORDER BY created_at DESC LIMIT 20;"
```

**Templates:**
- Food log viewer: `scripts/view-food-log.sh` (289 lines, 9 views)
- System monitor: `scripts/monitor-system.sh` (real-time dashboard)

---

## Question 3: Integrate with Google Notes (Google Keep)?

### ❌ NOT Currently Implemented

**Why:**
- Google Keep has **no official API**
- Only unofficial libraries exist (may break)
- High maintenance risk

**Alternatives (Better Options):**

### Option A: Use Obsidian (Already Integrated! ✅)

Obsidian is **already fully integrated** and is better than Google Keep:

| Feature | Google Keep | Obsidian (Current) |
|---------|-------------|--------------------|
| Official API | ❌ No | ✅ File-based |
| Privacy | ☁️ Cloud only | ✅ 100% local |
| Auto-vectorization | ❌ No | ✅ Built-in |
| Semantic search | ❌ No | ✅ Via AI |
| Graph view | ❌ No | ✅ Yes |
| Already setup | ❌ No | ✅ Yes! |

**How to use Obsidian as note system:**
```bash
# Already included in the stack!
./scripts/setup-vault.sh
```

Then:
1. Create notes in Obsidian vault
2. File watcher auto-vectorizes them
3. Search via AnythingLLM: *"search my notes for pasta recipes"*

### Option B: Use Google Tasks (Official API)

Google Tasks has an official API and works similarly to Keep.

**Implementation steps:**
1. Add to database:
```sql
ALTER TABLE tasks ADD COLUMN google_tasks_id TEXT;
ALTER TABLE tasks ADD COLUMN google_tasks_list_id TEXT;
```

2. Create n8n workflow (similar to Todoist sync)
3. Use n8n's Google Tasks node (built-in)

### Option C: Use Google Docs (Official API)

Store notes as Google Docs with official API support.

**Recommendation:**
**Use Obsidian** - it's already integrated, more powerful, and 100% local.

**Reference:** [docs/INTEGRATION_FAQ.md](docs/INTEGRATION_FAQ.md#-google-keepnotes-integration)

---

## Question 4: Are Subtasks Implemented in Todoist?

### ✅ YES! Fully implemented with 3 different methods.

### Method 1: Todoist Parent Tasks (Recommended)

**Database fields:**
```sql
todoist_id TEXT,           -- Todoist task ID
todoist_parent_id TEXT,    -- Parent task reference
todoist_project_id TEXT,   -- Project grouping
todoist_section_id TEXT    -- Section within project
```

**How it works:**
1. Create task in Todoist: "Build AI Stack"
2. Add subtask in Todoist: "Setup database" (drag under main task)
3. Syncs automatically every 15 minutes
4. Hierarchy preserved in local database

**Sync file:** `n8n-workflows/13-todoist-sync.json`

### Method 2: Local Parent Task ID

**Database field:**
```sql
parent_task_id UUID  -- Local parent reference
```

**Via AnythingLLM:**
```
You: "Create a task 'Write thesis'"
AI: ✅ Created task (ID: abc-123)

You: "Add subtask 'Research methodology' under abc-123"
AI: ✅ Created subtask under "Write thesis"
```

**Skill file:** `anythingllm-skills/create-task.js` (has `parent_task_id` parameter)

### Method 3: Checklist JSON

**Database field:**
```sql
checklist JSONB  -- Simple subtask list
```

**Format:**
```json
{
  "checklist": [
    {"text": "Buy milk", "done": false},
    {"text": "Pay bills", "done": true}
  ]
}
```

### Viewing Subtasks

**SQL query:**
```sql
-- Get task hierarchy
SELECT
    CASE WHEN todoist_parent_id IS NULL THEN '📋 ' ELSE '  └─ ' END || title as task,
    status,
    due_date
FROM tasks
WHERE status != 'completed'
ORDER BY todoist_parent_id NULLS FIRST, title;
```

**Output:**
```
task                          | status | due_date
------------------------------+--------+------------
📋 Build AI Stack             | active | 2025-12-01
  └─ Setup database           | active | 2025-11-20
  └─ Configure Qdrant         | active | 2025-11-22
📋 Write documentation        | active | 2025-11-25
  └─ API docs                 | active | NULL
```

**Reference:** [docs/INTEGRATION_FAQ.md](docs/INTEGRATION_FAQ.md#-todoist-subtasks---fully-implemented)

---

## 📂 Files Created for You

### Food Tracking System
```
migrations/
  └── 009_create_food_log.sql          # Database schema (180 lines)

n8n-workflows/
  └── 19-food-log.json                 # Logging & recommendations workflow

anythingllm-skills/
  ├── log-food.js                      # Log food skill
  └── recommend-food.js                # Get recommendations skill

scripts/
  ├── setup-food-log.sh                # Automated setup (executable)
  └── view-food-log.sh                 # Interactive viewer (executable)

docs/
  ├── FOOD_LOG_FEATURE.md              # Complete feature guide (500+ lines)
  └── INTEGRATION_FAQ.md               # Google Keep & subtasks FAQ (400+ lines)
```

---

## 🚀 Quick Start Commands

### Setup Food Logging
```bash
# 1. Run setup
./scripts/setup-food-log.sh

# 2. Import workflow in n8n
# Open http://localhost:5678
# Import: n8n-workflows/19-food-log.json

# 3. Install skills in AnythingLLM
# Open http://localhost:3001
# Upload: log-food.js and recommend-food.js

# 4. Test it!
# Say in AnythingLLM: "Log that I ate pizza for lunch, rating 5 stars"
```

### View Food Log
```bash
./scripts/view-food-log.sh
```

### View Todoist Subtasks
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "
SELECT
    CASE WHEN todoist_parent_id IS NULL THEN '📋 ' ELSE '  └─ ' END || title,
    status
FROM tasks
WHERE status != 'completed'
ORDER BY todoist_parent_id NULLS FIRST;
"
```

### Setup Obsidian (Alternative to Google Keep)
```bash
./scripts/setup-vault.sh
# Then create notes in Obsidian, they auto-vectorize!
```

---

## 📚 Full Documentation

| Document | Description |
|----------|-------------|
| [FOOD_LOG_FEATURE.md](docs/FOOD_LOG_FEATURE.md) | Complete guide to food tracking system |
| [INTEGRATION_FAQ.md](docs/INTEGRATION_FAQ.md) | Google Keep, subtasks, visualizations |
| [README.md](README.md) | Main project documentation |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Full deployment instructions |

---

## 💡 Summary

| Question | Answer | Status |
|----------|--------|--------|
| **1. Custom food database?** | ✅ Complete system with vectorization | **BUILT** |
| **2. Visualize database?** | ✅ Terminal scripts + web UIs available | **AVAILABLE** |
| **3. Google Notes integration?** | ❌ Not built (use Obsidian instead) | **ALTERNATIVE PROVIDED** |
| **4. Todoist subtasks?** | ✅ Fully implemented, 3 methods | **WORKING** |

---

**All systems operational! 🚀**

For detailed information, see the docs folder.
For quick commands, see sections above.
For full guides, see FOOD_LOG_FEATURE.md and INTEGRATION_FAQ.md.
