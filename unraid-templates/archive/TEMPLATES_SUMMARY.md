# AI Stack unRAID Templates - Summary

## ✅ Created Files

### XML Templates (7)
1. **postgres.xml** - PostgreSQL 16 database
2. **qdrant.xml** - Vector database (768-dim embeddings)
3. **redis.xml** - Cache and queue
4. **ollama.xml** - LLM server (llama3.2:3b + nomic-embed-text)
5. **mcp-server.xml** - MCP tools server (17 tools)
6. **n8n.xml** - Workflow automation (18 workflows)
7. **anythingllm.xml** - Chat interface (main UI)

### Support Files (2)
- **README.md** - Complete installation guide
- **setup-network.sh** - Docker network creation script

## 📋 Quick Start Checklist

- [ ] Run `./setup-network.sh` to create Docker network
- [ ] Install data layer: postgres, qdrant, redis
- [ ] Install AI layer: ollama
- [ ] Pull Ollama models: `llama3.2:3b`, `nomic-embed-text`
- [ ] Create Qdrant collections (768 dimensions)
- [ ] Build MCP server image
- [ ] Install MCP server
- [ ] Install n8n
- [ ] Install AnythingLLM
- [ ] Import n8n workflows
- [ ] Configure Obsidian vault

## 🔧 Key Configuration Points

### Passwords (MUST CHANGE!)
- PostgreSQL: `POSTGRES_PASSWORD` (used in 3 templates)
- n8n: `N8N_BASIC_AUTH_PASSWORD`
- AnythingLLM: `AUTH_TOKEN` (optional)

### Ports
- PostgreSQL: 5434 (mapped from 5432)
- Qdrant: 6333
- Redis: 6379
- Ollama: 11434
- MCP Server: 8081
- n8n: 5678 (Web UI)
- AnythingLLM: 3001 (Web UI)

### Storage Paths
All under `/mnt/user/appdata/ai_stack/`:
- `postgres/data` - Database files
- `qdrant/storage` - Vector embeddings
- `ollama/models` - LLM models (~5GB+)
- `n8n/data` - Workflows
- `anythingllm/storage` - Chat history
- `vault/` - Obsidian notes
- `documents/` - RAG documents
- `memory_vault/` - OpenMemory exports
- `chat_exports/` - ChatGPT/Claude imports

### Network
All containers use: `ai-stack-network`

Container hostnames:
- `postgres-ai-stack`
- `qdrant-ai-stack`
- `redis-ai-stack`
- `ollama-ai-stack`
- `mcp-server-ai-stack`
- `n8n-ai-stack`
- `anythingllm-ai-stack`

## 🎯 Key Features

### Embedding Configuration
- **Model:** nomic-embed-text
- **Dimensions:** 768
- **Distance:** Cosine similarity
- **Used by:** AnythingLLM, n8n, MCP Server

### Single User Mode
- Default User ID: `00000000-0000-0000-0000-000000000001`
- No multi-user authentication needed
- Simplified setup

### GPU Support (Optional)
Ollama template includes GPU passthrough options:
- Intel/AMD: `--device=/dev/dri`
- NVIDIA: `--gpus all` (add to ExtraParams)

## 📚 Documentation

See **README.md** for:
- Detailed installation steps
- Troubleshooting guide
- Configuration examples
- Health check commands

## 🆘 Common Issues

### "Network not found"
**Solution:** Run `./setup-network.sh` first

### "Can't connect to postgres"
**Solution:** Check passwords match across postgres, mcp-server, n8n templates

### "Ollama model not found"
**Solution:** Pull models after container starts:
```bash
docker exec ollama-ai-stack ollama pull llama3.2:3b
docker exec ollama-ai-stack ollama pull nomic-embed-text
```

### "Qdrant collection doesn't exist"
**Solution:** Create collections manually (see README.md Step 4)

### "Port already in use"
**Solution:** Edit template and change host port (left side of mapping)

## ✨ What's Next?

After installing all containers:

1. **Access UIs:**
   - AnythingLLM: http://YOUR_SERVER_IP:3001
   - n8n: http://YOUR_SERVER_IP:5678

2. **Import workflows:**
   - Copy JSON files to `/mnt/user/appdata/ai_stack/n8n-workflows/`
   - Import via n8n UI

3. **Setup Obsidian:**
   - Point vault to `/mnt/user/appdata/ai_stack/vault/`
   - Enable file watcher for auto-embedding

4. **Import chat history:**
   - Export from ChatGPT/Claude
   - Drop files in `/mnt/user/appdata/ai_stack/chat_exports/`
   - n8n will auto-process

5. **Start chatting:**
   - Ask "What did I learn about X?" to query memories
   - Create reminders: "Remind me tomorrow at 9am to..."
   - RAG over documents and notes

---

**Ready to deploy!** 🚀
