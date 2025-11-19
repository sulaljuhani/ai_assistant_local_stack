# 🚀 Production Deployment Checklist

**AI Assistant Local Stack - Production Deployment**

---

## Prerequisites

- [ ] unRAID server or Docker-compatible host
- [ ] Minimum 8GB RAM available
- [ ] 50GB free disk space
- [ ] Domain name configured (optional, for remote access)

---

## Phase 1: Pre-Deployment Preparation

### 1.1 Environment Configuration

- [ ] Copy `.env.example` to `.env`:
  ```bash
  cp .env.example .env
  ```

- [ ] Generate and set strong `POSTGRES_PASSWORD` (32+ characters):
  ```bash
  openssl rand -base64 32
  ```
  Then update in `.env`:
  ```
  POSTGRES_PASSWORD=<generated-password-here>
  ```

- [ ] Set `CORS_ALLOWED_ORIGINS` for production:
  ```
  # For production (replace with your domains)
  CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

  # For development/local
  CORS_ALLOWED_ORIGINS=http://localhost:3001,http://192.168.1.x:3001
  ```

- [ ] Review and update other production settings:
  ```
  API_RELOAD=false
  LOG_LEVEL=INFO
  STATE_PRUNING_ENABLED=true
  ```

- [ ] Secure the `.env` file:
  ```bash
  chmod 600 .env
  ```

### 1.2 Storage Preparation

- [ ] Create storage directories (adjust paths for your system):
  ```bash
  mkdir -p /mnt/user/appdata/postgres
  mkdir -p /mnt/user/appdata/qdrant
  mkdir -p /mnt/user/appdata/redis
  mkdir -p /mnt/user/appdata/ollama
  mkdir -p /mnt/user/appdata/n8n
  mkdir -p /mnt/user/appdata/anythingllm
  mkdir -p /mnt/user/appdata/mcp-server
  mkdir -p /mnt/user/appdata/openmemory
  mkdir -p /mnt/user/backups
  ```

- [ ] Set proper permissions:
  ```bash
  chmod 755 /mnt/user/appdata/*
  chown -R nobody:users /mnt/user/appdata/*
  ```

### 1.3 Docker Network

- [ ] Create Docker network:
  ```bash
  docker network create ai-stack-network
  ```

- [ ] Verify network exists:
  ```bash
  docker network ls | grep ai-stack-network
  ```

---

## Phase 2: Core Services Deployment

Deploy in this order to ensure dependencies are available.

### 2.1 PostgreSQL Database

- [ ] Deploy PostgreSQL container using `unraid-templates/my-postgres.xml`
- [ ] Wait for container to be healthy (30-60 seconds)
- [ ] Verify PostgreSQL is running:
  ```bash
  docker ps | grep postgres
  docker logs postgres-ai-stack
  ```

### 2.2 Redis

- [ ] Deploy Redis container using `unraid-templates/my-redis.xml`
- [ ] Verify Redis is running:
  ```bash
  docker ps | grep redis
  ```

### 2.3 Qdrant Vector Database

- [ ] Deploy Qdrant container using `unraid-templates/my-qdrant.xml`
- [ ] Verify Qdrant is running:
  ```bash
  docker ps | grep qdrant
  curl http://localhost:6333/healthz
  ```

### 2.4 Ollama LLM

- [ ] Deploy Ollama container using `unraid-templates/my-ollama.xml`
- [ ] Wait for Ollama to start (check logs)
- [ ] Pull required models:
  ```bash
  docker exec ollama-ai-stack ollama pull llama3.2:3b
  docker exec ollama-ai-stack ollama pull nomic-embed-text
  ```

- [ ] Verify models are downloaded:
  ```bash
  docker exec ollama-ai-stack ollama list
  ```

---

## Phase 3: Database Setup

### 3.1 Run Database Migrations

- [ ] Run all migrations:
  ```bash
  cd migrations
  chmod +x run-migrations.sh
  ./run-migrations.sh
  ```

- [ ] Verify migrations succeeded (check output)
- [ ] Verify tables exist:
  ```bash
  docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "\dt"
  ```

### 3.2 Initialize Qdrant Collections

- [ ] Initialize Qdrant:
  ```bash
  cd scripts/qdrant
  chmod +x init-collections.sh
  ./init-collections.sh
  ```

- [ ] Verify collections:
  ```bash
  chmod +x verify-collections.sh
  ./verify-collections.sh
  ```

---

## Phase 4: Application Services

### 4.1 MCP Server

- [ ] Deploy MCP Server using `unraid-templates/my-mcp-server.xml`
- [ ] Verify MCP server is healthy:
  ```bash
  docker logs mcp-server-ai-stack
  ```

### 4.2 LangGraph Multi-Agent System

- [ ] Build Docker image:
  ```bash
  cd containers/langgraph-agents
  docker build -t ai-stack-langgraph-agents:latest .
  ```

- [ ] Deploy using Docker run or docker-compose
- [ ] Verify health endpoint:
  ```bash
  curl http://localhost:8000/health
  ```

### 4.3 OpenMemory

- [ ] Deploy OpenMemory using `unraid-templates/my-openmemory.xml`
- [ ] Wait for OpenMemory to initialize database
- [ ] Verify OpenMemory is running:
  ```bash
  curl http://localhost:8080/health
  ```

### 4.4 n8n Workflow Automation

- [ ] Deploy n8n using `unraid-templates/my-n8n.xml`
- [ ] Access n8n UI: `http://your-server:5678`
- [ ] Set up n8n credentials (first-time setup)
- [ ] Import workflows from `n8n-workflows/` directory
- [ ] Configure PostgreSQL credentials in n8n
- [ ] Activate critical workflows:
  - [ ] `19-food-log.json` (secure version)
  - [ ] `01-create-reminder.json`
  - [ ] `04-fire-reminders.json`

### 4.5 AnythingLLM

- [ ] Deploy AnythingLLM using `unraid-templates/my-anythingllm.xml`
- [ ] Access AnythingLLM UI: `http://your-server:3001`
- [ ] Complete AnythingLLM setup wizard
- [ ] Configure Ollama connection
- [ ] Configure Qdrant connection
- [ ] Import skills from `anythingllm-skills/`

---

## Phase 5: Post-Deployment Verification

### 5.1 Health Checks

- [ ] All containers running:
  ```bash
  docker ps | grep ai-stack
  ```

- [ ] Check container logs for errors:
  ```bash
  docker logs postgres-ai-stack | tail -50
  docker logs qdrant-ai-stack | tail -50
  docker logs ollama-ai-stack | tail -50
  docker logs mcp-server-ai-stack | tail -50
  docker logs openmemory-ai-stack | tail -50
  docker logs n8n-ai-stack | tail -50
  docker logs anythingllm-ai-stack | tail -50
  ```

- [ ] Database connections working:
  ```bash
  docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT COUNT(*) FROM reminders;"
  ```

### 5.2 Security Verification

- [ ] Run security validation:
  ```bash
  cd tests
  ./validate-security.sh
  ```

- [ ] Test CORS configuration:
  ```bash
  # Should be rejected from unauthorized origin
  curl -H "Origin: https://evil.com" \
       -H "Access-Control-Request-Method: POST" \
       -X OPTIONS http://localhost:8000/chat
  ```

- [ ] Test rate limiting:
  ```bash
  # After 20 requests in 1 minute, should get 429
  for i in {1..25}; do
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"message":"test","user_id":"test","session_id":"test"}'
  done
  ```

### 5.3 Functional Testing

- [ ] Test LangGraph API:
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{
      "message": "What tasks do I have?",
      "user_id": "00000000-0000-0000-0000-000000000001",
      "session_id": "test-session"
    }'
  ```

- [ ] Test AnythingLLM chat
- [ ] Test memory storage and retrieval
- [ ] Test task creation via AnythingLLM
- [ ] Test reminder creation
- [ ] Test food logging

### 5.4 Backup Setup

- [ ] Configure automated backups (see `scripts/backup/`)
- [ ] Test backup creation:
  ```bash
  cd scripts/backup
  ./backup-database.sh
  ```

- [ ] Test backup restore (on test database):
  ```bash
  ./restore-database.sh <backup-file>
  ```

---

## Phase 6: Optional Enhancements

### 6.1 Obsidian Integration

- [ ] Set `VAULT_PATH` in `.env`
- [ ] Run vault watcher:
  ```bash
  cd scripts/vault-watcher
  ./watch-vault.sh
  ```

### 6.2 External Integrations

- [ ] Todoist sync (set `TODOIST_API_TOKEN` in `.env`)
- [ ] Google Calendar sync (configure OAuth in `.env`)

### 6.3 Monitoring

- [ ] Set up system monitoring dashboard:
  ```bash
  scripts/monitor-system.sh
  ```

- [ ] Configure alerts (Telegram, email, etc.)

---

## Phase 7: Production Hardening

### 7.1 Access Control

- [ ] Enable n8n basic auth (production):
  ```
  N8N_BASIC_AUTH_ACTIVE=true
  N8N_BASIC_AUTH_USER=admin
  N8N_BASIC_AUTH_PASSWORD=<strong-password>
  ```

- [ ] Configure firewall rules (if exposing to internet)
- [ ] Set up reverse proxy with SSL (nginx, Caddy, Traefik)

### 7.2 Backup Automation

- [ ] Configure cron job for daily backups:
  ```bash
  crontab -e
  # Add: 0 2 * * * /path/to/scripts/backup/backup-database.sh
  ```

- [ ] Configure backup retention policy
- [ ] Test backup notifications

### 7.3 Monitoring & Alerts

- [ ] Set up log aggregation (optional)
- [ ] Configure error alerts
- [ ] Set up uptime monitoring

---

## Troubleshooting

### Container Won't Start

1. Check logs: `docker logs <container-name>`
2. Verify environment variables in `.env`
3. Check Docker network: `docker network inspect ai-stack-network`
4. Verify ports are not in use: `netstat -tulpn | grep <port>`

### Database Connection Errors

1. Verify PostgreSQL is running: `docker ps | grep postgres`
2. Check PostgreSQL logs: `docker logs postgres-ai-stack`
3. Test connection:
   ```bash
   docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT 1;"
   ```
4. Verify password in `.env` matches database

### Migrations Fail

1. Check PostgreSQL is accessible
2. Verify user has CREATE permissions
3. Check migration script permissions: `chmod +x run-migrations.sh`
4. Review migration logs in `migrations/logs/`

### Rate Limiting Too Strict

1. Adjust in `containers/langgraph-agents/main.py`
2. Rebuild Docker image
3. Redeploy container

---

## Rollback Plan

If deployment fails:

1. Stop all containers:
   ```bash
   docker stop $(docker ps -q --filter "name=ai-stack")
   ```

2. Remove containers:
   ```bash
   docker rm $(docker ps -aq --filter "name=ai-stack")
   ```

3. Restore database from backup:
   ```bash
   cd scripts/backup
   ./restore-database.sh <backup-file>
   ```

4. Review logs and fix issues
5. Retry deployment

---

## Post-Deployment Checklist

- [ ] All containers running and healthy
- [ ] Security validation passed
- [ ] Functional tests passed
- [ ] Backups configured and tested
- [ ] Monitoring set up
- [ ] Documentation reviewed
- [ ] Team trained on system usage

---

## Success Criteria

✅ **Deployment is successful when:**

1. All containers are running without errors
2. Security validation passes
3. Can create and retrieve tasks/reminders
4. Chat with AnythingLLM works
5. Vector search returns results
6. Backups are being created
7. No critical errors in logs for 24 hours

---

## Maintenance

### Daily
- Check container health
- Monitor disk space
- Review error logs

### Weekly
- Test backups
- Review security logs
- Update models if needed

### Monthly
- Update Docker images
- Review dependencies
- Test disaster recovery

---

**Deployment Date:** __________

**Deployed By:** __________

**Sign-off:** __________

---

For issues or questions, refer to:
- `README.md` - Architecture overview
- `PRODUCTION_READY_STATUS.md` - Security status
- `PRODUCTION_READINESS_REPORT.md` - Detailed audit
- `docs/` - Component-specific documentation
