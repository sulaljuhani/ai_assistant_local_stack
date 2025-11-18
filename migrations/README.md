# AI Stack - Database Migrations

This directory contains PostgreSQL database migrations for the AI Stack, including OpenMemory tables.

## 📋 Migration Files

| File | Description | Key Tables |
|------|-------------|------------|
| `001_initial_schema.sql` | Base setup: users, categories, extensions | `users`, `categories` |
| `002_add_reminders.sql` | Reminders with recurring support | `reminders` |
| `003_add_tasks.sql` | Task management with Todoist sync | `tasks` |
| `004_add_events.sql` | Calendar events with Google sync | `events` |
| `005_add_notes_documents.sql` | Notes (Obsidian) and documents | `notes`, `documents`, `document_chunks`, `file_sync` |
| `006_openmemory_schema.sql` | **OpenMemory core tables** | `memories`, `memory_sectors`, `conversations`, `memory_links`, `imported_chats` |
| `007_performance_indexes.sql` | Optimization indexes and views | Materialized views, helper functions |
| `008_n8n_database.sql` | n8n workflow database setup | `n8n` database |

## 🚀 Running Migrations

### Method 1: Automated Script (Recommended)

```bash
cd /mnt/user/appdata/ai_stack/migrations

# Set environment variables (or use defaults)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5434
export POSTGRES_DB=aistack
export POSTGRES_USER=aistack_user
export POSTGRES_PASSWORD=your_secure_password

# Run all migrations
./run-migrations.sh
```

### Method 2: Docker Exec (unRAID)

```bash
# Copy migrations to container
docker cp /mnt/user/appdata/ai_stack/migrations postgres-ai-stack:/migrations

# Run migrations
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/001_initial_schema.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/002_add_reminders.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/003_add_tasks.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/004_add_events.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/005_add_notes_documents.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/006_openmemory_schema.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/007_performance_indexes.sql
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < /migrations/008_n8n_database.sql
```

### Method 3: Auto-run on First Start

The PostgreSQL container can auto-run migrations on first startup if you mount the migrations directory:

In your unRAID template, set:
```
Container Path: /docker-entrypoint-initdb.d
Host Path: /mnt/user/appdata/ai_stack/migrations
```

**Note:** This only runs on FIRST container start when database is empty!

## 📊 Database Schema Overview

### Core Tables

**User Management**
- `users` - Single default user (UUID: 00000000-0000-0000-0000-000000000001)
- `categories` - Organize reminders, tasks, notes

**Productivity**
- `reminders` - Timed reminders with recurrence
- `tasks` - Task management with Todoist sync
- `events` - Calendar events with Google Calendar sync

**Knowledge Base**
- `notes` - Markdown notes from Obsidian vault
- `documents` - PDFs, DOCX with text extraction
- `document_chunks` - Chunked text for RAG (linked to Qdrant)
- `file_sync` - Track file changes for auto-reembedding

### OpenMemory Tables

**Memory Core**
- `memories` - Main memory storage with salience scoring
- `memory_sectors` - Multi-dimensional classification
  - Sectors: `semantic`, `episodic`, `procedural`, `emotional`, `reflective`
- `conversations` - Group related memories
- `memory_links` - Relationships between memories
- `imported_chats` - Track ChatGPT/Claude/Gemini imports

**Key Features:**
- **Salience Scoring**: 0.0 (trivial) to 1.0 (critical)
- **Multi-sector Classification**: One memory can belong to multiple sectors
- **Access Tracking**: Counts how often memories are retrieved
- **Deduplication**: File hash tracking prevents duplicate imports
- **Temporal Context**: Link memories to time periods

## 🔍 Key Database Functions

### Memory Functions

```sql
-- Search memories by IDs (after Qdrant vector search)
SELECT * FROM search_memories_by_ids(
    ARRAY['uuid1', 'uuid2']::UUID[],
    'semantic'  -- Optional sector filter
);

-- Get conversation context
SELECT * FROM get_conversation_context('conversation-uuid');

-- Get related memories via links
SELECT * FROM get_related_memories('memory-uuid', 2);  -- max depth 2

-- Memory statistics
SELECT * FROM get_memory_stats();

-- Memory quality metrics
SELECT * FROM get_memory_quality_metrics();
```

### Productivity Functions

```sql
-- Upcoming reminders
SELECT * FROM get_reminders_due(60);  -- next 60 minutes

-- Tasks due soon
SELECT * FROM get_tasks_due_soon(7);  -- next 7 days

-- Today's events
SELECT * FROM get_events_today();

-- Events in date range
SELECT * FROM get_events_in_range('2025-11-18', '2025-11-25');

-- User activity summary
SELECT * FROM get_user_activity_summary();
```

### Maintenance Functions

```sql
-- Archive old low-value memories
SELECT archive_low_value_memories(
    180,   -- older than 180 days
    0.2,   -- salience <= 0.2
    1      -- access_count <= 1
);  -- Returns: count of archived memories

-- Clean up orphaned records
SELECT * FROM cleanup_orphaned_records();

-- Refresh materialized views
SELECT refresh_daily_summary();
SELECT refresh_memory_sector_stats();
```

## 🎯 Important Indexes

### Memory Performance
- `idx_memories_relevance` - Composite: salience + access + recency
- `idx_memories_recent_important` - Recent high-salience memories
- `idx_memories_text_search` - Full-text search on content

### Productivity
- `idx_tasks_active_priority` - Active tasks by priority
- `idx_tasks_overdue` - Overdue tasks
- `idx_events_upcoming` - Upcoming events
- `idx_reminders_pending_time` - Pending reminders by time

## 📈 Materialized Views

### `daily_summary`
Daily activity summary (reminders, tasks, events, memories, notes).

```sql
-- View summary
SELECT * FROM daily_summary WHERE user_id = '00000000-0000-0000-0000-000000000001';

-- Refresh (run daily via cron)
SELECT refresh_daily_summary();
```

### `memory_sector_stats`
Memory distribution across sectors with metrics.

```sql
-- View stats
SELECT * FROM memory_sector_stats WHERE user_id = '00000000-0000-0000-0000-000000000001';

-- Refresh (run after imports)
SELECT refresh_memory_sector_stats();
```

## 🔧 Configuration

### Single-User Mode
All tables use a hardcoded UUID for single-user deployments:
```
00000000-0000-0000-0000-000000000001
```

### Embedding Model
All embedding-related fields default to:
- Model: `nomic-embed-text`
- Dimensions: `768`
- Distance: Cosine similarity

### Default Categories
Five categories are auto-created:
- 👤 Personal (Blue)
- 💼 Work (Green)
- ❤️ Health (Red)
- 💰 Finance (Orange)
- 📚 Learning (Purple)

## 🧪 Testing Migrations

### Verify Tables Exist

```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "\dt"
```

### Check Record Counts

```sql
SELECT
    'memories' AS table_name, COUNT(*) FROM memories
UNION ALL SELECT 'memory_sectors', COUNT(*) FROM memory_sectors
UNION ALL SELECT 'conversations', COUNT(*) FROM conversations
UNION ALL SELECT 'tasks', COUNT(*) FROM tasks
UNION ALL SELECT 'reminders', COUNT(*) FROM reminders
UNION ALL SELECT 'events', COUNT(*) FROM events
UNION ALL SELECT 'notes', COUNT(*) FROM notes
UNION ALL SELECT 'documents', COUNT(*) FROM documents;
```

### Test Functions

```sql
-- Test user activity summary
SELECT * FROM get_user_activity_summary();

-- Test memory stats
SELECT * FROM get_memory_stats();

-- Test memory quality metrics
SELECT * FROM get_memory_quality_metrics();
```

## 🛠️ Troubleshooting

### "Permission denied"
Ensure `run-migrations.sh` is executable:
```bash
chmod +x run-migrations.sh
```

### "Connection refused"
1. Check PostgreSQL is running: `docker ps | grep postgres`
2. Verify port: `5434` (host) maps to `5432` (container)
3. Check password matches unRAID template

### "Database does not exist"
Create manually:
```bash
docker exec -it postgres-ai-stack psql -U aistack_user -c "CREATE DATABASE aistack;"
```

### "Table already exists"
Migrations use `IF NOT EXISTS` - safe to re-run.
To force re-create, drop tables first (CAUTION: deletes data):
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Check Migration Status
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "
SELECT schemaname, tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;"
```

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/)
- [Full-text Search in PostgreSQL](https://www.postgresql.org/docs/16/textsearch.html)
- [Qdrant Integration Guide](../docs/QDRANT_SETUP.md)
- [OpenMemory Architecture](../docs/OPENMEMORY_GUIDE.md)

## 🔄 Migration Best Practices

1. **Always backup before migrations** (especially in production)
2. **Test migrations on a copy first** if unsure
3. **Run migrations in order** (001, 002, 003, ...)
4. **Never modify past migrations** - create new ones for changes
5. **Refresh materialized views** after bulk imports
6. **Run ANALYZE** after large data loads for query optimization

---

**Database schema designed for single-user AI Stack with OpenMemory** 🗄️
