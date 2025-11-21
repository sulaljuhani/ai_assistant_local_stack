# Testing Infrastructure

This directory contains testing scripts and utilities for the AI Assistant Local Stack.

## Quick Start

```bash
# Run all FastAPI endpoint tests
./tests/test-webhooks.sh

# Run a specific test group
./tests/test-webhooks.sh reminder

# Run with verbose output
VERBOSE=1 ./tests/test-webhooks.sh
```

## Available Tests

### FastAPI Endpoint Tests (`test-webhooks.sh`)

Targets the native FastAPI/LangGraph APIs (no n8n). Health checks fail if services are not running.

**Individual Tests:**
- `reminder` - `/api/reminders/create`
- `task` - `/api/tasks/create`
- `event` - `/api/events/create`
- `chat` - `/api/memory/store`
- `search` - `/api/memory/search`
- `task-crud` - create/get/update/list/delete task
- `reminder-crud` - create/get/update/list/delete reminder
- `event-crud` - create/get/update/list/delete event
- `memory-pipeline` - store + search + stats/conversations for OpenMemory
- `documents` - document embed + semantic search (knowledge_base)
- `vault` - vault re-embed + status
- `imports` - Claude export import path
- `validation` - transport vs domain validation (400 vs 422)
- `health` - `/health` and `/api/tasks` (DB availability)
- `all` - Run every test (default)

**Usage:**
```bash
# Test specific endpoint
./tests/test-webhooks.sh reminder

# Test all endpoints
./tests/test-webhooks.sh all

# Use custom API URL (default http://localhost:8080)
API_URL=http://localhost:8080 ./tests/test-webhooks.sh

# Verbose mode (shows response bodies)
VERBOSE=1 ./tests/test-webhooks.sh reminder
```

**Example Output:**
```
========================================================================
AI Stack Webhook Testing Suite
========================================================================
API URL: http://localhost:8080
Verbose: 0

Testing: Create Reminder
------------------------------------------------------------------------
✓ PASS: Valid reminder creation (HTTP 200)
✓ PASS: Invalid reminder (missing title) (HTTP 400)
✓ PASS: Invalid reminder (invalid priority) (HTTP 400)

========================================================================
Test Summary
========================================================================
Tests run: 3
Passed: 3
Failed: 0

All tests passed!
```

## Test Coverage

- ✅ FastAPI routing and validation for core CRUD endpoints (tasks, reminders, events)
- ✅ Memory storage/search endpoints with sample payloads
- ✅ CRUD regression flows for tasks, reminders, events
- ✅ OpenMemory pipeline touchpoints (store, search, stats, conversations)
- ✅ Documents embed/search, vault re-embed/status, Claude import path
- ✅ Validation split for transport/format (400) vs domain (422) errors
- ✅ Health checks fail when FastAPI or backing services (e.g., Postgres) are unavailable

## Adding New Tests

To add tests for a new API endpoint:

1. **Add test function** to `test-webhooks.sh`:
   ```bash
   test_my_endpoint() {
       print_test "My Endpoint"
       test_endpoint "POST" "/api/my-endpoint" \
           '{"field": "value"}' \
           200 \
           "Valid request"
   }
   ```

2. **Add to main case statement**:
   ```bash
   case $TEST_NAME in
       # ...
       "my-endpoint")
           test_my_endpoint
           ;;
       "all")
           # ...
           test_my_endpoint
           ;;
   esac
   ```

3. **Run your test**:
   ```bash
   ./tests/test-webhooks.sh my-endpoint
   ```

## Continuous Integration

These tests can be integrated into CI/CD pipelines once the FastAPI stack is running:

```yaml
# Example GitHub Actions workflow
- name: Run API tests
  run: |
    docker-compose up -d
    sleep 10  # Wait for services
    ./tests/test-webhooks.sh
    exit_code=$?
    docker-compose down
    exit $exit_code
```

## Troubleshooting

### Tests fail with "connection error"

**Problem**: FastAPI is not running or not accessible on `API_URL`.

**Solution**:
```bash
curl http://localhost:8080/health
docker ps | grep langgraph-agents
```

### Tests return 500 errors for CRUD endpoints

**Problem**: Backing services (Postgres/Redis/Qdrant) are not available.

**Solution**: Start required containers and rerun migrations:
```bash
docker ps
cd migrations && ./run-migrations.sh
```

## Related Documentation

- [API Documentation](../docs/API_DOCUMENTATION.md) - Endpoint specifications
- [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) - Common issues
