#!/bin/bash
# =============================================================================
# Webhook Testing Script
# =============================================================================
# Purpose: Test all webhook endpoints with sample data
# Usage: ./tests/test-webhooks.sh [webhook_name]
# =============================================================================

set -e  # Exit on error

# Configuration
N8N_URL="${N8N_URL:-http://localhost:5678}"
VERBOSE="${VERBOSE:-0}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

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
    if [ "$VERBOSE" -eq 1 ]; then
        echo "  Response: $2"
    fi
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

test_endpoint() {
    local endpoint=$1
    local data=$2
    local expected_status=${3:-200}
    local test_name=$4

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$N8N_URL/webhook/$endpoint")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq "$expected_status" ]; then
        pass "$test_name (HTTP $http_code)"
        if [ "$VERBOSE" -eq 1 ]; then
            echo "  Response: $body"
        fi
        return 0
    else
        fail "$test_name (Expected $expected_status, got $http_code)" "$body"
        return 1
    fi
}

# =============================================================================
# Test Cases
# =============================================================================

test_create_reminder() {
    print_test "Create Reminder Webhook"

    # Valid reminder
    test_endpoint "create-reminder" \
        '{"title": "Test Reminder", "remind_at": "2025-12-01T10:00:00Z", "priority": "high"}' \
        200 \
        "Valid reminder creation"

    # Invalid reminder (missing title)
    test_endpoint "create-reminder" \
        '{"remind_at": "2025-12-01T10:00:00Z"}' \
        400 \
        "Invalid reminder (missing title)"

    # Invalid reminder (invalid priority)
    test_endpoint "create-reminder" \
        '{"title": "Test", "remind_at": "2025-12-01T10:00:00Z", "priority": "invalid"}' \
        400 \
        "Invalid reminder (invalid priority)"
}

test_create_task() {
    print_test "Create Task Webhook"

    # Valid task
    test_endpoint "create-task" \
        '{"title": "Test Task", "due_date": "2025-12-01", "priority": 2}' \
        200 \
        "Valid task creation"

    # Task without due date (optional)
    test_endpoint "create-task" \
        '{"title": "Task without due date"}' \
        200 \
        "Task without due date"
}

test_create_event() {
    print_test "Create Event Webhook"

    # Valid event
    test_endpoint "create-event" \
        '{"title": "Team Meeting", "start_time": "2025-12-01T14:00:00Z", "end_time": "2025-12-01T15:00:00Z"}' \
        200 \
        "Valid event creation"

    # Event with location
    test_endpoint "create-event" \
        '{"title": "Conference", "start_time": "2025-12-01T09:00:00Z", "end_time": "2025-12-01T17:00:00Z", "location": "Convention Center"}' \
        200 \
        "Event with location"
}

test_store_chat_turn() {
    print_test "Store Chat Turn Webhook"

    # Valid chat turn
    test_endpoint "store-chat-turn" \
        '{"content": "This is a test message", "conversation_id": "test-conv-123", "conversation_title": "Test Conversation"}' \
        200 \
        "Valid chat turn storage"
}

test_search_memories() {
    print_test "Search Memories Webhook"

    # Search without summarization
    test_endpoint "search-memories" \
        '{"query": "test query", "limit": 5}' \
        200 \
        "Memory search without summary"

    # Search with summarization
    test_endpoint "search-memories" \
        '{"query": "test query", "limit": 5, "summarize": true}' \
        200 \
        "Memory search with summary"
}

test_food_log() {
    print_test "Food Log Webhook"

    # Valid food log entry
    test_endpoint "food-log" \
        '{"food_name": "Pizza", "preference": "like", "location": "home"}' \
        200 \
        "Valid food log entry"

    # Food log with restaurant
    test_endpoint "food-log" \
        '{"food_name": "Sushi", "preference": "love", "restaurant_name": "Sushi Palace", "location": "downtown"}' \
        200 \
        "Food log with restaurant"
}

# =============================================================================
# Health Check Tests
# =============================================================================

test_health_checks() {
    print_test "System Health Checks"

    # Check n8n is running
    if curl -s -f "$N8N_URL" > /dev/null 2>&1; then
        pass "n8n is accessible"
    else
        fail "n8n is not accessible" "Cannot connect to $N8N_URL"
    fi

    # Check PostgreSQL (via n8n workflow if available)
    # This would require a health check endpoint
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "AI Stack Webhook Testing Suite"
    echo "n8n URL: $N8N_URL"
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
        "store-chat-turn"|"chat")
            test_store_chat_turn
            ;;
        "search-memories"|"search")
            test_search_memories
            ;;
        "food-log"|"food")
            test_food_log
            ;;
        "health")
            test_health_checks
            ;;
        "all")
            test_health_checks
            test_create_reminder
            test_create_task
            test_create_event
            test_store_chat_turn
            test_search_memories
            test_food_log
            ;;
        *)
            echo "Unknown test: $TEST_NAME"
            echo ""
            echo "Available tests:"
            echo "  reminder, task, event, chat, search, food, health, all"
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
