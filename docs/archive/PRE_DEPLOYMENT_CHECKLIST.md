# 🚀 Pre-Deployment Checklist for unRAID

Complete this checklist before deploying AI Stack to your unRAID server.

## ⚠️ CRITICAL SECURITY ITEMS

### 1. Environment Configuration
- [ ] Copy `.env.example` to `.env`: `cp .env.example .env`
- [ ] Update **all** passwords in `.env`:
  - [ ] `POSTGRES_PASSWORD` - Generate: `openssl rand -base64 32`
  - [ ] `REDIS_PASSWORD` (if using) - Generate: `openssl rand -base64 32`
  - [ ] `N8N_BASIC_AUTH_PASSWORD` (if using) - Use strong password
  - [ ] `ANYTHINGLLM_JWT_SECRET` (if using) - Generate: `openssl rand -hex 64`
- [ ] Verify `DEFAULT_USER_ID` is set
- [ ] Update `TZ` to your timezone
- [ ] Set correct storage paths for unRAID (typically `/mnt/user/appdata/...`)
- [ ] Secure `.env` file: `chmod 600 .env`

### 2. Fix SQL Injection Vulnerabilities
- [ ] **CRITICAL**: Replace `n8n-workflows/19-food-log.json` with secure version:
  ```bash
  cp n8n-workflows/19-food-log-SECURE.json n8n-workflows/19-food-log.json
  ```
- [ ] Review `N8N_WORKFLOW_SECURITY_FIX_GUIDE.md` for comprehensive fixes
- [ ] Plan to fix remaining 13 vulnerable workflows (see priority order in guide)
- [ ] Run security validation: `./scripts/validate-security.sh`

### 3. Network Security
- [ ] Verify Tailscale is configured and running
- [ ] Test Tailscale connectivity from remote device
- [ ] Configure Cloudflare Tunnel (if exposing publicly)
- [ ] Enable Cloudflare Access authentication (if public)
- [ ] Document which services are exposed and how

## 📦 Container Setup

### 4. Docker Network
- [ ] Create AI Stack network: `docker network create ai-stack-network`
- [ ] Verify network exists: `docker network ls | grep ai-stack`

### 5. Storage Directories (unRAID paths)
- [ ] Create PostgreSQL data directory: `mkdir -p /mnt/user/appdata/postgres-ai-stack`
- [ ] Create Qdrant data directory: `mkdir -p /mnt/user/appdata/qdrant-ai-stack`
- [ ] Create Redis data directory: `mkdir -p /mnt/user/appdata/redis-ai-stack`
- [ ] Create Ollama models directory: `mkdir -p /mnt/user/appdata/ollama-ai-stack`
- [ ] Create n8n data directory: `mkdir -p /mnt/user/appdata/n8n-ai-stack`
- [ ] Create AnythingLLM data directory: `mkdir -p /mnt/user/appdata/anythingllm-ai-stack`
- [ ] Create MCP Server data directory: `mkdir -p /mnt/user/appdata/mcp-server-ai-stack`
- [ ] Set permissions: `chmod 755 /mnt/user/appdata/*-ai-stack`

### 6. unRAID Template Installation
- [ ] Copy templates to unRAID: `/boot/config/plugins/dockerMan/templates-user/`
- [ ] Or add template URL in Community Applications
- [ ] Install containers in this order:
  1. [ ] PostgreSQL (`my-postgres.xml`)
  2. [ ] Qdrant (`my-qdrant.xml`)
  3. [ ] Redis (`my-redis.xml`)
  4. [ ] Ollama (`my-ollama.xml`)
  5. [ ] n8n (`my-n8n.xml`)
  6. [ ] MCP Server (`my-mcp-server.xml`)
  7. [ ] AnythingLLM (`my-anythingllm.xml`)
- [ ] Verify all containers are running: `docker ps`

## 🗄️ Database Setup

### 7. PostgreSQL Initialization
- [ ] Wait for PostgreSQL to start (check logs)
- [ ] Run migrations: `cd migrations && ./run-migrations.sh`
- [ ] Verify tables created:
  ```bash
  docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "\dt"
  ```
- [ ] Add metadata column: `./scripts/add_metadata_column.sh`
- [ ] Test database connection from host:
  ```bash
  psql -h localhost -p 5434 -U aistack_user -d aistack
  ```

### 8. Qdrant Setup
- [ ] Wait for Qdrant to start
- [ ] Initialize collections: `cd scripts/qdrant && ./init-collections.sh`
- [ ] Or use Python script: `python3 scripts/qdrant/init-collections.py`
- [ ] Verify collections:
  ```bash
  curl http://localhost:6333/collections
  ```
- [ ] Expected: `knowledge_base` and `memories` collections with 768 dimensions

### 9. Ollama Models
- [ ] Pull embedding model:
  ```bash
  docker exec ollama-ai-stack ollama pull nomic-embed-text
  ```
- [ ] Pull LLM model:
  ```bash
  docker exec ollama-ai-stack ollama pull llama3.2:3b
  ```
- [ ] Verify models:
  ```bash
  docker exec ollama-ai-stack ollama list
  ```
- [ ] Test embedding:
  ```bash
  curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test"}'
  ```

## 🔧 Application Configuration

### 10. n8n Setup
- [ ] Access n8n UI: `http://your-unraid-ip:5678`
- [ ] Create admin account
- [ ] Configure PostgreSQL credentials in n8n
- [ ] Import workflows from `n8n-workflows/`
- [ ] **IMPORTANT**: Use secure versions of workflows
- [ ] Activate workflows:
  - [ ] Daily Summary
  - [ ] Fire Reminders
  - [ ] Vault Watcher (if using Obsidian)
  - [ ] Food Log (use SECURE version)
- [ ] Test webhook endpoints

### 11. AnythingLLM Setup
- [ ] Access AnythingLLM: `http://your-unraid-ip:3001`
- [ ] Complete first-time setup
- [ ] Configure Ollama connection:
  - Base URL: `http://ollama-ai-stack:11434`
  - Model: `llama3.2:3b`
- [ ] Configure embedding:
  - Model: `nomic-embed-text`
  - Dimensions: 768
- [ ] Configure Qdrant:
  - URL: `http://qdrant-ai-stack:6333`
  - Collection: `knowledge_base`
- [ ] Test chat functionality

### 12. MCP Server Setup
- [ ] Verify MCP server is running: `docker logs mcp-server-ai-stack`
- [ ] Check for errors in startup logs
- [ ] Test database connection from MCP server
- [ ] Test Qdrant connection from MCP server

## 📝 Optional Integrations

### 13. Obsidian Vault Sync (Optional)
- [ ] Set `VAULT_PATH` in `.env`
- [ ] Run vault setup: `./scripts/setup-vault.sh`
- [ ] Configure vault watcher in n8n
- [ ] Test file sync: Create a note, verify it appears in database

### 14. Todoist Integration (Optional)
- [ ] Get API token from https://todoist.com/prefs/integrations
- [ ] Set `TODOIST_API_TOKEN` in `.env`
- [ ] Activate Todoist sync workflow in n8n
- [ ] Test bidirectional sync

### 15. Google Calendar Integration (Optional)
- [ ] Create OAuth credentials at https://console.cloud.google.com/
- [ ] Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` in `.env`
- [ ] Activate Google Calendar sync workflow in n8n
- [ ] Test bidirectional sync

## 🧪 Testing & Validation

### 16. Run Security Validation
- [ ] Execute validation script: `./scripts/validate-security.sh`
- [ ] Fix any errors reported
- [ ] Address warnings if applicable

### 17. Test Core Functionality
- [ ] Create a reminder via n8n webhook
- [ ] Create a task via n8n webhook
- [ ] Create an event via n8n webhook
- [ ] Log food via secure webhook
- [ ] Search memories in AnythingLLM
- [ ] Verify vector search works in Qdrant

### 18. Test SQL Injection Protection
- [ ] Run SQL injection tests:
  ```bash
  curl -X POST http://localhost:5678/webhook/log-food \
    -H "Content-Type: application/json" \
    -d '{"food_name":"Pizza'\'')); DROP TABLE food_log; --","location":"Home","preference":"liked"}'
  ```
- [ ] Verify malicious SQL is stored as text, not executed
- [ ] Check database: `SELECT * FROM food_log ORDER BY created_at DESC LIMIT 1;`

### 19. Monitor System Health
- [ ] Run system monitor: `./scripts/monitor-system.sh`
- [ ] Verify all containers are healthy
- [ ] Check resource usage
- [ ] Review logs for errors

### 20. Backup Verification
- [ ] Create database backup:
  ```bash
  docker exec postgres-ai-stack pg_dump -U aistack_user aistack > backup_$(date +%Y%m%d).sql
  ```
- [ ] Test backup restoration on test system
- [ ] Document backup location
- [ ] Set up automated backups (unRAID CA Backup plugin recommended)

## 🔒 Security Hardening (For Production)

### 21. Network Security (if exposing beyond Tailscale)
- [ ] Enable n8n basic authentication
- [ ] Set AnythingLLM JWT secret
- [ ] Configure Redis password
- [ ] Enable SSL/TLS for exposed services
- [ ] Configure firewall rules on unRAID
- [ ] Use Cloudflare Access for public exposure

### 22. Monitoring & Logging
- [ ] Set up log rotation for Docker containers
- [ ] Configure unRAID syslog
- [ ] Set up alerts for container failures
- [ ] Monitor disk usage
- [ ] Set up PostgreSQL backup automation

### 23. Documentation
- [ ] Document your specific configuration
- [ ] Save `.env` to secure location (encrypted)
- [ ] Document any customizations
- [ ] Note which workflows are active
- [ ] Document backup procedures
- [ ] Create disaster recovery plan

## 📊 Post-Deployment

### 24. Initial Data Import (Optional)
- [ ] Import ChatGPT conversations:
  ```bash
  python3 scripts/python/import_chatgpt.py /path/to/conversations.json
  ```
- [ ] Verify imported memories in database
- [ ] Check Qdrant vectors were created
- [ ] Test memory search in AnythingLLM

### 25. Ongoing Maintenance
- [ ] Schedule weekly database backups
- [ ] Review logs monthly
- [ ] Update containers quarterly
- [ ] Check for security updates
- [ ] Monitor disk usage
- [ ] Review and rotate logs

---

## ✅ Deployment Sign-off

**Date**: _______________

**Deployed By**: _______________

**Checklist Complete**: [ ] Yes [ ] No

**Security Validation Passed**: [ ] Yes [ ] No

**All Tests Passed**: [ ] Yes [ ] No

**Backups Configured**: [ ] Yes [ ] No

**Notes**:
_______________________________________________
_______________________________________________
_______________________________________________

---

## 🆘 Troubleshooting Quick Reference

### Container won't start
```bash
docker logs <container-name>
docker inspect <container-name>
```

### Database connection failed
```bash
docker exec postgres-ai-stack pg_isready -U aistack_user
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT 1;"
```

### Qdrant not responding
```bash
curl http://localhost:6333/health
docker logs qdrant-ai-stack
```

### n8n workflow errors
- Check n8n execution logs in UI
- Verify PostgreSQL credentials
- Test database connectivity
- Check webhook URLs

### Ollama errors
```bash
docker exec ollama-ai-stack ollama list
curl http://localhost:11434/api/tags
```

---

## 📚 Additional Resources

- **Main Documentation**: `README.md`
- **Security Guide**: `SECURITY.md`
- **SQL Injection Fixes**: `N8N_WORKFLOW_SECURITY_FIX_GUIDE.md`
- **Security Audit**: `SECURITY_AUDIT_FINDINGS.md`
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md`
- **Architecture**: `COMPLETE_STRUCTURE.md`
- **FAQ**: `ANSWERS_TO_YOUR_QUESTIONS.md`

---

**Ready for deployment? Run the security validator first:**
```bash
./scripts/validate-security.sh
```

**Good luck! 🚀**
