# AI Stack - Vault File Watcher

Monitors the Obsidian vault for file changes and automatically triggers re-embedding.

## 🎯 Purpose

When you edit markdown files in your Obsidian vault, this watcher:
1. Detects file changes in real-time
2. Calculates file hash to detect actual content changes
3. Triggers n8n webhook for re-embedding
4. Updates vector database with new embeddings

## 🚀 Quick Start

### Linux/unRAID

```bash
cd /mnt/user/appdata/ai_stack/scripts/vault-watcher

# Set environment variables (optional)
export VAULT_DIR=/mnt/user/appdata/ai_stack/vault
export N8N_WEBHOOK=http://n8n-ai-stack:5678/webhook/reembed-file

# Run watcher
./watch-vault.sh
```

### Windows

```powershell
cd C:\ai_stack\scripts\vault-watcher

# Run watcher
.\watch-vault.ps1 -VaultPath "C:\ai_stack\vault" -WebhookUrl "http://localhost:5678/webhook/reembed-file"
```

## ⚙️ Configuration

### Environment Variables (Bash)

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_DIR` | `/mnt/user/appdata/ai_stack/vault` | Vault directory path |
| `N8N_WEBHOOK` | `http://n8n-ai-stack:5678/webhook/reembed-file` | n8n webhook URL |
| `POSTGRES_HOST` | `postgres-ai-stack` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `aistack` | Database name |
| `POSTGRES_USER` | `aistack_user` | Database user |
| `POSTGRES_PASSWORD` | *(required)* | Database password |
| `DEBOUNCE_SECONDS` | `5` | Debounce time |

### PowerShell Parameters

```powershell
.\watch-vault.ps1 `
    -VaultPath "C:\ai_stack\vault" `
    -WebhookUrl "http://localhost:5678/webhook/reembed-file" `
    -DebounceSeconds 5
```

## 🔄 How It Works

1. **File Change Detection**
   - Uses `inotifywait` (Linux) or `FileSystemWatcher` (Windows)
   - Monitors MODIFY, CREATE, DELETE, MOVE events
   - Filters for `.md` files only

2. **Debouncing**
   - Prevents duplicate processing of rapid changes
   - Default: 5 seconds between processing same file

3. **Hash Comparison**
   - Calculates SHA-256 hash of file content
   - Queries database for existing hash
   - Skips re-embedding if content unchanged

4. **Webhook Trigger**
   - Sends file metadata to n8n webhook
   - Payload includes: path, hash, size, event type
   - n8n workflow handles embedding generation

5. **Database Update**
   - n8n workflow updates `file_sync` table
   - Updates `notes` table with new content
   - Updates Qdrant vector database

## 📊 Workflow Integration

### n8n Webhook Payload

```json
{
  "file_path": "/mnt/user/appdata/ai_stack/vault/daily/2025-11-18.md",
  "relative_path": "daily/2025-11-18.md",
  "file_hash": "abc123...",
  "file_size": 1234,
  "event": "MODIFY",
  "timestamp": "2025-11-18T10:30:00Z"
}
```

### n8n Workflow Steps

1. Receive webhook
2. Read file content
3. Update `notes` table in PostgreSQL
4. Generate embedding via Ollama
5. Upsert to Qdrant `knowledge_base` collection
6. Update `file_sync` table with new hash

## 🖥️ Running as Service

### Linux (systemd)

```bash
# Copy service file
sudo cp vault-watcher.service /etc/systemd/system/

# Edit environment variables
sudo nano /etc/systemd/system/vault-watcher.service

# Enable and start
sudo systemctl enable vault-watcher
sudo systemctl start vault-watcher

# Check status
sudo systemctl status vault-watcher

# View logs
sudo journalctl -u vault-watcher -f
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-File C:\ai_stack\scripts\vault-watcher\watch-vault.ps1`
5. Conditions: Uncheck "Stop if computer goes on batteries"
6. Settings: Check "Run task as soon as possible after scheduled start is missed"

### Docker Container (Alternative)

```bash
docker run -d \
  --name vault-watcher \
  --network ai-stack-network \
  -v /mnt/user/appdata/ai_stack/vault:/vault:ro \
  -e VAULT_DIR=/vault \
  -e N8N_WEBHOOK=http://n8n-ai-stack:5678/webhook/reembed-file \
  -e POSTGRES_HOST=postgres-ai-stack \
  -e POSTGRES_PASSWORD=your_password \
  --restart unless-stopped \
  alpine:latest \
  /bin/sh -c "apk add --no-cache inotify-tools curl bash && /watch-vault.sh"
```

## 📝 Watched Events

### Linux (inotify)

- `MODIFY` - File content changed
- `CREATE` - New file created
- `DELETE` - File deleted
- `MOVE` - File renamed/moved

### Windows (FileSystemWatcher)

- `Changed` - File content changed
- `Created` - New file created
- `Deleted` - File deleted
- `Renamed` - File renamed

## 🚫 Excluded Patterns

Files/directories automatically excluded:
- `.obsidian/` - Obsidian config
- `.git/` - Git repository
- `.trash/` - Trash folder
- Hidden files (starting with `.`)
- Temp files (ending with `~`)
- Non-markdown files

## 🐛 Troubleshooting

### "inotify-tools not installed" (Linux)

```bash
# Debian/Ubuntu
sudo apt-get install inotify-tools

# RHEL/CentOS
sudo yum install inotify-tools

# Alpine
apk add inotify-tools
```

### "Webhook failed" Error

Check:
1. n8n container is running
2. Webhook URL is correct
3. n8n workflow is active
4. Network connectivity: `curl $N8N_WEBHOOK`

### Files Not Being Detected

Check:
1. Vault directory path is correct
2. Watcher has read permissions
3. File is `.md` extension
4. Not in excluded directory (`.obsidian`, `.git`)

### High CPU Usage

Reduce monitoring load:
- Increase debounce time: `DEBOUNCE_SECONDS=10`
- Exclude more directories
- Use scheduled sync instead of real-time

### Database Connection Failed

Check:
1. PostgreSQL container is running
2. Password is correct
3. Database exists
4. User has permissions

Test connection:
```bash
PGPASSWORD=your_password psql -h postgres-ai-stack -U aistack_user -d aistack -c "SELECT 1"
```

## 📊 Performance

### Resource Usage

- **CPU**: ~1-5% (idle), ~10-20% (during processing)
- **Memory**: ~10-50 MB
- **Disk I/O**: Minimal (hash calculation only)
- **Network**: Minimal (webhook calls only)

### Limitations

- **Linux**: inotify watch limit (default 8192)
  ```bash
  # Increase limit
  echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
  ```

- **Windows**: No hard limit, but performance degrades with >10k files

### Scaling

For large vaults (>10k files):
- Consider scheduled batch processing instead
- Use incremental scanning
- Implement rate limiting on webhook

## 🔄 Alternative: Scheduled Sync

If real-time watching is problematic, use cron/scheduled task:

```bash
# Cron job (every 5 minutes)
*/5 * * * * /mnt/user/appdata/ai_stack/scripts/vault-watcher/scan-vault.sh
```

## 📚 Related Components

- **n8n Workflow**: `09-watch-vault.json` - Processes webhook
- **Database Table**: `file_sync` - Tracks file hashes
- **Database Table**: `notes` - Stores note content
- **Qdrant Collection**: `knowledge_base` - Stores embeddings

## ✨ Features

✅ Real-time file change detection
✅ Content hash comparison (avoid unnecessary re-embedding)
✅ Debouncing (prevent rapid-fire triggers)
✅ Cross-platform (Linux, Windows)
✅ Systemd service support
✅ Obsidian integration
✅ Automatic exclusion of config/temp files
✅ Error handling and logging

---

**Auto-sync your Obsidian vault with the AI Stack vector database** 📝
