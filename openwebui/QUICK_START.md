# Quick Start: OpenWebUI + LangGraph

## 🚀 Fastest Setup (Recommended)

### Using OpenWebUI Pipe Function

**Step 1:** Copy the Pipe code
```bash
cat /mnt/user/appdata/ai_stack/openwebui/langgraph_pipe.py
```

**Step 2:** In OpenWebUI
1. Open http://192.168.0.12:8084/
2. Go to Workspace → Functions
3. Click "+" → Select "Pipe Function"
4. Paste the code from Step 1
5. Click Save

**Step 3:** Configure
- Set `LANGGRAPH_CHAT_URL` to `http://langgraph-agents:8000/chat`
- Leave other values as default
- Enable the function (toggle switch)

**Step 4:** Use it!
1. Start new chat
2. Select "LangGraph Multi-Agent System" model
3. Try: "Create a task to test the integration"
4. Then: "What task did I just create?" (it remembers! ✅)

---

## 📋 What You Get

### Working Features
✅ **50+ Tools** - Tasks, Events, Food logging, Memory, Documents
✅ **3 Specialized Agents** - Automatically route to Task/Food/Event agent
✅ **Conversation Continuity** - Same chat remembers full context
✅ **Multi-User Ready** - Uses OpenWebUI's user IDs

### Example Commands

**Task Management:**
- "Create a task to finish the project report by Friday"
- "Show me my high priority tasks"
- "Add a checklist item to the report task"

**Food Logging:**
- "Log breakfast: oatmeal with berries and coffee"
- "What did I eat yesterday?"
- "Analyze my eating patterns this week"

**Calendar/Events:**
- "Schedule a team meeting tomorrow at 2pm for 1 hour"
- "What's on my calendar today?"
- "Find available time slots this week"

**Memory & Search:**
- "Remember that I prefer morning meetings"
- "Search my notes for 'project deadline'"

---

## 🔧 Current Setup Status

### ✅ Working Right Now (Adapter Approach)
- Adapter running on port 8090
- All agents and tools functional
- API key: `change_me`

Test it:
```bash
curl -X POST http://localhost:8090/v1/chat/completions \
  -H "Authorization: Bearer change_me" \
  -H "Content-Type: application/json" \
  -d '{"model":"langgraph","messages":[{"role":"user","content":"Hello"}]}'
```

### ⚠️ Limitation
- Each request = new session (no memory across requests)
- Solution: Use Pipe Function for full continuity

---

## 📚 Full Documentation

See `INTEGRATION_GUIDE.md` for:
- Detailed comparison of both approaches
- Troubleshooting guide
- Advanced configuration
- Architecture diagrams

---

## 🆘 Quick Troubleshooting

**Pipe Function not showing in model list?**
→ Make sure it's enabled in Functions list

**Connection refused error?**
→ Use `http://langgraph-agents:8000/chat` (Docker network name)

**Timeout errors?**
→ Increase `REQUEST_TIMEOUT` in Valves to 60

**Want to see what's happening?**
→ Enable `DEBUG_MODE` in Valves, check container logs

**Made code changes to adapter?**
→ Run: `docker-compose build openwebui-adapter && docker-compose up -d openwebui-adapter`

---

## 🎯 Next Steps

1. ✅ Install Pipe Function (5 minutes)
2. ✅ Test conversation continuity
3. ✅ Try different agents (tasks, food, events)
4. 📖 Read full integration guide
5. 🔧 Customize for your workflow
