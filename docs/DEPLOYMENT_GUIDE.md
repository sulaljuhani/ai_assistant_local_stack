# 🚀 AI Stack - Deployment Guide

Complete step-by-step guide to deploying the AI Stack on unRAID or any Docker-capable system.

## 📋 Prerequisites

### Hardware Requirements

- **CPU**: 4+ cores recommended (for Ollama LLM)
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 50GB+ free space
- **GPU** (optional): NVIDIA GPU for faster Ollama inference

### Software Requirements

- **unRAID** 6.10+ (or any Docker-capable OS)
- **Docker**: 20.10+
- **Docker Compose** (optional, for non-unRAID deployments)
- **Python**: 3.11+ (for scripts)
- **Bash**: 4.0+ (for Linux scripts)
- **PowerShell**: 5.1+ (for Windows scripts)

## 🎯 Deployment Path

Choose your deployment method:

- **Path A**: unRAID (recommended) - Use XML templates
- **Path B**: Docker Compose - Use docker-compose.yml (to be created)
- **Path C**: Manual Docker - Use individual docker run commands

This guide covers **Path A (unRAID)** in detail. Adapt as needed for other paths.

---

## 📦 Step 1: Create Docker Network

All containers must be on the same network to communicate.

```bash
docker network create ai-stack-network
```

Verify:
```bash
docker network ls | grep ai-stack
```

---

## 🗄️ Step 2: Deploy PostgreSQL

### 2.1 Install Container

1. Go to unRAID: **Docker** tab
2. Click **Add Container**
3. Click **Select a template** dropdown
4. Navigate to: `/mnt/user/appdata/ai_stack/unraid-templates/`
5. Select: `my-postgres.xml`
6. Configure:
   - **Name**: `postgres-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `5434` (host) → `5432` (container)
   - **Environment Variables**:
     - `POSTGRES_DB`: `aistack`
     - `POSTGRES_USER`: `aistack_user`
     - `POSTGRES_PASSWORD`: `<strong-password>` ⚠️ **Change this!**
   - **AppData Path**: `/mnt/user/appdata/postgres-ai-stack`

7. Click **Apply**

### 2.2 Run Migrations

Wait 30 seconds for PostgreSQL to fully start, then:

```bash
cd /mnt/user/appdata/ai_stack/migrations
export POSTGRES_PASSWORD=<your-password>
./run-migrations.sh
```

Verify:
```bash
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "\\dt"
```

You should see 18+ tables.

---

## 🔍 Step 3: Deploy Qdrant

### 3.1 Install Container

1. **Docker** tab → **Add Container**
2. Select template: `my-qdrant.xml`
3. Configure:
   - **Name**: `qdrant-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `6333` (both)
   - **AppData Path**: `/mnt/user/appdata/qdrant-ai-stack`

4. Click **Apply**

### 3.2 Initialize Collections

```bash
cd /mnt/user/appdata/ai_stack/scripts/qdrant
./init-collections.sh
```

Verify:
```bash
curl http://localhost:6333/collections
```

Should show `knowledge_base` and `memories` collections.

---

## 🧠 Step 4: Deploy Ollama

### 4.1 Install Container

1. **Docker** tab → **Add Container**
2. Select template: `my-ollama.xml`
3. Configure:
   - **Name**: `ollama-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `11434` (both)
   - **GPU** (if available): Enable GPU passthrough
   - **AppData Path**: `/mnt/user/appdata/ollama-ai-stack`

4. Click **Apply**

### 4.2 Pull Models

```bash
# Embedding model (required)
docker exec ollama-ai-stack ollama pull nomic-embed-text

# LLM model (required for summaries)
docker exec ollama-ai-stack ollama pull llama3.2:3b
```

Wait for downloads (may take 5-10 minutes).

Verify:
```bash
docker exec ollama-ai-stack ollama list
```

---

## 💾 Step 5: Deploy Redis (Optional)

Required for n8n queue functionality.

1. **Docker** tab → **Add Container**
2. Select template: `my-redis.xml`
3. Configure:
   - **Name**: `redis-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `6379` (both)

4. Click **Apply**

---

## 🔧 Step 6: Deploy MCP Server

### 6.1 Build Image

```bash
cd /mnt/user/appdata/ai_stack/containers/mcp-server
docker build -t mcp-server-ai-stack:latest .
```

### 6.2 Install Container

1. **Docker** tab → **Add Container**
2. Select template: `my-mcp-server.xml`
3. Configure:
   - **Name**: `mcp-server-ai-stack`
   - **Network**: `ai-stack-network`
   - **Environment Variables**:
     - `POSTGRES_HOST`: `postgres-ai-stack`
     - `POSTGRES_PASSWORD`: `<your-password>`
     - `QDRANT_URL`: `http://qdrant-ai-stack:6333`
     - `OLLAMA_URL`: `http://ollama-ai-stack:11434`

4. Click **Apply**

Verify:
```bash
docker logs mcp-server-ai-stack
```

Should show "MCP Server started on stdio".

---

## 🔄 Step 7: Deploy n8n

### 7.1 Install Container

1. **Docker** tab → **Add Container**
2. Select template: `my-n8n.xml`
3. Configure:
   - **Name**: `n8n-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `5678` (both)
   - **AppData Path**: `/mnt/user/appdata/n8n-ai-stack`
   - **Environment Variables**:
     - `N8N_HOST`: `<your-server-ip>`
     - `WEBHOOK_URL`: `http://<your-server-ip>:5678`
     - `GENERIC_TIMEZONE`: `America/New_York` (adjust)

4. Click **Apply**

### 7.2 Import Workflows

1. Access n8n: `http://<your-server-ip>:5678`
2. Create account (first launch)
3. For each workflow in `n8n-workflows/`:
   - Settings → Import from file
   - Select workflow JSON file
   - Click **Import**

4. Configure credentials:
   - Settings → Credentials → **Add Credential**
   - Type: **PostgreSQL**
   - Name: `AI Stack PostgreSQL`
   - Host: `postgres-ai-stack`
   - Database: `aistack`
   - User: `aistack_user`
   - Password: `<your-password>`
   - **Save**

5. Activate all workflows:
   - For each workflow, click toggle to **ON**

Verify:
```bash
curl http://localhost:5678/webhook/create-reminder \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "remind_at": "2025-11-20T09:00:00Z"}'
```

---

## 💬 Step 8: Deploy AnythingLLM

### 8.1 Install Container

1. **Docker** tab → **Add Container**
2. Select template: `my-anythingllm.xml`
3. Configure:
   - **Name**: `anythingllm-ai-stack`
   - **Network**: `ai-stack-network`
   - **Port**: `3001` (both)
   - **AppData Path**: `/mnt/user/appdata/anythingllm-ai-stack`
   - **Environment Variables**:
     - `STORAGE_DIR`: `/app/server/storage`

4. Click **Apply**

### 8.2 Initial Setup

1. Access: `http://<your-server-ip>:3001`
2. Create admin account
3. Configure LLM:
   - Settings → LLM Provider → **Ollama**
   - Base URL: `http://ollama-ai-stack:11434`
   - Model: `llama3.2:3b`
   - **Save**

4. Configure Embeddings:
   - Settings → Embedding Provider → **Ollama**
   - Base URL: `http://ollama-ai-stack:11434`
   - Model: `nomic-embed-text`
   - **Save**

5. Configure Vector Database:
   - Settings → Vector Database → **Qdrant**
   - URL: `http://qdrant-ai-stack:6333`
   - **Save**

### 8.3 Install Custom Skills

```bash
# Copy skills to AnythingLLM
docker cp /mnt/user/appdata/ai_stack/anythingllm-skills/. \
  anythingllm-ai-stack:/app/server/storage/custom-skills/

# Restart container
docker restart anythingllm-ai-stack
```

Verify skills:
1. Workspace Settings → Agent Skills
2. Should see 6 custom skills
3. Enable all skills

---

## 📝 Step 9: Setup Obsidian Vault

### 9.1 Create Vault Structure

```bash
cd /mnt/user/appdata/ai_stack/scripts
./setup-vault.sh
```

### 9.2 Configure Obsidian

1. Open Obsidian
2. **Open folder as vault**
3. Select: `/mnt/user/appdata/ai_stack/vault`
4. Install recommended plugins:
   - Dataview (for queries)
   - Calendar (for daily notes)
   - Templater (for templates)

### 9.3 Start Vault Watcher

**Linux/unRAID**:
```bash
cd /mnt/user/appdata/ai_stack/scripts/vault-watcher
export POSTGRES_PASSWORD=<your-password>
nohup ./watch-vault.sh > /var/log/vault-watcher.log 2>&1 &
```

**As systemd service** (preferred):
```bash
sudo cp vault-watcher.service /etc/systemd/system/
sudo nano /etc/systemd/system/vault-watcher.service
# Edit POSTGRES_PASSWORD
sudo systemctl enable vault-watcher
sudo systemctl start vault-watcher
```

Verify:
```bash
# Edit a file in vault
echo "Test note" > /mnt/user/appdata/ai_stack/vault/test.md

# Check n8n logs
docker logs n8n-ai-stack | tail -20

# Check if file was embedded
curl http://localhost:6333/collections/knowledge_base | jq .result.points_count
```

---

## 🧪 Step 10: Verify Installation

### 10.1 Check All Containers

```bash
docker ps | grep ai-stack
```

Should show 7 running containers:
- postgres-ai-stack
- qdrant-ai-stack
- redis-ai-stack (optional)
- ollama-ai-stack
- mcp-server-ai-stack
- n8n-ai-stack
- anythingllm-ai-stack

### 10.2 Run System Monitor

```bash
cd /mnt/user/appdata/ai_stack/scripts
./monitor-system.sh
```

Should show:
- All containers running
- Database statistics
- Qdrant collections with point counts
- Ollama models loaded

### 10.3 Test End-to-End

1. **Create a task via n8n**:
```bash
curl -X POST http://localhost:5678/webhook/create-task \
  -H "Content-Type: application/json" \
  -d '{"title": "Test task", "priority": "high"}'
```

2. **Store a memory**:
```bash
curl -X POST http://localhost:5678/webhook/store-chat-turn \
  -H "Content-Type: application/json" \
  -d '{"content": "This is a test memory", "conversation_title": "Test"}'
```

3. **Search memories**:
```bash
curl -X POST http://localhost:5678/webhook/search-memories \
  -H "Content-Type: application/json" \
  -d '{"query": "test memory", "limit": 5}'
```

4. **Test AnythingLLM skill**:
   - Open AnythingLLM chat
   - Say: "Create a reminder to test the system at 2 PM today"
   - AI should use `create-reminder` skill

---

## 🔒 Step 11: Security Hardening (Production)

### 11.1 Change Default Passwords

- PostgreSQL: Update `POSTGRES_PASSWORD` everywhere
- n8n: Enable authentication
- AnythingLLM: Use strong admin password

### 11.2 Enable HTTPS

Use reverse proxy (nginx, Traefik, etc.):
- AnythingLLM: `https://ai.yourdomain.com`
- n8n: `https://n8n.yourdomain.com`

### 11.3 Firewall Rules

```bash
# Only allow necessary ports
ufw allow 3001/tcp  # AnythingLLM
ufw allow 5678/tcp  # n8n
ufw deny 5434/tcp   # PostgreSQL (internal only)
ufw deny 6333/tcp   # Qdrant (internal only)
ufw deny 11434/tcp  # Ollama (internal only)
```

### 11.4 Backup Strategy

```bash
# Daily PostgreSQL backup
docker exec postgres-ai-stack pg_dump -U aistack_user aistack > backup.sql

# Daily Qdrant snapshot
curl -X POST http://localhost:6333/collections/memories/snapshots
curl -X POST http://localhost:6333/collections/knowledge_base/snapshots
```

---

## 📊 Step 12: Optional Integrations

### 12.1 Todoist Sync

1. Get Todoist API token: https://todoist.com/prefs/integrations
2. n8n: Settings → Credentials → **Todoist API**
3. Enter token
4. Activate workflow 13 (todoist-sync)

### 12.2 Google Calendar Sync

1. Google Cloud Console: Create OAuth2 credentials
2. n8n: Settings → Credentials → **Google Calendar OAuth2**
3. Enter credentials
4. Activate workflow 14 (google-calendar-sync)

### 12.3 Claude Desktop (MCP)

1. Install Claude Desktop
2. Configure MCP server:

`~/.config/claude/config.json`:
```json
{
  "mcpServers": {
    "ai-stack": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-server-ai-stack", "python", "server.py"]
    }
  }
}
```

3. Restart Claude Desktop
4. Verify tools appear in Claude

---

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs <container-name>

# Check network
docker network inspect ai-stack-network

# Restart container
docker restart <container-name>
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT 1"

# Check password
echo $POSTGRES_PASSWORD
```

### Embedding Generation Fails

```bash
# Check Ollama models
docker exec ollama-ai-stack ollama list

# Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'

# Re-pull model
docker exec ollama-ai-stack ollama pull nomic-embed-text
```

### n8n Workflows Not Executing

1. Check workflow is active (toggle ON)
2. Check credentials are configured
3. Test webhook manually with curl
4. Check n8n logs: `docker logs n8n-ai-stack`

### Vault Watcher Not Working

```bash
# Check process is running
ps aux | grep watch-vault

# Check logs
tail -f /var/log/vault-watcher.log

# Test manually
curl -X POST http://localhost:5678/webhook/reembed-file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/file.md", "file_hash": "abc123"}'
```

---

## 📚 Next Steps

1. **Import Chat History**: Use `scripts/python/import_chatgpt.py`
2. **Customize Workflows**: Edit n8n workflows for your needs
3. **Add Notes to Vault**: Start writing in Obsidian
4. **Monitor System**: Use `scripts/monitor-system.sh`
5. **Deduplicate Memories**: Run `scripts/python/deduplicate_memories.py`

---

## 🎉 Success!

You now have a fully functional AI Stack with:

✅ 7 Docker containers running
✅ 18 database tables
✅ 18 n8n workflows active
✅ 6 AnythingLLM custom skills
✅ Vault file watcher running
✅ OpenMemory system operational
✅ Vector search enabled
✅ LLM and embeddings working

**Your AI assistant is ready!** 🧠✨

---

## 📞 Support

- **Issues**: https://github.com/sulaljuhani/ai_assistant_local_stack/issues
- **Documentation**: See README.md and component-specific READMEs
- **Logs**: `docker logs <container-name>`
- **Monitor**: `./scripts/monitor-system.sh`
