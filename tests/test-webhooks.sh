#!/bin/bash
# =============================================================================
# API Testing Script
# =============================================================================
# Purpose: Test FastAPI/LangGraph endpoints with sample data
# Usage: ./tests/test-webhooks.sh [test_name]
# =============================================================================

# Configuration
API_URL="${API_URL:-http://localhost:8080}"
VERBOSE="${VERBOSE:-0}"
DEFAULT_USER_ID="${DEFAULT_USER_ID:-00000000-0000-0000-0000-000000000001}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Reusable response holders
RESPONSE_BODY=""
RESPONSE_STATUS=""

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
}

print_test() {
    echo ""
    echo "Testing: $1"
    echo "------------------------------------------------------------------------"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    if [ "$VERBOSE" -eq 1 ] && [ -n "$2" ]; then
        echo "  Response: $2"
    fi
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

call_endpoint() {
    local method=$1
    local path=$2
    local data=$3

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$path")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$path")
    fi

    if [ -z "$response" ]; then
        RESPONSE_BODY=""
        RESPONSE_STATUS=""
        return 1
    fi

    RESPONSE_STATUS=$(echo "$response" | tail -n1)
    RESPONSE_BODY=$(echo "$response" | head -n-1)
    return 0
}

test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local expected_status=${4:-200}
    local test_name=$5

    call_endpoint "$method" "$path" "$data"

    if [ -z "$RESPONSE_STATUS" ]; then
        fail "$test_name (Expected $expected_status, got connection error)" "Connection failed to $API_URL$path"
        return 1
    fi

    if [ "$RESPONSE_STATUS" -eq "$expected_status" ]; then
        pass "$test_name (HTTP $RESPONSE_STATUS)"
        if [ "$VERBOSE" -eq 1 ]; then
            echo "  Response: $RESPONSE_BODY"
        fi
        return 0
    else
        fail "$test_name (Expected $expected_status, got $RESPONSE_STATUS)" "$RESPONSE_BODY"
        return 1
    fi
}

expect_json_field() {
    local json="$1"
    local field="$2"
    JSON_IN="$json" FIELD_IN="$field" python - <<'PY' 2>/dev/null
import json, os, sys

json_in = os.environ.get("JSON_IN", "")
field = os.environ.get("FIELD_IN", "")

try:
    data = json.loads(json_in)
    for part in field.split("."):
        if isinstance(data, list):
            data = data[int(part)]
        else:
            data = data.get(part)
    if data is None:
        sys.exit(1)
    print(data)
except Exception:
    sys.exit(1)
PY
}

# =============================================================================
# Test Cases
# =============================================================================

test_create_reminder() {
    print_test "Create Reminder"

    # Valid reminder
    test_endpoint "POST" "/api/reminders/create" \
        '{"title": "Test Reminder", "remind_at": "2025-12-01T10:00:00", "priority": 2}' \
        200 \
        "Valid reminder creation"

    # Invalid reminder (missing title)
    test_endpoint "POST" "/api/reminders/create" \
        '{"remind_at": "2025-12-01T10:00:00"}' \
        422 \
        "Invalid reminder (missing title)"

    # Invalid reminder (invalid priority)
    test_endpoint "POST" "/api/reminders/create" \
        '{"title": "Test", "remind_at": "2025-12-01T10:00:00", "priority": 99}' \
        422 \
        "Invalid reminder (invalid priority)"
}

test_create_task() {
    print_test "Create Task"

    # Valid task
    test_endpoint "POST" "/api/tasks/create" \
        '{"title": "Test Task", "due_date": "2025-12-01T10:00:00", "priority": 2}' \
        200 \
        "Valid task creation"

    # Task without due date (optional)
    test_endpoint "POST" "/api/tasks/create" \
        '{"title": "Task without due date"}' \
        200 \
        "Task without due date"
}

test_create_event() {
    print_test "Create Event"

    # Valid event
    test_endpoint "POST" "/api/events/create" \
        '{"title": "Team Meeting", "start_time": "2025-12-01T14:00:00", "end_time": "2025-12-01T15:00:00"}' \
        200 \
        "Valid event creation"

    # Event with location
    test_endpoint "POST" "/api/events/create" \
        '{"title": "Conference", "start_time": "2025-12-01T09:00:00", "end_time": "2025-12-01T17:00:00", "location": "Convention Center"}' \
        200 \
        "Event with location"
}

test_store_chat_turn() {
    print_test "Store Chat Turn"

    # Valid chat turn
    test_endpoint "POST" "/api/memory/store" \
        "{\"user_id\": \"${DEFAULT_USER_ID}\", \"role\": \"user\", \"content\": \"This is a test message\", \"conversation_id\": \"00000000-0000-0000-0000-000000000002\", \"conversation_title\": \"Test Conversation\"}" \
        200 \
        "Valid chat turn storage"
}

test_search_memories() {
    print_test "Search Memories"

    # Search without summarization
    test_endpoint "POST" "/api/memory/search" \
        "{\"query\": \"test query\", \"limit\": 5, \"user_id\": \"${DEFAULT_USER_ID}\"}" \
        200 \
        "Memory search without summary"

    # Search with summarization
    test_endpoint "POST" "/api/memory/search" \
        "{\"query\": \"test query\", \"limit\": 5, \"summarize\": true, \"user_id\": \"${DEFAULT_USER_ID}\"}" \
        200 \
        "Memory search with summary"
}

# =============================================================================
# CRUD & Pipeline Tests
# =============================================================================

test_task_crud() {
    print_test "Task CRUD Flow"

    # Create
    test_endpoint "POST" "/api/tasks/create" \
        '{"title": "End-to-end Task", "priority": 2, "tags": ["smoke"]}' \
        200 \
        "Create task (CRUD)"
    task_id=$(expect_json_field "$RESPONSE_BODY" "id")

    if [ -z "$task_id" ]; then
        fail "Extract task id after create" "$RESPONSE_BODY"
        return
    fi

    # Get detail
    test_endpoint "GET" "/api/tasks/$task_id" "" 200 "Get task detail"

    # Update status and title
    test_endpoint "PUT" "/api/tasks/$task_id" \
        '{"status": "done", "title": "End-to-end Task Updated"}' \
        200 \
        "Update task status"

    # List filter by status=done
    test_endpoint "GET" "/api/tasks?status=done&limit=5" "" 200 "List tasks filtered"

    # Delete
    test_endpoint "DELETE" "/api/tasks/$task_id" "" 200 "Delete task"
}

test_reminder_crud() {
    print_test "Reminder CRUD Flow"

    # Create future reminder
    test_endpoint "POST" "/api/reminders/create" \
        '{"title": "End-to-end Reminder", "remind_at": "2025-12-01T10:00:00", "priority": 2}' \
        200 \
        "Create reminder (CRUD)"
    reminder_id=$(expect_json_field "$RESPONSE_BODY" "id")
    if [ -z "$reminder_id" ]; then
        fail "Extract reminder id after create" "$RESPONSE_BODY"
        return
    fi

    # Get detail
    test_endpoint "GET" "/api/reminders/$reminder_id" "" 200 "Get reminder detail"

    # Update completion
    test_endpoint "PUT" "/api/reminders/$reminder_id" \
        '{"is_completed": true, "title": "Reminder Updated"}' \
        200 \
        "Update reminder status"

    # List today (should still succeed even if date not today)
    test_endpoint "GET" "/api/reminders/today?limit=5" "" 200 "List reminders today"

    # Delete
    test_endpoint "DELETE" "/api/reminders/$reminder_id" "" 200 "Delete reminder"
}

test_event_crud() {
    print_test "Event CRUD Flow"

    # Create event
    test_endpoint "POST" "/api/events/create" \
        '{"title": "End-to-end Event", "start_time": "2025-12-05T10:00:00", "end_time": "2025-12-05T11:00:00", "attendees": ["a@example.com"]}' \
        200 \
        "Create event (CRUD)"
    event_id=$(expect_json_field "$RESPONSE_BODY" "id")
    if [ -z "$event_id" ]; then
        fail "Extract event id after create" "$RESPONSE_BODY"
        return
    fi

    # Get detail
    test_endpoint "GET" "/api/events/$event_id" "" 200 "Get event detail"

    # Update location
    test_endpoint "PUT" "/api/events/$event_id" \
        '{"location": "Updated Room", "attendees": ["a@example.com", "b@example.com"]}' \
        200 \
        "Update event location/attendees"

    # List week view
    test_endpoint "GET" "/api/events/week?limit=5" "" 200 "List events (week)"

    # Delete
    test_endpoint "DELETE" "/api/events/$event_id" "" 200 "Delete event"
}

test_memory_pipeline() {
    print_test "OpenMemory Pipeline"

    conversation_id="00000000-0000-0000-0000-00000000abcd"

    # Store chat turn ensures vector write + DB upsert
    test_endpoint "POST" "/api/memory/store" \
        "{\"user_id\": \"${DEFAULT_USER_ID}\", \"role\": \"user\", \"content\": \"Memory pipeline test\", \"conversation_id\": \"${conversation_id}\", \"conversation_title\": \"Pipeline\"}" \
        200 \
        "Store memory"

    # Search with filters
    test_endpoint "POST" "/api/memory/search" \
        "{\"query\": \"pipeline test\", \"limit\": 3, \"user_id\": \"${DEFAULT_USER_ID}\", \"conversation_id\": \"${conversation_id}\"}" \
        200 \
        "Search memory with filters"

    # Conversations listing
    test_endpoint "GET" "/api/memory/conversations?user_id=${DEFAULT_USER_ID}" "" 200 "List conversations"

    # Stats endpoint
    test_endpoint "GET" "/api/memory/stats" "" 200 "Memory stats"
}

# =============================================================================
# Documents & Vault & Imports
# =============================================================================

test_documents_embed_and_search() {
    print_test "Documents Embed & Search"
    tmp_file=$(mktemp /tmp/ai-stack-doc.XXXX.txt)
    echo "This is a knowledge base test document" > "$tmp_file"

    # Embed document via upload endpoint (container handles temp path)
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -F "file=@${tmp_file}" \
        -F "collection_name=knowledge_base" \
        "$API_URL/api/documents/upload-and-embed")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    RESPONSE_STATUS=$http_code
    RESPONSE_BODY=$body
    if [ "$http_code" -eq 200 ]; then
        pass "Embed document (HTTP $http_code)"
        if [ "$VERBOSE" -eq 1 ]; then
            echo "  Response: $body"
        fi
    else
        fail "Embed document (Expected 200, got $http_code)" "$body"
    fi

    # Search document collection
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -F "query=knowledge base test" \
        -F "collection_name=knowledge_base" \
        "$API_URL/api/documents/search")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    RESPONSE_STATUS=$http_code
    RESPONSE_BODY=$body
    if [ "$http_code" -eq 200 ]; then
        pass "Search documents collection (HTTP $http_code)"
        if [ "$VERBOSE" -eq 1 ]; then
            echo "  Response: $body"
        fi
    else
        fail "Search documents collection (Expected 200, got $http_code)" "$body"
    fi

    rm -f "$tmp_file"
}

test_vault_reembed_and_status() {
    print_test "Vault Re-embed & Status"
    # Create file inside container so path is accessible
    vault_tmp="/tmp/ai-stack-vault-file.md"
    docker exec langgraph-agents sh -c "echo '# Vault file' > ${vault_tmp}"

    # Re-embed vault file (force)
    test_endpoint "POST" "/api/vault/reembed" \
        "{\"file_path\": \"${vault_tmp}\", \"force\": true}" \
        200 \
        "Re-embed vault file"

    # Vault status
    test_endpoint "GET" "/api/vault/status" "" 200 "Vault status"
}

test_imports_claude() {
    print_test "Imports: Claude Export"
    tmp_json=$(mktemp /tmp/ai-stack-claude.XXXX.json)
    cat > "$tmp_json" <<'JSON'
{
  "conversations": [
    {
      "uuid": "import-conv-1",
      "uuid": "00000000-0000-0000-0000-00000000c0fe",
      "name": "Imported Conversation",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "chat_messages": [
        {
          "uuid": "msg-1",
          "text": "Hello from Claude export",
          "sender": "human",
          "created_at": "2024-01-01T00:00:00Z"
        }
      ]
    }
  ]
}
JSON

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -F "file=@${tmp_json}" \
        -F "user_id=${DEFAULT_USER_ID}" \
        -F "default_salience=0.3" \
        "$API_URL/api/import/claude")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    RESPONSE_STATUS=$http_code
    RESPONSE_BODY=$body

    if [ "$http_code" -eq 200 ]; then
        pass "Import Claude export (HTTP $http_code)"
        if [ "$VERBOSE" -eq 1 ]; then
            echo "  Response: $body"
        fi
    else
        fail "Import Claude export (Expected 200, got $http_code)" "$body"
    fi

    rm -f "$tmp_json"
}

# =============================================================================
# Validation & Failure-path Tests
# =============================================================================

test_validation_errors() {
    print_test "Validation & Error Handling"

    # Transport/format: malformed JSON should yield 400
    test_endpoint "POST" "/api/tasks/create" \
        '{"title": "Bad JSON",' \
        400 \
        "Invalid JSON returns HTTP 400"

    # Transport/format: bad query param type should yield 400
    test_endpoint "GET" "/api/tasks?limit=not-a-number" \
        "" \
        400 \
        "Invalid query param returns HTTP 400"

    # Domain validation: reminder in the past should yield 422
    test_endpoint "POST" "/api/reminders/create" \
        "{\"title\": \"Past Reminder\", \"remind_at\": \"2000-01-01T00:00:00\"}" \
        422 \
        "Domain validation returns HTTP 422"

    # Domain validation: event end before start should yield 422
    test_endpoint "POST" "/api/events/create" \
        "{\"title\": \"Invalid Event\", \"start_time\": \"2025-12-02T10:00:00\", \"end_time\": \"2025-12-02T09:00:00\"}" \
        422 \
        "Event end before start returns HTTP 422"
}

# =============================================================================
# Health Check Tests
# =============================================================================

test_health_checks() {
    print_test "System Health Checks"

    # FastAPI health
    test_endpoint "GET" "/health" "" 200 "FastAPI health endpoint"

    # Quick DB-backed read should fail if Postgres/Redis are down
    test_endpoint "GET" "/api/tasks?limit=1" "" 200 "Tasks API list (DB available)"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "AI Stack Webhook Testing Suite"
    echo "API URL: $API_URL"
    echo "Verbose: $VERBOSE"

    # Parse arguments
    TEST_NAME=${1:-"all"}

    # Run tests based on argument
    case $TEST_NAME in
        "create-reminder"|"reminder")
            test_create_reminder
            ;;
        "create-task"|"task")
            test_create_task
            ;;
        "create-event"|"event")
            test_create_event
            ;;
        "task-crud")
            test_task_crud
            ;;
        "reminder-crud")
            test_reminder_crud
            ;;
        "event-crud")
            test_event_crud
            ;;
        "memory-pipeline")
            test_memory_pipeline
            ;;
        "documents")
            test_documents_embed_and_search
            ;;
        "vault")
            test_vault_reembed_and_status
            ;;
        "imports")
            test_imports_claude
            ;;
        "store-chat-turn"|"chat")
            test_store_chat_turn
            ;;
        "search-memories"|"search")
            test_search_memories
            ;;
        "validation")
            test_validation_errors
            ;;
        "health")
            test_health_checks
            ;;
        "all")
            test_health_checks
            test_create_reminder
            test_create_task
            test_create_event
            test_task_crud
            test_reminder_crud
            test_event_crud
            test_store_chat_turn
            test_search_memories
            test_memory_pipeline
            test_documents_embed_and_search
            test_vault_reembed_and_status
            test_imports_claude
            test_validation_errors
            ;;
        *)
            echo "Unknown test: $TEST_NAME"
            echo ""
            echo "Available tests:"
            echo "  reminder, task, event, task-crud, reminder-crud, event-crud, memory-pipeline, documents, vault, imports, chat, search, validation, health, all"
            exit 1
            ;;
    esac

    # Print summary
    print_header "Test Summary"
    echo "Tests run: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
