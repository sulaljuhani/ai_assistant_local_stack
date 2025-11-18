# 🔌 Integration FAQ - Google Keep, Subtasks, and More

Answers to common questions about integrations and features in the AI Stack.

---

## 📝 Google Keep/Notes Integration

### Current Status: ❌ NOT Implemented

**What's Missing:**
- No n8n workflow for Google Keep sync
- No database fields for Keep notes (e.g., `keep_id`, `keep_label`)
- No Google Keep credentials in n8n
- No AnythingLLM skill for creating/searching Keep notes

### How to Implement Google Keep Integration

You can add this integration following the same pattern as Google Calendar:

#### Step 1: Create Database Fields

```sql
-- Add to migrations/010_add_google_keep.sql
ALTER TABLE notes ADD COLUMN IF NOT EXISTS keep_id TEXT UNIQUE;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS keep_labels TEXT[];
ALTER TABLE notes ADD COLUMN IF NOT EXISTS keep_color TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS keep_archived BOOLEAN DEFAULT false;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS keep_pinned BOOLEAN DEFAULT false;
CREATE INDEX idx_notes_keep_id ON notes(keep_id);
```

#### Step 2: Setup Google Keep API Access

**Problem:** Google Keep doesn't have an official API! 😞

**Workarounds:**

1. **Unofficial Keep API (Node.js)**
   - Use: `google-keep-api` npm package
   - Note: Requires Google account credentials
   - Risk: May break if Google changes things

2. **Google Tasks API** (Official Alternative)
   - Google Tasks has an official API
   - Similar functionality to Keep
   - Better long-term stability

3. **Google Docs API** (Alternative)
   - Create notes as Google Docs
   - Fully supported official API
   - Store doc IDs in database

#### Step 3: Example n8n Workflow (Using Google Tasks)

Since Google Keep lacks an official API, here's how to use **Google Tasks** instead:

```json
{
  "name": "Google Tasks Sync",
  "nodes": [
    {
      "name": "Trigger: Every 15 Minutes",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "triggerTimes": {
          "item": [
            {
              "mode": "everyX",
              "value": 15,
              "unit": "minutes"
            }
          ]
        }
      }
    },
    {
      "name": "Get Tasks from Google",
      "type": "n8n-nodes-base.googleTasks",
      "parameters": {
        "operation": "getAll",
        "taskListId": "YOUR_TASK_LIST_ID"
      },
      "credentials": {
        "googleTasksOAuth2Api": {
          "id": "1",
          "name": "Google Tasks API"
        }
      }
    },
    {
      "name": "Insert to Database",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "executeQuery",
        "query": "INSERT INTO tasks (title, description, external_service, external_id) VALUES ('{{ $json.title }}', '{{ $json.notes }}', 'google_tasks', '{{ $json.id }}') ON CONFLICT (external_id) DO UPDATE SET title = EXCLUDED.title;"
      }
    }
  ]
}
```

#### Step 4: Alternative - Obsidian Integration (Already Built!)

**Use Obsidian instead of Google Keep:**

The AI Stack already has **Obsidian vault integration** via the file watcher:

```bash
# Setup Obsidian vault auto-embedding (already included)
./scripts/setup-vault.sh
```

**Advantages over Google Keep:**
- ✅ 100% local (privacy)
- ✅ Markdown format (portable)
- ✅ Already integrated with AI Stack
- ✅ Auto-vectorization of notes
- ✅ Semantic search across all notes
- ✅ Graph view for connections

**How to use Obsidian as a Keep replacement:**

1. Install Obsidian: https://obsidian.md/
2. Create notes in your vault
3. File watcher auto-embeds them
4. Search via AnythingLLM: "search my notes for recipes"

### Recommendation: Use Obsidian Instead of Google Keep

Since Google Keep lacks an official API and Obsidian is already fully integrated, we recommend:

| Feature | Google Keep | Obsidian (Current Setup) |
|---------|-------------|--------------------------|
| Official API | ❌ No | ✅ File-based |
| Privacy | ☁️ Cloud | ✅ 100% local |
| Integration | ❌ Not built | ✅ Fully integrated |
| Auto-vectorization | ❌ Not available | ✅ Built-in |
| Semantic search | ❌ Not available | ✅ Via AnythingLLM |
| Graph view | ❌ No | ✅ Yes |
| Mobile app | ✅ Yes | ✅ Yes (with sync) |

---

## ✅ Todoist Subtasks - FULLY IMPLEMENTED!

### Answer: YES, subtasks are implemented! 🎉

The Todoist integration supports subtasks through **three different mechanisms**:

### Method 1: Parent Task ID (Todoist Native)

**Database Schema:**
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    todoist_id TEXT,
    todoist_parent_id TEXT,  -- ← This stores Todoist's parent task
    todoist_project_id TEXT,
    todoist_section_id TEXT,
    ...
);
```

**How it works:**
1. Todoist task with `parent_id` is synced
2. Stored in `todoist_parent_id` column
3. Bidirectional sync preserves hierarchy

**Example:**
```
Main Task: "Plan vacation" (todoist_id: 123456)
  ↳ Subtask 1: "Book flights" (todoist_parent_id: 123456)
  ↳ Subtask 2: "Reserve hotel" (todoist_parent_id: 123456)
```

### Method 2: Local Parent Task ID

**Database Schema:**
```sql
parent_task_id UUID,  -- ← Local reference to parent task
```

**Usage via AnythingLLM:**

The `create-task` skill supports parent tasks:

```javascript
// In anythingllm-skills/create-task.js
inputs: {
    title: { type: "string", required: true },
    parent_task_id: {
        type: "string",
        description: "Parent task ID for subtasks (optional)",
        required: false
    },
    ...
}
```

**Example conversation:**
```
You: "Create a task 'Write thesis'"

AI: ✅ Created task "Write thesis" (ID: abc-123)

You: "Add a subtask 'Research methodology' under task abc-123"

AI: ✅ Created subtask "Research methodology" (parent: abc-123)
```

### Method 3: Checklist JSON (Alternative)

**Database Schema:**
```sql
checklist JSONB  -- ← Array of subtasks as JSON
```

**Format:**
```json
{
  "checklist": [
    {"text": "Buy groceries", "done": false},
    {"text": "Clean kitchen", "done": true},
    {"text": "Call mom", "done": false}
  ]
}
```

**Usage:**
This is useful for simple subtasks that don't need full task functionality.

### Todoist Sync Workflow

**File:** `n8n-workflows/13-todoist-sync.json`

**Sync Flow:**
```
Every 15 minutes:
  1. Fetch tasks from Todoist API
  2. For each task:
     - Extract parent_id (if exists)
     - Store as todoist_parent_id
     - Preserve task hierarchy
  3. Sync back to Todoist (bidirectional)
```

**Key Fields Synced:**
- `todoist_id` - Todoist task ID
- `todoist_parent_id` - Parent task reference
- `todoist_project_id` - Project grouping
- `todoist_section_id` - Section within project
- `title`, `description`, `due_date`, `priority`, `status`

### Working with Subtasks

#### Creating Subtasks via AnythingLLM

**Method 1: Reference parent task ID**
```
You: "Create a task 'Build AI Stack'"

AI: Task created with ID: task-001

You: "Add subtask 'Setup database' under task-001"

AI: ✅ Subtask created under "Build AI Stack"
```

**Method 2: Create in Todoist, auto-sync**
```
1. Create main task in Todoist: "Build AI Stack"
2. Add subtask in Todoist: "Setup database" (drag under main task)
3. Wait 15 minutes for sync
4. Query via AnythingLLM: "show my AI Stack tasks"
```

#### Querying Subtasks via MCP Server

**File:** `containers/mcp-server/server.py`

```python
# Get tasks with their subtasks
async def get_tasks_with_subtasks():
    query = """
        SELECT
            t1.id,
            t1.title,
            t1.todoist_parent_id,
            t2.title as parent_title
        FROM tasks t1
        LEFT JOIN tasks t2 ON t1.todoist_parent_id = t2.todoist_id
        WHERE t1.status != 'completed'
        ORDER BY t2.title, t1.title;
    """
```

#### SQL Queries for Subtasks

**Get all subtasks of a task:**
```sql
-- Find subtasks by Todoist parent ID
SELECT * FROM tasks
WHERE todoist_parent_id = (
    SELECT todoist_id FROM tasks WHERE id = 'parent-task-uuid'
);

-- Find subtasks by local parent ID
SELECT * FROM tasks
WHERE parent_task_id = 'parent-task-uuid';
```

**Get task hierarchy:**
```sql
WITH RECURSIVE task_hierarchy AS (
    -- Base case: top-level tasks (no parent)
    SELECT id, title, todoist_parent_id, 0 as level
    FROM tasks
    WHERE todoist_parent_id IS NULL

    UNION ALL

    -- Recursive case: subtasks
    SELECT t.id, t.title, t.todoist_parent_id, th.level + 1
    FROM tasks t
    INNER JOIN task_hierarchy th ON t.todoist_parent_id = (
        SELECT todoist_id FROM tasks WHERE id = th.id
    )
)
SELECT
    repeat('  ', level) || title as indented_title,
    level
FROM task_hierarchy
ORDER BY level, title;
```

**Count subtasks per task:**
```sql
SELECT
    t1.title as parent_task,
    COUNT(t2.id) as subtask_count
FROM tasks t1
LEFT JOIN tasks t2 ON t1.todoist_id = t2.todoist_parent_id
GROUP BY t1.id, t1.title
HAVING COUNT(t2.id) > 0
ORDER BY subtask_count DESC;
```

### Visualization of Task Hierarchy

Add to `scripts/view-food-log.sh` (or create new script):

```bash
#!/bin/bash
# View Todoist task hierarchy

docker exec postgres-ai-stack psql -U aistack_user -d aistack <<'SQL'
WITH RECURSIVE task_tree AS (
    SELECT
        id,
        title,
        todoist_parent_id,
        0 as depth,
        title as path
    FROM tasks
    WHERE todoist_parent_id IS NULL
      AND status != 'completed'

    UNION ALL

    SELECT
        t.id,
        t.title,
        t.todoist_parent_id,
        tt.depth + 1,
        tt.path || ' → ' || t.title
    FROM tasks t
    INNER JOIN task_tree tt ON t.todoist_parent_id = (
        SELECT todoist_id FROM tasks WHERE id = tt.id
    )
    WHERE t.status != 'completed'
)
SELECT
    repeat('  ', depth) || '├─ ' || title as task_hierarchy,
    status,
    due_date
FROM task_tree
ORDER BY path;
SQL
```

**Output:**
```
task_hierarchy                          | status    | due_date
----------------------------------------+-----------+------------
├─ Build AI Stack                       | active    | 2025-12-01
  ├─ Setup database                     | active    | 2025-11-20
    ├─ Install PostgreSQL               | completed | 2025-11-15
    ├─ Run migrations                   | active    | 2025-11-20
  ├─ Configure Qdrant                   | active    | 2025-11-22
├─ Write documentation                  | active    | 2025-11-25
  ├─ API docs                           | active    | NULL
  ├─ User guide                         | pending   | NULL
```

### MCP Tools for Subtasks

**File:** `containers/mcp-server/server.py` (lines 200-250)

**Available tools:**
```python
# Get all tasks (includes subtasks)
get_tasks_by_status(status="active")

# Search tasks (searches subtasks too)
search_reminders(query="database setup")

# Create task with parent
create_task(title="Subtask", parent_task_id="parent-uuid")
```

---

## 📊 Comparison: Different Subtask Approaches

| Feature | Todoist Parent ID | Local Parent ID | Checklist JSON |
|---------|-------------------|-----------------|----------------|
| Synced to Todoist | ✅ Yes | ❌ No | ❌ No |
| Hierarchical queries | ✅ Yes | ✅ Yes | ⚠️ Limited |
| MCP tool support | ✅ Yes | ✅ Yes | ❌ No |
| Recursive depth | ✅ Unlimited | ✅ Unlimited | ⚠️ Single level |
| Mobile access | ✅ Via Todoist | ❌ No | ❌ No |
| Best for | External sync | Local tasks | Simple checklists |

---

## 🎯 Recommendations

### For Note-Taking:
**Use Obsidian instead of Google Keep**
- Already fully integrated
- Better privacy (100% local)
- More powerful (graph view, linking, tags)
- Auto-vectorization built-in

### For Subtasks:
**Use Todoist parent tasks**
- Fully supported and synced
- Works across devices via Todoist app
- Hierarchical structure maintained
- Bidirectional sync every 15 minutes

### For Database Visualization:
**Use the provided terminal scripts**
- `./scripts/monitor-system.sh` - System overview
- `./scripts/view-food-log.sh` - Food log viewer (after setup)
- Create custom viewers following the same pattern

---

## 🚀 Quick Commands

### View Todoist Tasks with Subtasks
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "
SELECT
    CASE WHEN todoist_parent_id IS NULL THEN '📋 ' ELSE '  └─ ' END || title as task,
    status,
    due_date
FROM tasks
WHERE status != 'completed'
ORDER BY todoist_parent_id NULLS FIRST, title;
"
```

### Check Google Calendar Sync Status
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "
SELECT COUNT(*) as synced_events
FROM events
WHERE external_service = 'google_calendar';
"
```

### View All Integrations
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "
SELECT 'Tasks with Todoist' as integration, COUNT(*) as count
FROM tasks WHERE todoist_id IS NOT NULL
UNION ALL
SELECT 'Events with Google Calendar', COUNT(*)
FROM events WHERE external_service = 'google_calendar'
UNION ALL
SELECT 'Food Log Entries', COUNT(*)
FROM food_log;
"
```

---

**For more details, see:**
- [FOOD_LOG_FEATURE.md](/home/user/ai_assistant_local_stack/docs/FOOD_LOG_FEATURE.md) - Complete food logging guide
- [README.md](/home/user/ai_assistant_local_stack/README.md) - Main project documentation
- [DEPLOYMENT_GUIDE.md](/home/user/ai_assistant_local_stack/DEPLOYMENT_GUIDE.md) - Full deployment instructions
