# Testing Infrastructure

This directory contains testing scripts and utilities for the AI Assistant Local Stack.

## Quick Start

```bash
# Run all webhook tests
./tests/test-webhooks.sh

# Run specific test
./tests/test-webhooks.sh reminder

# Run with verbose output
VERBOSE=1 ./tests/test-webhooks.sh
```

## Available Tests

### Webhook Tests (`test-webhooks.sh`)

Tests all webhook endpoints with valid and invalid data.

**Individual Tests:**
- `reminder` - Create reminder webhook
- `task` - Create task webhook
- `event` - Create event webhook
- `chat` - Store chat turn webhook
- `search` - Search memories webhook
- `food` - Food log webhook
- `health` - System health checks
- `all` - Run all tests (default)

**Usage:**
```bash
# Test specific endpoint
./tests/test-webhooks.sh reminder

# Test all endpoints
./tests/test-webhooks.sh all

# Use custom n8n URL
N8N_URL=http://localhost:5678 ./tests/test-webhooks.sh

# Verbose mode (shows response bodies)
VERBOSE=1 ./tests/test-webhooks.sh reminder
```

**Example Output:**
```
========================================================================
AI Stack Webhook Testing Suite
========================================================================
n8n URL: http://localhost:5678
Verbose: 0

Testing: Create Reminder Webhook
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

### Phase 3 Validation Tests

Workflow 01 (Create Reminder) includes inline validation. The test suite verifies:

- ✅ Valid inputs return 200 OK
- ✅ Missing required fields return 400 Bad Request
- ✅ Invalid enum values return 400 Bad Request
- ✅ Field length constraints are enforced
- ✅ Date/time parsing validates correctly

### Integration Tests

The test scripts verify end-to-end functionality:

1. **Webhook accessibility** - n8n responds to HTTP requests
2. **Data validation** - Invalid inputs are rejected
3. **Database operations** - Records are created correctly
4. **Error handling** - Errors return proper status codes

## Adding New Tests

To add tests for a new webhook:

1. **Add test function** to `test-webhooks.sh`:
   ```bash
   test_my_webhook() {
       print_test "My Webhook"
       test_endpoint "my-webhook" \
           '{"field": "value"}' \
           200 \
           "Valid request"
   }
   ```

2. **Add to main case statement**:
   ```bash
   case $TEST_NAME in
       # ...
       "my-webhook")
           test_my_webhook
           ;;
       "all")
           # ...
           test_my_webhook
           ;;
   esac
   ```

3. **Run your test**:
   ```bash
   ./tests/test-webhooks.sh my-webhook
   ```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run webhook tests
  run: |
    docker-compose up -d
    sleep 10  # Wait for services
    ./tests/test-webhooks.sh
    exit_code=$?
    docker-compose down
    exit $exit_code
```

## Troubleshooting

### Tests fail with "Connection refused"

**Problem**: n8n is not running or not accessible

**Solution**:
```bash
# Check if n8n is running
docker ps | grep n8n

# Start n8n if needed
docker-compose up -d n8n-ai-stack

# Verify n8n is accessible
curl http://localhost:5678
```

### Tests fail with 404 Not Found

**Problem**: Webhook workflows are not active

**Solution**:
1. Open n8n UI: http://localhost:5678
2. Check that workflows are activated (green toggle)
3. Verify webhook paths match test script

### Tests timeout

**Problem**: Services are starting up or overloaded

**Solution**:
```bash
# Wait longer for services to start
sleep 30

# Check service health
docker-compose ps
docker-compose logs n8n-ai-stack
```

## Future Enhancements

Potential additions to the testing infrastructure:

1. **Unit tests** for validation logic
2. **Performance tests** for vector search
3. **Load tests** for concurrent requests
4. **Database state verification** after operations
5. **Rollback tests** for error scenarios
6. **End-to-end tests** with real AI models

## Related Documentation

- [Phase 3 Implementation](../docs/PHASE_3_IMPLEMENTATION.md) - Validation patterns
- [API Documentation](../docs/API_DOCUMENTATION.md) - Webhook specifications
- [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) - Common issues
