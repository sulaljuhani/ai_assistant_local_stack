# AI Stack - unRAID Container Templates

This directory contains 7 unRAID XML templates for deploying the complete AI Stack on unRAID servers.

## 📦 Container Overview

| Container | Port | Purpose | Dependencies |
|-----------|------|---------|--------------|
| **postgres** | 5434 | PostgreSQL database for structured data | None |
| **qdrant** | 6333 | Vector database for embeddings | None |
| **redis** | 6379 | Cache and queue | None |
| **ollama** | 11434 | LLM and embedding models | None |
| **mcp-server** | 8081 | MCP tools for DB/memory access | postgres, qdrant, ollama |
| **n8n** | 5678 | Workflow automation | postgres, qdrant, ollama, redis |
| **anythingllm** | 3001 | Chat interface (main UI) | ollama, qdrant |

## 🚀 Installation Order

**IMPORTANT:** Install containers in this order to satisfy dependencies:

### Step 1: Create Docker Network
```bash
docker network create ai-stack-network
```

### Step 2: Install Data Layer (can be done in parallel)
1. **postgres** - Install and start
2. **qdrant** - Install and start
3. **redis** - Install and start

**Wait for all to be healthy before proceeding.**

### Step 3: Install AI Layer
4. **ollama** - Install and start
   - After starting, pull required models:
   ```bash
   docker exec ollama ollama pull llama3.2:3b
   docker exec ollama ollama pull nomic-embed-text
   ```
   - **Wait for models to download** (llama3.2:3b ~2GB, nomic-embed-text ~274MB)

### Step 4: Initialize Qdrant Collections
```bash
# Create knowledge_base collection (documents, notes)
curl -X PUT "http://YOUR_SERVER_IP:6333/collections/knowledge_base" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'

# Create memories collection (OpenMemory)
curl -X PUT "http://YOUR_SERVER_IP:6333/collections/memories" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
```

### Step 5: Build and Install MCP Server
```bash
# Navigate to MCP server directory (will be created in setup)
cd /mnt/user/appdata/ai_stack/containers/mcp-server

# Build the image
docker build -t mcp-server:latest .

# Then install via unRAID template
```

5. **mcp-server** - Install via template

### Step 6: Install Application Layer
6. **n8n** - Install and start
7. **anythingllm** - Install and start

## 📝 Installation Instructions

### Method 1: unRAID Web UI (Recommended)

1. **Navigate to Docker tab** in unRAID web interface
2. **Click "Add Container"**
3. **Select "Template"** dropdown at the top
4. **Click "Template repositories"** at the bottom
5. **Add your templates directory path:**
   ```
   /mnt/user/appdata/ai_stack/unraid-templates/
   ```
6. **Select the template** you want to install
7. **Configure settings** (especially passwords!)
8. **Click "Apply"**

### Method 2: Manual XML Import

1. **Copy XML file** to unRAID:
   ```bash
   cp postgres.xml /boot/config/plugins/dockerMan/templates-user/
   ```
2. **Refresh Docker page** in unRAID UI
3. **Template will appear** in "User Templates" section

### Method 3: Community Applications (Future)

Once published to Community Applications:
1. Open **Apps** tab in unRAID
2. Search for **"AI Stack"**
3. Install containers in order

## ⚙️ Configuration Notes

### Security (IMPORTANT!)

**Change all default passwords before starting:**
- PostgreSQL password (postgres, mcp-server, n8n templates)
- n8n web UI password
- AnythingLLM auth token (optional)

**Use strong passwords** - these are visible in container settings!

### Storage Paths

Containers installed from Unraid will be located at `/mnt/user/appdata/<container_name>/`:

```
/mnt/user/appdata/
├── postgres/              # PostgreSQL database files
├── qdrant/                # Vector database files
├── redis/                 # Redis persistence
├── ollama/                # LLM models (large!)
├── n8n/                   # n8n workflows and settings
├── anythingllm/           # Chat history and storage
├── mcp-server/            # MCP server (custom build)
└── ai_stack/              # Shared data directory
    ├── vault/             # Obsidian markdown notes
    ├── documents/         # PDFs, DOCX for RAG
    ├── memory_vault/      # OpenMemory exports
    ├── chat_exports/      # ChatGPT/Claude imports
    └── config/            # Configuration files
```

**Make sure your array has enough space!** Ollama models alone can use 10GB+.

### Network Configuration

All containers must be on the **ai-stack-network** bridge network.

If you get connection errors:
1. Check network exists: `docker network ls | grep ai-stack`
2. Verify containers are on network: `docker network inspect ai-stack-network`
3. Test connectivity: `docker exec n8n ping postgres`

### GPU Support (Ollama)

For GPU acceleration with Ollama:
1. **Install GPU drivers** on unRAID (Nvidia/AMD)
2. **Edit template** and ensure `--device=/dev/dri` is in ExtraParams
3. **For NVIDIA:** Add `--gpus all` to ExtraParams
4. **For AMD:** Add `--device=/dev/kfd --device=/dev/dri` to ExtraParams

### Port Conflicts

If ports are already in use, change them in templates:
- PostgreSQL: 5434 (can change to 5435, 5436, etc.)
- Qdrant: 6333 (can change to 6334, etc.)
- n8n: 5678 (can change to any free port)
- AnythingLLM: 3001 (can change to 3002, etc.)

**Note:** Ollama port 11434 is recommended to keep as-is.

## 🔍 Troubleshooting

### Container won't start
- Check logs: Docker tab → click container name → View Logs
- Verify dependencies are running (postgres, qdrant, ollama)
- Check network: `docker network inspect ai-stack-network`

### Can't connect to database
- Verify PostgreSQL password matches across templates
- Check PostgreSQL is running: `docker ps | grep postgres`
- Test connection:
  ```bash
  docker exec postgres pg_isready -U aistack_user
  ```

### Ollama models not loading
- Check disk space: Models are large (2-5GB each)
- Verify models are pulled:
  ```bash
  docker exec ollama ollama list
  ```
- Pull manually if missing:
  ```bash
  docker exec ollama ollama pull llama3.2:3b
  docker exec ollama ollama pull nomic-embed-text
  ```

### n8n can't reach other services
- Verify all containers are on ai-stack-network
- Use container names (e.g., `postgres`), not IPs
- Check n8n environment variables are correct

### AnythingLLM embedding errors
- Ensure nomic-embed-text model is pulled in Ollama
- Check Qdrant collections exist (Step 4)
- Verify EMBEDDING_MODEL=nomic-embed-text in template

## 📊 Health Checks

After installation, verify all services:

```bash
# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test PostgreSQL
docker exec postgres pg_isready

# Test Qdrant
curl -s http://YOUR_SERVER_IP:6333/collections

# Test Ollama
curl -s http://YOUR_SERVER_IP:11434/api/tags

# Test n8n (should see login page)
curl -s http://YOUR_SERVER_IP:5678

# Test AnythingLLM (should see UI)
curl -s http://YOUR_SERVER_IP:3001
```

## 🆘 Support

If you encounter issues:
1. Check logs for each container
2. Verify installation order was followed
3. Ensure all passwords match across dependent containers
4. Check unRAID system logs: `/var/log/syslog`
5. Post in unRAID forums or GitHub issues

## 📚 Next Steps

After installation:
1. **Access AnythingLLM:** http://YOUR_SERVER_IP:3001
2. **Access n8n:** http://YOUR_SERVER_IP:5678
3. **Import n8n workflows** from `/mnt/user/appdata/ai_stack/n8n-workflows/`
4. **Configure Obsidian** to use `/mnt/user/appdata/ai_stack/vault/`
5. **Import chat history** to `/mnt/user/appdata/ai_stack/chat_exports/`

See main documentation for detailed usage instructions.
