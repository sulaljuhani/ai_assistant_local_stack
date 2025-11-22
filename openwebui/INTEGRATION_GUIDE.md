# OpenWebUI Integration Guide for LangGraph

This guide explains **two approaches** for integrating OpenWebUI with your LangGraph multi-agent system, with pros/cons and setup instructions for each.

---

## Approach 1: OpenWebUI Pipe Function ⭐ **RECOMMENDED**

### Overview

A **Pipe Function** is a custom plugin that runs directly inside OpenWebUI and has **full access to conversation metadata** including `chat_id`, making it ideal for conversation continuity.

### ✅ Advantages

1. **True Conversation Continuity** - Direct access to `chat_id` from `__metadata__`
2. **No External Container** - Runs inside OpenWebUI, no separate adapter needed
3. **Rich Metadata Access** - Access to user info, files, features, variables
4. **Easy Updates** - Edit directly in OpenWebUI UI, no rebuilds required
5. **Event Emitter Support** - Can show status updates in the UI
6. **Multi-User Ready** - Automatically gets user_id from `__user__` dict

### ❌ Disadvantages

1. **Manual Installation** - Must copy/paste code into OpenWebUI UI
2. **No Version Control** - Code lives in OpenWebUI database (export to backup)
3. **UI-Only Editing** - Must use OpenWebUI's function editor

### Setup Instructions

#### Step 1: Copy the Pipe Function

The Pipe function is located at:
```
/mnt/user/appdata/ai_stack/openwebui/langgraph_pipe.py
```

#### Step 2: Install in OpenWebUI

1. Open OpenWebUI at `http://192.168.0.12:8084/`
2. Go to **Workspace** → **Functions**
3. Click the **"+"** button to create a new function
4. Select **"Pipe Function"**
5. Copy the contents of `langgraph_pipe.py` and paste into the editor
6. Click **Save**

#### Step 3: Configure Valves

After saving, click on the function and configure the Valves:

| Valve | Value | Description |
|-------|-------|-------------|
| `LANGGRAPH_CHAT_URL` | `http://langgraph-agents:8000/chat` | Use Docker network name |
| `LANGGRAPH_API_KEY` | *(leave empty)* | Optional authentication |
| `LANGGRAPH_USER_ID` | `00000000-0000-0000-0000-000000000001` | Default user ID |
| `LANGGRAPH_WORKSPACE` | `default` | Workspace identifier |
| `REQUEST_TIMEOUT` | `30` | Timeout in seconds |
| `DEBUG_MODE` | `false` | Enable for troubleshooting |

#### Step 4: Enable and Use

1. **Enable the function** - Toggle it on in the Functions list
2. **Start a new chat** - Go to the main chat interface
3. **Select the model** - Choose "LangGraph Multi-Agent System" from the model dropdown
4. **Chat normally** - Your messages will be routed to LangGraph with full conversation continuity!

### How It Works

```
┌─────────────┐
│  OpenWebUI  │
│   (User)    │
└──────┬──────┘
       │ chat message
       ▼
┌─────────────────────────┐
│  Pipe Function          │
│  (runs in OpenWebUI)    │
│  - Extracts chat_id     │
│  - Forwards to API      │
└──────┬──────────────────┘
       │ HTTP POST with session_id=chat_id
       ▼
┌─────────────────────────┐
│  LangGraph API          │
│  - Maintains state      │
│  - Executes agents      │
│  - Returns response     │
└─────────────────────────┘
```

### Conversation Continuity

**How it achieves continuity:**

1. OpenWebUI assigns a unique `chat_id` to each conversation
2. The Pipe function receives this in `__metadata__["chat_id"]`
3. It maps `chat_id` → `session_id` when calling LangGraph
4. LangGraph uses `session_id` to load/save conversation state from Redis
5. Each message in the same chat maintains context!

**Example flow:**

```
Message 1: "Create a task to test the system"
  → chat_id: abc-123
  → LangGraph session_id: abc-123
  → Agent creates task, stores in state

Message 2: "What was that task about?"
  → chat_id: abc-123 (same conversation)
  → LangGraph session_id: abc-123 (loads previous state)
  → Agent remembers the task from Message 1!
```

---

## Approach 2: OpenAI-Compatible Adapter (Current Setup)

### Overview

A **FastAPI adapter** that exposes an OpenAI-compatible `/v1/chat/completions` endpoint and forwards to LangGraph.

### ✅ Advantages

1. **Standard Protocol** - Works with any OpenAI-compatible client
2. **Containerized** - Runs as separate Docker service
3. **Version Controlled** - Code in Git repository
4. **Independence** - Can be used by multiple frontends
5. **Already Working** - Currently deployed and functional

### ❌ Disadvantages

1. **No chat_id Access** - OpenAI API doesn't include conversation IDs by default
2. **Requires ENABLE_FORWARD_USER_INFO_HEADERS** - Need special OpenWebUI config
3. **Header-based** - Less reliable than direct metadata access
4. **Extra Container** - Requires separate service (more resources)
5. **Rebuild Required** - Code changes need Docker rebuild

### Current Status

✅ **Working** - Successfully routes requests to LangGraph
✅ **Agents Working** - Task, Food, and Event agents all functional
✅ **Tools Working** - All 50+ tools accessible
⚠️ **Limited Continuity** - Each request gets new session_id (stateless)

### Enabling Conversation Continuity

To add conversation continuity to the adapter approach:

#### Option A: Enable OpenWebUI Headers (Requires OpenWebUI Config)

1. Set environment variable in OpenWebUI container:
   ```bash
   ENABLE_FORWARD_USER_INFO_HEADERS=true
   ```

2. OpenWebUI will send header:
   ```
   X-OpenWebUI-Chat-Id: <chat-id>
   ```

3. Update adapter code to extract header (see `adapter/main.py` improvements)

**Limitation:** This feature may not be available in all OpenWebUI versions.

#### Option B: Use Message History Hash (Partial Solution)

Generate session_id based on conversation hash:
- Hash the first user message to create consistent session ID
- Same conversation starter = same session
- **Limitation:** New conversations with similar starts will collide

---

## Comparison Table

| Feature | Pipe Function | Adapter |
|---------|--------------|---------|
| **Conversation Continuity** | ✅ Full (via chat_id) | ⚠️ Limited (requires headers) |
| **Metadata Access** | ✅ Full (chat_id, user, files, etc.) | ❌ Limited (headers only) |
| **Installation** | Manual (UI paste) | Automated (Docker) |
| **Version Control** | ❌ UI only | ✅ Git repository |
| **Updates** | ✅ Instant (edit in UI) | ⚠️ Requires rebuild |
| **Multi-Frontend** | ❌ OpenWebUI only | ✅ Any OpenAI client |
| **Resource Usage** | ✅ No extra container | ⚠️ Extra container |
| **Setup Complexity** | ✅ Simple (copy/paste) | ⚠️ Moderate (Docker) |

---

## Recommendation

### For OpenWebUI Use ⭐

**Use the Pipe Function** (Approach 1)

- Direct access to `chat_id` for perfect conversation continuity
- Easier to update and maintain
- Runs inside OpenWebUI (no extra containers)
- Full metadata access for future enhancements

### For Multi-Frontend Use

**Use the Adapter** (Approach 2)

- Works with any OpenAI-compatible client
- Can serve multiple frontends simultaneously
- Version controlled in Git
- Consider implementing conversation ID via custom headers

### Hybrid Approach

You can run **both** simultaneously:

- **Pipe Function** for OpenWebUI users (best experience)
- **Adapter** for API access, testing, or other clients

They both talk to the same LangGraph backend, so data is shared.

---

## Testing Conversation Continuity

### Test with Pipe Function

1. Select "LangGraph Multi-Agent System" in OpenWebUI
2. Send: "Create a task called 'Test conversation memory'"
3. In the **same chat**, send: "What task did I just create?"
4. The agent should remember the task! ✅

### Test with Adapter

```bash
# First message
curl -X POST http://localhost:8090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change_me" \
  -d '{
    "model": "langgraph",
    "messages": [{"role": "user", "content": "Create a task to test memory"}]
  }'

# Second message (different session, won't remember)
curl -X POST http://localhost:8090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change_me" \
  -d '{
    "model": "langgraph",
    "messages": [{"role": "user", "content": "What task did I just create?"}]
  }'
```

Expected with adapter: Agent won't remember (new session) ❌

---

## Troubleshooting

### Pipe Function Issues

**Problem:** Function not appearing in model list
- **Solution:** Make sure the function is **enabled** (toggle in Functions list)

**Problem:** "Connection refused" error
- **Solution:** Check `LANGGRAPH_CHAT_URL` uses Docker network name (`http://langgraph-agents:8000/chat`)

**Problem:** No response or timeout
- **Solution:** Increase `REQUEST_TIMEOUT` in Valves, check LangGraph container is running

**Problem:** Want to see debug logs
- **Solution:** Enable `DEBUG_MODE` in Valves, check OpenWebUI container logs

### Adapter Issues

**Problem:** "Invalid token" error
- **Solution:** Use `Bearer change_me` or update `OPENWEBUI_ADAPTER_API_KEY` in `.env`

**Problem:** Need to rebuild after code changes
- **Solution:**
  ```bash
  cd /mnt/user/appdata/ai_stack
  docker-compose build openwebui-adapter
  docker-compose up -d openwebui-adapter
  ```

**Problem:** Want conversation continuity
- **Solution:** Switch to Pipe Function approach, or configure OpenWebUI headers

---

## Next Steps

1. **Try the Pipe Function** - Best experience for OpenWebUI
2. **Test conversation continuity** - Verify same chat remembers context
3. **Explore agent capabilities** - Try task creation, food logging, event scheduling
4. **Add custom tools** - Extend LangGraph with new capabilities
5. **Consider streaming** - Future enhancement for real-time responses

---

## Files Reference

```
/mnt/user/appdata/ai_stack/openwebui/
├── INTEGRATION_GUIDE.md          # This file
├── langgraph_pipe.py              # Pipe Function (copy to OpenWebUI)
├── README.md                      # Original plan
└── adapter/
    ├── main.py                    # FastAPI adapter
    ├── Dockerfile                 # Adapter container
    ├── requirements.txt           # Python dependencies
    ├── .env                       # Adapter configuration
    └── README.md                  # Adapter documentation
```

---

## Support

- **LangGraph Backend Issues:** Check logs with `docker logs langgraph-agents`
- **OpenWebUI Issues:** Check OpenWebUI documentation at https://docs.openwebui.com/
- **Adapter Issues:** Check logs with `docker logs openwebui-adapter`
