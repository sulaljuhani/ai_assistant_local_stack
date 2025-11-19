# API Documentation

Complete reference for all webhook endpoints in the AI Assistant Local Stack.

## Base URL

```
http://localhost:5678/webhook/
```

## Authentication

Currently, no authentication is required for localhost deployment. For production deployments, implement n8n's built-in authentication or add API key validation.

---

## Table of Contents

1. [Reminders](#reminders)
2. [Tasks](#tasks)
3. [Events](#events)
4. [Memory](#memory)
5. [Food Log](#food-log)
6. [File Operations](#file-operations)
7. [Import](#import)

---

## Reminders

### Create Reminder

Create a new reminder with optional category and priority.

**Endpoint**: `POST /webhook/create-reminder`

**Request Body**:
```json
{
  "title": "string (required, 1-200 chars)",
  "description": "string (optional, max 1000 chars)",
  "remind_at": "datetime (required, ISO 8601)",
  "priority": "string (optional, enum: low|medium|high, default: medium)",
  "category": "string (optional, max 50 chars, default: General)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "reminder": {
    "id": "uuid",
    "title": "Call dentist",
    "remind_at": "2025-12-01T10:00:00Z"
  }
}
```

**Validation Error** (400 Bad Request):
```json
{
  "success": false,
  "error": "Validation failed",
  "errors": [
    {
      "field": "title",
      "message": "Title is required and must be a string"
    },
    {
      "field": "remind_at",
      "message": "Remind at must be a valid date/time"
    }
  ]
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/create-reminder \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Call dentist",
    "remind_at": "2025-12-01T10:00:00Z",
    "priority": "high",
    "description": "Schedule teeth cleaning appointment"
  }'
```

---

## Tasks

### Create Task

Create a new task with optional due date and priority.

**Endpoint**: `POST /webhook/create-task`

**Request Body**:
```json
{
  "title": "string (required, 1-200 chars)",
  "description": "string (optional, max 2000 chars)",
  "due_date": "date (optional, YYYY-MM-DD)",
  "priority": "integer (optional, 0-3, default: 1)",
  "category": "string (optional, max 50 chars)",
  "is_recurring": "boolean (optional, default: false)",
  "recurrence_rule": "string (optional, cron expression)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "task": {
    "id": "uuid",
    "title": "Write documentation",
    "due_date": "2025-12-01",
    "priority": 2,
    "status": "pending"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/create-task \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write documentation",
    "description": "Complete API docs for all endpoints",
    "due_date": "2025-12-01",
    "priority": 2,
    "category": "Work"
  }'
```

---

## Events

### Create Event

Create a new calendar event with start/end times.

**Endpoint**: `POST /webhook/create-event`

**Request Body**:
```json
{
  "title": "string (required, 1-200 chars)",
  "description": "string (optional, max 2000 chars)",
  "start_time": "datetime (required, ISO 8601)",
  "end_time": "datetime (optional, ISO 8601)",
  "location": "string (optional, max 200 chars)",
  "attendees": "array<string> (optional, email addresses)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "event": {
    "id": "uuid",
    "title": "Team Meeting",
    "start_time": "2025-12-01T14:00:00Z",
    "end_time": "2025-12-01T15:00:00Z",
    "location": "Conference Room A"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/create-event \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Meeting",
    "start_time": "2025-12-01T14:00:00Z",
    "end_time": "2025-12-01T15:00:00Z",
    "location": "Conference Room A",
    "description": "Weekly team standup"
  }'
```

---

## Memory

### Store Chat Turn

Store a chat message/turn for long-term memory with OpenMemory integration.

**Endpoint**: `POST /webhook/store-chat-turn`

**Request Body**:
```json
{
  "content": "string (required)",
  "conversation_id": "string (required)",
  "conversation_title": "string (optional)",
  "source": "string (optional, default: chat)",
  "salience_score": "number (optional, 0.0-1.0, default: 0.5)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "memory_id": "uuid",
  "sectors": ["semantic", "episodic"]
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/store-chat-turn \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I prefer using dark mode for coding",
    "conversation_id": "conv-123",
    "conversation_title": "Development Preferences",
    "salience_score": 0.8
  }'
```

### Search Memories

Search stored memories using vector similarity with optional LLM summarization.

**Endpoint**: `POST /webhook/search-memories`

**Request Body**:
```json
{
  "query": "string (required)",
  "limit": "integer (optional, default: 10, max: 50)",
  "summarize": "boolean (optional, default: false)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "query": "coding preferences",
  "results_count": 3,
  "memories": [
    {
      "memory_id": "uuid",
      "sector": "semantic",
      "content": "I prefer using dark mode for coding",
      "salience_score": 0.8,
      "similarity_score": 0.92
    }
  ],
  "summary": "User prefers dark mode for coding..." // If summarize=true
}
```

**Example**:
```bash
# Search without summary
curl -X POST http://localhost:5678/webhook/search-memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my coding preferences?",
    "limit": 5
  }'

# Search with LLM summary
curl -X POST http://localhost:5678/webhook/search-memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my coding preferences?",
    "limit": 5,
    "summarize": true
  }'
```

---

## Food Log

### Log Food Entry

Track food preferences and restaurant experiences.

**Endpoint**: `POST /webhook/food-log`

**Request Body**:
```json
{
  "food_name": "string (required, max 200 chars)",
  "preference": "string (required, enum: love|like|dislike|hate)",
  "location": "string (optional, max 200 chars)",
  "restaurant_name": "string (optional, max 200 chars)",
  "description": "string (optional, max 1000 chars)",
  "consumed_at": "datetime (optional, defaults to now)",
  "meal_type": "string (optional, enum: breakfast|lunch|dinner|snack)",
  "ingredients": "array<string> (optional)",
  "tags": "array<string> (optional)",
  "calories": "integer (optional)",
  "notes": "string (optional, max 500 chars)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "food_log": {
    "id": "uuid",
    "food_name": "Margherita Pizza",
    "preference": "love",
    "consumed_at": "2025-11-19T18:30:00Z"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/food-log \
  -H "Content-Type: application/json" \
  -d '{
    "food_name": "Margherita Pizza",
    "preference": "love",
    "location": "downtown",
    "restaurant_name": "Pizzeria Napoli",
    "meal_type": "dinner",
    "description": "Perfect crust, fresh mozzarella",
    "ingredients": ["dough", "tomato sauce", "mozzarella", "basil"],
    "tags": ["italian", "vegetarian"],
    "notes": "Ask for extra basil next time"
  }'
```

---

## File Operations

### Re-embed File (Vault)

Re-process and re-embed a file from your vault.

**Endpoint**: `POST /webhook/reembed-file`

**Request Body**:
```json
{
  "file_path": "string (required, absolute path)",
  "file_hash": "string (required, MD5 hash)",
  "relative_path": "string (optional, vault-relative path)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "file": "/path/to/file.md",
  "status": "embedded"
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/reembed-file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/vault/notes/project-ideas.md",
    "file_hash": "a1b2c3d4e5f6",
    "relative_path": "notes/project-ideas.md"
  }'
```

### Embed Document

Process and embed a general document (non-vault files).

**Endpoint**: `POST /webhook/embed-document`

**Request Body**:
```json
{
  "file_path": "string (required, absolute path)",
  "file_hash": "string (required, MD5 hash)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "file": "/documents/report.pdf",
  "document_id": "uuid",
  "status": "embedded"
}
```

**Example**:
```bash
curl -X POST http://localhost:5678/webhook/embed-document \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/documents/quarterly-report.pdf",
    "file_hash": "x9y8z7w6v5u4"
  }'
```

---

## Import

### Import ChatGPT Export

Import conversation history from ChatGPT export file.

**Endpoint**: `POST /webhook/import-chatgpt`

**Request Body**:
```json
{
  "file_path": "string (required, path to conversations.json)",
  "file_hash": "string (required, MD5 hash)"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "conversations_imported": 15,
  "messages_imported": 142
}
```

### Import Claude Export

Import conversation history from Claude export file.

**Endpoint**: `POST /webhook/import-claude`

**Request Body**:
```json
{
  "file_path": "string (required, path to export.json)",
  "file_hash": "string (required, MD5 hash)"
}
```

### Import Gemini Export

Import conversation history from Gemini export file.

**Endpoint**: `POST /webhook/import-gemini`

**Request Body**:
```json
{
  "file_path": "string (required, path to export.json)",
  "file_hash": "string (required, MD5 hash)"
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request

Invalid input data or validation failure.

```json
{
  "success": false,
  "error": "Validation failed",
  "errors": [
    {
      "field": "field_name",
      "message": "Error description"
    }
  ]
}
```

### 500 Internal Server Error

Server-side error during processing.

```json
{
  "success": false,
  "error": "Internal server error",
  "message": "Error description"
}
```

### 503 Service Unavailable

Required service (PostgreSQL, Ollama, Qdrant) is unavailable.

```json
{
  "success": false,
  "error": "Service unavailable",
  "message": "Cannot connect to database"
}
```

---

## Data Types

### Date/Time Format

All datetime fields accept ISO 8601 format:

```
2025-12-01T14:30:00Z        # UTC timezone
2025-12-01T14:30:00-05:00   # With timezone offset
2025-12-01                  # Date only (midnight UTC)
```

### Priority Levels

**Tasks** (integer 0-3):
- `0` - Low priority
- `1` - Normal priority (default)
- `2` - High priority
- `3` - Urgent priority

**Reminders** (string enum):
- `low` - Low importance
- `medium` - Medium importance (default)
- `high` - High importance

### UUID Format

All IDs use UUID v4 format:
```
00000000-0000-0000-0000-000000000001
```

---

## Rate Limiting

Currently, no rate limiting is enforced for localhost deployment. For production:

- Consider implementing rate limiting per IP
- Use n8n's built-in rate limiting features
- Add Redis-based rate limiting for distributed setups

---

## Versioning

Current API version: `v1`

The API follows semantic versioning:
- **Major**: Breaking changes (v1 → v2)
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, backward compatible

---

## Best Practices

### 1. Include Descriptive Titles

Always provide clear, descriptive titles for reminders/tasks/events:

```json
// ✅ Good
{"title": "Review Q4 budget report with finance team"}

// ❌ Bad
{"title": "Meeting"}
```

### 2. Use Appropriate Salience Scores

For memory storage, use salience scores that reflect importance:

- `0.9-1.0` - Critical facts, strong preferences
- `0.7-0.8` - Important information, clear preferences
- `0.5-0.6` - Moderate importance (default)
- `0.3-0.4` - Low importance, temporary notes
- `0.0-0.2` - Trivial information

### 3. Provide Context in Memory Content

Include enough context for future retrieval:

```json
// ✅ Good
{
  "content": "I prefer using VSCode with Vim keybindings for Python development. Dark+ theme with Fira Code font."
}

// ❌ Bad
{
  "content": "VSCode"
}
```

### 4. Use Consistent Date Formats

Always use ISO 8601 format with timezone information:

```json
// ✅ Good
"remind_at": "2025-12-01T14:30:00Z"

// ⚠️ Acceptable
"remind_at": "2025-12-01T14:30:00-05:00"

// ❌ Bad
"remind_at": "12/01/2025 2:30 PM"
```

---

## Testing

Use the provided test script to verify endpoints:

```bash
# Test all webhooks
./tests/test-webhooks.sh

# Test specific endpoint
./tests/test-webhooks.sh reminder

# Verbose mode
VERBOSE=1 ./tests/test-webhooks.sh
```

See [Testing Documentation](../tests/README.md) for details.

---

## Related Documentation

- [Phase 3 Implementation](./PHASE_3_IMPLEMENTATION.md) - Input validation patterns
- [Testing Guide](../tests/README.md) - Test suite documentation
- [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common API issues
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Setup instructions
