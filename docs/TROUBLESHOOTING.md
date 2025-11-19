# Troubleshooting Guide

Common issues and solutions for the AI Assistant Local Stack.

## Table of Contents

1. [Service Health](#service-health)
2. [Docker Issues](#docker-issues)
3. [Database Problems](#database-problems)
4. [n8n Workflow Issues](#n8n-workflow-issues)
5. [Memory/Vector Search](#memoryvector-search)
6. [File Sync Issues](#file-sync-issues)
7. [Performance Problems](#performance-problems)

---

## Service Health

### Check All Services

```bash
# View running services
docker-compose ps

# Check service logs
docker-compose logs --tail=50 -f

# Check specific service
docker-compose logs n8n-ai-stack
docker-compose logs postgres-ai-stack
docker-compose logs qdrant-ai-stack
docker-compose logs ollama-ai-stack
docker-compose logs openmemory-ai-stack
```

### Health Check Workflow

The system includes automated health monitoring (workflow 21):

```bash
# Check latest health status
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT * FROM health_checks ORDER BY check_time DESC LIMIT 1;"

# View failed health checks
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT * FROM health_checks WHERE all_healthy = false ORDER BY check_time DESC LIMIT 10;"
```

### Service Won't Start

**Symptom**: Service exits immediately or won't start

**Diagnosis**:
```bash
# Check for port conflicts
sudo netstat -tlnp | grep ':5678\|:5432\|:6333\|:11434\|:8080'

# Check Docker logs for errors
docker-compose logs [service-name]

# Check disk space
df -h

# Check system resources
free -h
top
```

**Common Solutions**:

1. **Port already in use**:
   ```bash
   # Find process using port
   sudo lsof -i :5678

   # Kill conflicting process or change port in docker-compose.yml
   ```

2. **Insufficient disk space**:
   ```bash
   # Clean up Docker
   docker system prune -a
   docker volume prune
   ```

3. **Memory limit reached**:
   ```bash
   # Check Docker memory limits
   docker stats

   # Increase in docker-compose.yml
   # mem_limit: 4g  # Increase as needed
   ```

---

## Docker Issues

### Container Keeps Restarting

**Symptom**: Service status shows "Restarting"

**Diagnosis**:
```bash
# View restart count and last exit code
docker ps -a | grep ai-stack

# Check logs for crash reason
docker-compose logs --tail=100 [service-name]
```

**Solutions**:

1. **Database connection failures**:
   ```bash
   # Ensure PostgreSQL is fully started
   docker-compose up -d postgres-ai-stack
   sleep 10
   docker-compose up -d
   ```

2. **Missing environment variables**:
   ```bash
   # Verify .env.local-stack exists
   cat .env.local-stack | grep -E "POSTGRES_|OLLAMA_|DEFAULT_USER"

   # Recreate containers with new env
   docker-compose down
   docker-compose up -d
   ```

3. **Corrupted container state**:
   ```bash
   # Force recreate
   docker-compose down
   docker-compose up -d --force-recreate
   ```

### Volume Permissions

**Symptom**: Permission denied errors in logs

**Solution**:
```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./data
sudo chown -R 1000:1000 ./vault

# Or run as root (not recommended for production)
# Add to docker-compose.yml:
# user: "0:0"
```

---

## Database Problems

### Cannot Connect to PostgreSQL

**Symptom**: "Connection refused" or "FATAL: database does not exist"

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Try manual connection
docker exec -it postgres-ai-stack psql -U aistack_user -d aistack

# Check PostgreSQL logs
docker-compose logs postgres-ai-stack | tail -50
```

**Solutions**:

1. **Database not initialized**:
   ```bash
   # Run migrations
   cd migrations
   ./run-migrations.sh
   ```

2. **Wrong credentials**:
   ```bash
   # Verify credentials in .env.local-stack
   cat .env.local-stack | grep POSTGRES

   # Reset password if needed
   docker exec -it postgres-ai-stack psql -U postgres -c \
     "ALTER USER aistack_user WITH PASSWORD 'your_password';"
   ```

3. **Connection pool exhausted**:
   ```bash
   # Check active connections
   docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
     "SELECT count(*) FROM pg_stat_activity;"

   # Kill long-running queries
   docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
      WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
   ```

### Migration Failures

**Symptom**: Migration script fails or tables don't exist

**Diagnosis**:
```bash
# Check which migrations have run
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT * FROM schema_migrations ORDER BY version;"

# Check for missing tables
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "\dt"
```

**Solutions**:

1. **Run specific migration**:
   ```bash
   docker exec postgres-ai-stack psql -U aistack_user -d aistack \
     -f /migrations/010_monitoring_tables.sql
   ```

2. **Reset and re-run all migrations**:
   ```bash
   # DANGER: This deletes all data
   docker-compose down -v
   docker-compose up -d postgres-ai-stack
   sleep 10
   cd migrations && ./run-migrations.sh
   ```

---

## n8n Workflow Issues

### Workflows Not Executing

**Symptom**: Scheduled workflows don't run or webhooks return 404

**Diagnosis**:
```bash
# Check n8n logs
docker-compose logs n8n-ai-stack | tail -100

# Verify n8n is accessible
curl http://localhost:5678

# Check workflow status in UI
open http://localhost:5678
```

**Solutions**:

1. **Workflows not activated**:
   - Open n8n UI
   - Check that workflow toggle is green (activated)
   - Save workflow after making changes

2. **Webhook path mismatch**:
   ```bash
   # Test webhook manually
   curl -X POST http://localhost:5678/webhook/create-reminder \
     -H "Content-Type: application/json" \
     -d '{"title": "Test", "remind_at": "2025-12-01T10:00:00Z"}'
   ```

3. **Environment variables not loaded**:
   ```bash
   # Restart n8n to reload env vars
   docker-compose restart n8n-ai-stack

   # Check env vars are set
   docker exec n8n-ai-stack env | grep -E "DEFAULT_USER|OLLAMA"
   ```

### Workflow Execution Errors

**Symptom**: Workflow fails with errors in n8n logs

**Common Errors**:

1. **"Cannot read property of undefined"**:
   - Check that previous node output exists
   - Use `$item(0).json` to reference first item
   - Add IF node to check for empty results

2. **"Database query failed"**:
   ```bash
   # Check PostgreSQL is accessible
   docker exec n8n-ai-stack ping -c 3 postgres-ai-stack

   # Verify credentials are correct
   # In n8n UI: Credentials → PostgreSQL → Test connection
   ```

3. **"Ollama request failed"**:
   ```bash
   # Check Ollama is running
   docker ps | grep ollama

   # Test Ollama endpoint
   curl http://localhost:11434/api/tags

   # Pull required model
   docker exec ollama-ai-stack ollama pull nomic-embed-text
   ```

---

## Memory/Vector Search

### No Search Results

**Symptom**: Memory search returns 0 results

**Diagnosis**:
```bash
# Check if memories exist
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT count(*) FROM memories;"

# Check Qdrant collection
curl http://localhost:6333/collections/memories

# Check vector count
curl http://localhost:6333/collections/memories | jq '.result.vectors_count'
```

**Solutions**:

1. **No memories stored**:
   ```bash
   # Store test memory
   curl -X POST http://localhost:5678/webhook/store-chat-turn \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Test memory for search",
       "conversation_id": "test-123"
     }'
   ```

2. **Qdrant collection not created**:
   ```bash
   # Create collection manually
   curl -X PUT http://localhost:6333/collections/memories \
     -H "Content-Type: application/json" \
     -d '{
       "vectors": {
         "size": 768,
         "distance": "Cosine"
       }
     }'
   ```

3. **Embedding dimension mismatch**:
   ```bash
   # Check embedding model dimensions
   docker exec ollama-ai-stack ollama show nomic-embed-text | grep dimensions

   # Recreate Qdrant collection with correct size (768 for nomic-embed-text)
   ```

### Slow Vector Search

**Symptom**: Search takes >5 seconds

**Diagnosis**:
```bash
# Check Qdrant stats
curl http://localhost:6333/collections/memories | jq '.'

# Check system resources
docker stats qdrant-ai-stack
```

**Solutions**:

1. **Too many vectors**:
   ```bash
   # Archive old memories
   docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
     "UPDATE memories SET is_archived = true
      WHERE created_at < NOW() - INTERVAL '90 days';"
   ```

2. **Insufficient memory**:
   - Increase Qdrant memory limit in docker-compose.yml
   - Add HNSW indexing parameters to Qdrant collection

3. **Optimize Qdrant**:
   ```bash
   # Trigger optimization
   curl -X POST http://localhost:6333/collections/memories/index
   ```

---

## File Sync Issues

### Files Not Syncing to Vault

**Symptom**: New/modified files in vault aren't indexed

**Diagnosis**:
```bash
# Check file watcher logs
docker-compose logs n8n-ai-stack | grep "watch-vault"

# Check file_sync table
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT file_path, sync_status, last_synced_at FROM file_sync ORDER BY last_synced_at DESC LIMIT 10;"

# Verify scheduled sync is running
docker-compose logs n8n-ai-stack | grep "scheduled-vault-sync"
```

**Solutions**:

1. **File watcher not running**:
   - Ensure workflow 07 (watch-vault) is activated in n8n UI
   - Check that file watcher script is running (if using external watcher)

2. **Schedule not triggering**:
   ```bash
   # Check workflow 18 schedule (should be 4:30 AM daily)
   # In n8n UI: Open workflow 18 → Check schedule trigger

   # Manually trigger sync
   # In n8n UI: Open workflow 18 → Click "Execute Workflow"
   ```

3. **File path issues**:
   ```bash
   # Verify vault path is correct
   echo $VAULT_PATH

   # Check file permissions
   ls -la /vault/path/to/file.md

   # Ensure n8n can read files
   docker exec n8n-ai-stack cat /vault/path/to/file.md
   ```

### Duplicate Embeddings

**Symptom**: Same file embedded multiple times

**Diagnosis**:
```bash
# Check for duplicate entries
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT file_path, COUNT(*) as count FROM file_sync
   GROUP BY file_path HAVING COUNT(*) > 1;"
```

**Solutions**:

1. **Remove duplicates**:
   ```sql
   -- Keep only most recent entry
   DELETE FROM file_sync a USING file_sync b
   WHERE a.file_path = b.file_path
     AND a.last_synced_at < b.last_synced_at;
   ```

2. **Fix upsert logic**:
   - Workflow 07 should use `upsert` operation, not `insert`
   - Verify `file_path` is the unique key

---

## Performance Problems

### Slow Workflow Execution

**Symptom**: Workflows take >30 seconds to complete

**Diagnosis**:
```bash
# Check n8n execution logs
# In n8n UI: Executions tab → View slow executions

# Check system resources
docker stats

# Check database query performance
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c \
  "SELECT query, calls, total_time/calls as avg_time
   FROM pg_stat_statements
   ORDER BY total_time DESC LIMIT 10;"
```

**Solutions**:

1. **Database queries slow**:
   ```bash
   # Add missing indexes
   docker exec postgres-ai-stack psql -U aistack_user -d aistack <<EOF
   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_user_created
     ON memories(user_id, created_at DESC);
   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_salience
     ON memories(salience_score DESC) WHERE is_archived = false;
   EOF
   ```

2. **Ollama model loading slow**:
   ```bash
   # Keep model loaded in memory
   curl http://localhost:11434/api/generate \
     -d '{"model": "nomic-embed-text", "keep_alive": -1}'

   # Or set in Ollama config
   docker exec ollama-ai-stack sh -c \
     'echo "keep_alive=-1" >> /etc/ollama/config'
   ```

3. **Too many concurrent workflows**:
   - Limit concurrent executions in n8n settings
   - Add queue system for heavy workflows
   - Stagger scheduled workflow times

### High Memory Usage

**Symptom**: System runs out of memory, services crash

**Diagnosis**:
```bash
# Check memory usage
free -h
docker stats --no-stream

# Check for memory leaks
docker stats --format "table {{.Name}}\t{{.MemUsage}}" --no-stream
```

**Solutions**:

1. **Increase system memory**:
   - Add more RAM to host machine
   - Reduce other running applications

2. **Optimize Docker limits**:
   ```yaml
   # In docker-compose.yml
   services:
     ollama-ai-stack:
       mem_limit: 2g
       memswap_limit: 2g
   ```

3. **Clean up old data**:
   ```bash
   # Run cleanup workflow (workflow 08)
   # Or manually:
   docker exec postgres-ai-stack psql -U aistack_user -d aistack <<EOF
   DELETE FROM memories WHERE created_at < NOW() - INTERVAL '180 days';
   DELETE FROM health_checks WHERE check_time < NOW() - INTERVAL '30 days';
   VACUUM FULL;
   EOF
   ```

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check logs**: Always start with service logs
   ```bash
   docker-compose logs --tail=100 -f
   ```

2. **Search existing issues**: Check GitHub issues for similar problems

3. **Create detailed bug report**:
   - System information: `docker version`, `docker-compose version`
   - Service status: `docker-compose ps`
   - Relevant logs: Last 100 lines of affected service
   - Steps to reproduce
   - Expected vs actual behavior

4. **Test with minimal setup**:
   - Stop all services: `docker-compose down`
   - Start only required services
   - Test in isolation

---

## Quick Reference

### Restart Everything

```bash
docker-compose down
docker-compose up -d
docker-compose logs -f
```

### Reset Database (DANGER: Deletes all data)

```bash
docker-compose down -v
docker-compose up -d postgres-ai-stack
sleep 10
cd migrations && ./run-migrations.sh
```

### Check Service Health

```bash
# Quick health check
curl http://localhost:5678                 # n8n
curl http://localhost:6333/collections    # Qdrant
curl http://localhost:11434/api/tags      # Ollama
docker exec postgres-ai-stack pg_isready  # PostgreSQL
```

### View Recent Errors

```bash
docker-compose logs --tail=50 | grep -i error
```

### Clean Up Disk Space

```bash
docker system prune -a --volumes
# WARNING: This removes all unused containers, images, and volumes
```

---

## Related Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Webhook specifications
- [Phase 2 Implementation](./PHASE_2_IMPLEMENTATION.md) - Error handling & logging
- [Phase 3 Implementation](./PHASE_3_IMPLEMENTATION.md) - Configuration & validation
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Initial setup instructions
