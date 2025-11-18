# 🔒 n8n Workflow Security Fix Guide

## ⚠️ CRITICAL: 14 of 20 workflows contain SQL injection vulnerabilities

This guide explains how to fix all vulnerable workflows using n8n's built-in parameterized query operations.

---

## Understanding the Problem

### ❌ VULNERABLE Pattern (String Interpolation):
```json
{
  "operation": "executeQuery",
  "query": "INSERT INTO tasks (title) VALUES ('{{ $json.body.title }}')"
}
```

**Why dangerous**: User input is directly inserted into SQL string, allowing:
```sql
-- Attacker sends: title = "Test'); DROP TABLE tasks; --"
-- Resulting SQL: INSERT INTO tasks (title) VALUES ('Test'); DROP TABLE tasks; --')
```

### ✅ SECURE Pattern (Parameterized):
```json
{
  "operation": "insert",
  "table": "tasks",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "title": "={{ $json.body.title }}"
    }
  }
}
```

**Why secure**: n8n PostgreSQL node automatically parameterizes the query.

---

## Fix Instructions by Workflow

### 1. **01-create-reminder.json**

**Current Vulnerable Code** (Line 21):
```json
{
  "operation": "executeQuery",
  "query": "INSERT INTO reminders (user_id, title, description, remind_at, status, priority, category_id)\nVALUES ('00000000-0000-0000-0000-000000000001', '{{ $json.body.title }}', '{{ $json.body.description }}', '{{ $json.body.remind_at }}', 'pending', '{{ $json.body.priority || \"medium\" }}', (SELECT id FROM categories WHERE user_id = '00000000-0000-0000-0000-000000000001' AND name = '{{ $json.body.category || \"General\" }}'))"
}
```

**Fixed Secure Code**:
```json
{
  "operation": "insert",
  "schema": "public",
  "table": "reminders",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "00000000-0000-0000-0000-000000000001",
      "title": "={{ $json.body.title }}",
      "description": "={{ $json.body.description || null }}",
      "remind_at": "={{ $json.body.remind_at }}",
      "status": "pending",
      "priority": "={{ $json.body.priority || 'medium' }}",
      "category_id": "={{ $('Get Category ID').item.json.id }}"
    }
  },
  "options": {
    "returnFields": "id,title,remind_at"
  }
}
```

**Additional Node Required** (before insert):
```json
{
  "name": "Get Category ID",
  "type": "n8n-nodes-base.postgres",
  "parameters": {
    "operation": "select",
    "schema": "public",
    "table": "categories",
    "returnAll": false,
    "limit": 1,
    "where": {
      "conditions": [
        {
          "column": "user_id",
          "operator": "=",
          "value": "00000000-0000-0000-0000-000000000001"
        },
        {
          "column": "name",
          "operator": "=",
          "value": "={{ $json.body.category || 'General' }}"
        }
      ]
    }
  }
}
```

---

### 2. **02-create-task.json**

**Fix Pattern**: Same as reminders, use `insert` operation with `defineBelow` mapping.

**Key Changes**:
- Replace `executeQuery` with `insert`
- Map each field individually
- Handle NULL values with `|| null` instead of string concatenation
- For `parent_task_id` and `category_id`, use separate SELECT nodes if needed

---

### 3. **03-create-event.json**

**Fix Pattern**: Use `insert` operation for events table.

**Special Handling**:
- `location`: Can be NULL, use `={{ $json.body.location || null }}`
- `external_calendar_id`: Can be NULL
- For timestamps, ensure proper format validation

---

### 4. **04-fire-reminders.json**

**Current Vulnerable Code** (Line 59):
```json
{
  "operation": "executeQuery",
  "query": "UPDATE reminders\nSET status = 'fired', fired_at = NOW(), updated_at = NOW()\nWHERE id = '{{ $json.id }}'\nRETURNING id, title;"
}
```

**Fixed Secure Code**:
```json
{
  "operation": "update",
  "schema": "public",
  "table": "reminders",
  "updateKey": "id",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "id": "={{ $json.id }}",
      "status": "fired",
      "fired_at": "={{ $now }}",
      "updated_at": "={{ $now }}"
    }
  },
  "options": {
    "returnFields": "id,title"
  }
}
```

---

### 5. **06-expand-recurring-tasks.json**

**Challenge**: Multiple statements (INSERT + UPDATE).

**Solution**: Split into two separate PostgreSQL nodes:

**Node 1 - Insert New Task Instance**:
```json
{
  "name": "Create Task Instance",
  "operation": "insert",
  "table": "tasks",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "={{ $json.user_id }}",
      "title": "={{ $json.title }}",
      "description": "={{ $json.description }}",
      "status": "todo",
      "priority": "={{ $json.priority }}",
      "due_date": "={{ $json.next_date }}",
      "category_id": "={{ $json.category_id }}",
      "parent_task_id": "={{ $json.id }}"
    }
  }
}
```

**Node 2 - Update Parent Task**:
```json
{
  "name": "Update Parent Recurrence",
  "operation": "update",
  "table": "tasks",
  "updateKey": "id",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "id": "={{ $('Get Recurring Tasks').item.json.id }}",
      "next_recurrence_date": "={{ $json.next_date }}",
      "updated_at": "={{ $now }}"
    }
  }
}
```

---

### 6. **07-watch-vault.json** & **18-scheduled-vault-sync.json**

**Challenge**: File content can be very large (10,000+ characters).

**Solution**: Use INSERT operation with content as field:

```json
{
  "operation": "insert",
  "table": "notes",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "00000000-0000-0000-0000-000000000001",
      "title": "={{ $json.relative_path }}",
      "content": "={{ $('Read File').item.json.data.toString('utf-8') }}",
      "file_path": "={{ $json.file_path }}",
      "file_hash": "={{ $json.file_hash }}"
    }
  }
}
```

**Important**: n8n handles escaping of large text automatically.

---

### 7. **09-store-chat-turn.json** (CRITICAL - 3 vulnerable nodes)

**Node 1 - Insert Conversation**:
```json
{
  "operation": "insert",
  "table": "conversations",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "00000000-0000-0000-0000-000000000001",
      "title": "={{ $json.body.conversation_title || 'Untitled Conversation' }}",
      "source": "={{ $json.body.source || 'chat' }}",
      "external_id": "={{ $json.body.conversation_id }}"
    }
  },
  "options": {
    "returnFields": "id"
  }
}
```

**Node 2 - Insert Memory**:
```json
{
  "operation": "insert",
  "table": "memories",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "00000000-0000-0000-0000-000000000001",
      "content": "={{ $json.body.content }}",
      "memory_type": "explicit",
      "source": "={{ $json.body.source || 'chat' }}",
      "conversation_id": "={{ $('Insert Conversation').item.json.id }}",
      "event_timestamp": "={{ $now }}",
      "salience_score": "={{ $json.body.salience_score || 0.5 }}"
    }
  }
}
```

**Node 3 - Insert Memory Sectors**:
```json
{
  "operation": "insert",
  "table": "memory_sectors",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "memory_id": "={{ $json.memory_id }}",
      "sector": "={{ $json.sector }}",
      "qdrant_point_id": "={{ $json.point_id }}",
      "confidence": 0.8,
      "embedding_dimensions": 768
    }
  }
}
```

---

### 8. **11-enrich-memories.json**

**Challenge**: Complex JOIN query for related memories.

**Solution**: Keep the SELECT query (read-only, less critical) but fix the INSERT:

```json
{
  "operation": "insert",
  "table": "memory_enrichments",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "memory_id": "={{ $json.memory_id }}",
      "enrichment_type": "summary",
      "enrichment_data": "={{ $json.enrichment }}"
    }
  }
}
```

**Note**: For complex JOINs where parameterization is difficult, consider:
1. Move to a stored procedure
2. Use separate SELECT nodes with WHERE clauses
3. Validate UUIDs before query execution

---

### 9. **12-sync-memory-to-vault.json**

**Current Issue**: JSONB object with string interpolation.

**Fixed**:
```json
{
  "operation": "update",
  "table": "memories",
  "updateKey": "id",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "id": "={{ $json.memory_id }}",
      "metadata": "={{ { synced_to_vault: true, vault_file: $json.filename } }}",
      "updated_at": "={{ $now }}"
    }
  }
}
```

**Note**: n8n automatically converts JavaScript objects to JSONB.

---

### 10. **13-todoist-sync.json** & **14-google-calendar-sync.json**

**Pattern**: External API data insertion.

**Security Note**: Even though data comes from Todoist/Google, it's still user-controlled (user created the task/event).

**Fix**: Use `insert` operation with field mapping:

```json
{
  "operation": "insert",
  "table": "tasks",
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "user_id": "00000000-0000-0000-0000-000000000001",
      "title": "={{ $json.content }}",
      "description": "={{ $json.description || null }}",
      "status": "={{ $json.is_completed ? 'done' : 'todo' }}",
      "priority": "={{ $json.priority > 3 ? 'high' : ($json.priority > 2 ? 'medium' : 'low') }}",
      "due_date": "={{ $json.due ? $json.due.date : null }}",
      "external_service": "todoist",
      "external_id": "={{ $json.id }}"
    }
  }
}
```

---

### 11. **15-watch-documents.json**

**Same pattern as vault watchers** - use `insert` for documents.

---

### 12. **19-food-log.json**

**CRITICAL**: Already fixed in `19-food-log-SECURE.json`.

**Key Changes**:
- ARRAY fields: Pass as JavaScript arrays, n8n converts to PostgreSQL arrays
- `ingredients`: `={{ $json.body.ingredients || [] }}`
- `tags`: `={{ $json.body.tags || [] }}`

---

## General Patterns

### Handling NULL Values

**❌ Wrong**:
```json
{{ $json.field ? `'${$json.field}'` : 'NULL' }}
```

**✅ Correct**:
```json
"field": "={{ $json.field || null }}"
```

### Handling Arrays

**❌ Wrong**:
```json
ARRAY[{{ $json.items.map(i => `'${i}'`).join(',') }}]
```

**✅ Correct**:
```json
"items": "={{ $json.items || [] }}"
```

n8n automatically converts to PostgreSQL array syntax.

### Handling Conditional Logic

**❌ Wrong**:
```sql
{{ $json.completed ? "'done'" : "'pending'" }}
```

**✅ Correct**:
```json
"status": "={{ $json.completed ? 'done' : 'pending' }}"
```

---

## Testing Your Fixes

### 1. Test Normal Input
```bash
curl -X POST http://localhost:5678/webhook/create-task \
  -H "Content-Type: application/json" \
  -d '{"title": "Normal Task", "description": "Test"}'
```

### 2. Test SQL Injection Attempt
```bash
curl -X POST http://localhost:5678/webhook/create-task \
  -H "Content-Type: application/json" \
  -d '{"title": "Task'\'')); DROP TABLE tasks; --", "description": "Evil"}'
```

**Expected**: The malicious SQL should be stored as literal text, NOT executed.

### 3. Verify in Database
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT title FROM tasks ORDER BY created_at DESC LIMIT 1;"
```

**Expected Output**:
```
                     title
-----------------------------------------------
 Task')); DROP TABLE tasks; --
```

If you see this, the injection was properly escaped! ✅

---

## Migration Checklist

For each vulnerable workflow:

- [ ] Identify all `executeQuery` operations
- [ ] Determine operation type (INSERT/UPDATE/SELECT)
- [ ] Replace with appropriate operation (`insert`, `update`, `select`)
- [ ] Use `defineBelow` mapping mode
- [ ] Map each field individually
- [ ] Handle NULL values with `|| null`
- [ ] Test with normal input
- [ ] Test with SQL injection attempt
- [ ] Verify data in database
- [ ] Update workflow name to indicate "SECURE" version
- [ ] Document changes in workflow description

---

## Priority Order for Fixes

### 🔴 CRITICAL (Fix Immediately):
1. **19-food-log.json** - ✅ Already fixed
2. **09-store-chat-turn.json** - Stores user conversations
3. **07-watch-vault.json** - Handles file content
4. **01-create-reminder.json** - User-facing create endpoint
5. **02-create-task.json** - User-facing create endpoint

### 🟡 HIGH (Fix This Week):
6. **03-create-event.json**
7. **13-todoist-sync.json**
8. **14-google-calendar-sync.json**
9. **06-expand-recurring-tasks.json**
10. **18-scheduled-vault-sync.json**

### 🟢 MEDIUM (Fix This Month):
11. **04-fire-reminders.json** - Lower risk (UUID only)
12. **11-enrich-memories.json**
13. **12-sync-memory-to-vault.json**
14. **15-watch-documents.json**

---

## Automated Testing Script

Create `/scripts/test_sql_injection.sh`:

```bash
#!/bin/bash
# Test all workflows for SQL injection vulnerabilities

WEBHOOKS=(
  "create-reminder"
  "create-task"
  "create-event"
  "log-food"
)

PAYLOAD='{"title":"Test'\'')); DROP TABLE tasks; --","description":"Evil"}'

for webhook in "${WEBHOOKS[@]}"; do
  echo "Testing $webhook..."
  curl -X POST "http://localhost:5678/webhook/$webhook" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"
  echo ""
done
```

---

## Questions?

See `SECURITY_AUDIT_FINDINGS.md` for detailed vulnerability analysis.

---

**Remember**: Even with Tailscale/Cloudflare Tunnel, defense-in-depth is important. Fix these vulnerabilities to protect against:
- Compromised devices on your Tailscale network
- Misconfigured firewall rules
- Future changes to your network architecture
- Accidental exposure

**SQL injection is the #1 web vulnerability. Fix it now!** 🔒
