# Pydantic AI Agent - Deployment & Usage Guide

> **⚠️ Standalone Installation:** The Pydantic AI agent is now installed as a **separate container** outside the main AI Stack. See the "Deployment" section below for installation instructions from the repository.

This guide explains the intelligent agent layer for your AI Stack.

## 📋 Table of Contents

1. [What Is This?](#what-is-this)
2. [Architecture](#architecture)
3. [Why Add an Agent Layer?](#why-add-an-agent-layer)
4. [Deployment](#deployment)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## What Is This?

**Pydantic AI Agent** is an intelligent conversational middleware that sits between AnythingLLM and your tools (n8n webhooks, database).

### Before (Direct to n8n):
```
You: "Add a task"
n8n: ERROR - Missing title

You: "Add task to call dentist"
n8n: Created (but no due date, no reminder, incomplete)
```

### After (With Agent Layer):
```
You: "Add a task"
Agent: "What task would you like to add?"

You: "Call dentist"
Agent: "When do you need to do this? Is it urgent?"

You: "Not sure when, but it's urgent"
Agent: "Since it's urgent, I'd suggest:
       - Due: End of this week
       - Priority: High
       - Reminder: Tomorrow morning
       Sound good?"

You: "Perfect"
Agent: ✓ Created with all details + reminder
```

---

## Architecture

### Old Architecture (Direct):
```
┌─────────────────┐
│  AnythingLLM    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  n8n Webhooks   │ (No validation, no questions)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘
```

### New Architecture (With Agent Layer):
```
┌─────────────────────────┐
│     AnythingLLM         │
│  (User Interface)       │
└───────────┬─────────────┘
            │
            │ All requests
            ▼
┌─────────────────────────┐
│  Pydantic AI Agent      │
│  (Intelligent Layer)    │
│                         │
│  • Evaluates intent     │
│  • Asks questions       │
│  • Validates data       │
│  • Suggests defaults    │
│  • Maintains context    │
└───────────┬─────────────┘
            │
            │ Only when ready
            │
  ┌─────────┴─────────┐
  │                   │
  ▼                   ▼
┌──────────┐    ┌──────────┐
│   n8n    │    │  Direct  │
│ Webhooks │    │ Database │
│          │    │          │
│(Complex) │    │ (Simple) │
└────┬─────┘    └─────┬────┘
     │                │
     └────────┬───────┘
              ▼
      ┌──────────────┐
      │  PostgreSQL  │
      │   + Qdrant   │
      └──────────────┘
```

---

## Why Add an Agent Layer?

### 1. **Validation & Error Prevention**
```
You: "Create reminder at 25:00"
Agent: "I don't think 25:00 is valid. Did you mean 23:00?"
```
Instead of: Database corruption

### 2. **Intelligent Defaults**
```
You: "Create task to buy groceries"
Agent: "Got it. Since you didn't specify:
       - Due date: This weekend
       - Priority: Medium
       - Want a reminder Friday evening?"
```

### 3. **Clarifying Questions**
```
You: "Log that I ate food"
Agent: "I can log that! What did you eat?
       When? How would you rate it?"
```

### 4. **Context Awareness**
```
You: "Show me my day"
Agent: [Shows tasks and events]

You: "Move it to tomorrow"
Agent: [Knows "it" = last mentioned task]
       "Moving 'Call dentist' to tomorrow"
```

### 5. **Multi-Step Conversations**
```
You: "Help me plan my week"
Agent: [Analyzes calendar, tasks, patterns]
       "Here's what I suggest... Want to adjust anything?"

You: "Move Monday's tasks to Tuesday"
Agent: [Updates multiple tasks]
       "Done! Anything else?"
```

---

## Deployment

### Step 1: Build the Agent Container

```bash
# Navigate to agent directory
# Clone repository for standalone installation
git clone https://github.com/sulaljuhani/ai_assistant_local_stack.git /mnt/user/appdata/pydantic-agent-source
cd /mnt/user/appdata/pydantic-agent-source/containers/pydantic-agent

# Build image
docker build -t pydantic-agent:latest .
```

### Step 2: Deploy on unRAID

**Option A: Using Template (Recommended)**

1. Copy template: `unraid-templates/my-pydantic-agent.xml`
2. In unRAID: Docker → Add Container → Template: pydantic-agent
3. Configure:
   - Port: 8000
   - Network: ai-stack-network
   - PostgreSQL host: postgres-ai-stack
   - PostgreSQL password: (your password)
   - n8n URL: http://n8n:5678/webhook
   - Ollama model: ollama:llama3.2:3b
4. Apply

**Option B: Manual Docker Command**

```bash
docker run -d \
  --name pydantic-agent-ai-stack \
  --network ai-stack-network \
  -p 8000:8000 \
  -e POSTGRES_HOST=postgres-ai-stack \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=aistack \
  -e POSTGRES_USER=aistack_user \
  -e POSTGRES_PASSWORD=your_password \
  -e N8N_BASE_URL=http://n8n:5678/webhook \
  -e OLLAMA_MODEL=ollama:llama3.2:3b \
  -e OLLAMA_BASE_URL=http://ollama-ai-stack:11434 \
  -e DEFAULT_USER_ID=00000000-0000-0000-0000-000000000001 \
  --restart unless-stopped \
  pydantic-agent:latest
```

### Step 3: Verify Deployment

```bash
# Check container is running
docker ps | grep pydantic-agent

# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "model": "ollama:llama3.2:3b",
#   "n8n_base_url": "http://n8n:5678/webhook",
#   "conversations_active": 0
# }
```

### Step 4: Import AnythingLLM Skill

1. Open AnythingLLM: http://your-server:3001
2. Go to: Settings → Agent Configuration → Agent Skills
3. Click: "Import Custom Skill"
4. Upload: `anythingllm-skills/ai-assistant.js`
5. Enable the skill in your workspace
6. (Optional) Disable old skills: create-task, create-reminder, log-food

### Step 5: Test the Agent

In AnythingLLM, try:

```
You: "Create a task"
```

The agent should respond with a question, not an error!

---

## Usage Examples

### Example 1: Task Creation with Clarification

```
You: "Add a task"

Agent: "I'd be happy to help! What task would you like to add?"

You: "Call dentist"

Agent: "Got it - call dentist. A few questions:
       - When do you need to do this by?
       - Is this urgent, or can it wait?
       - Would you like a reminder?"

You: "Urgent, but not sure when"

Agent: "Since it's urgent but no specific date, I'd suggest:
       - Due date: End of this week (Friday)
       - Priority: High
       - Reminder: Tomorrow morning
       Sound good?"

You: "Perfect"

Agent: "✓ Created: 'Call dentist'
       - Due: Friday Dec 22
       - Priority: High
       - Reminder: Tomorrow 9am

       Anything else?"
```

### Example 2: Daily Planning

```
You: "Show me my day"

Agent: [Uses get_tasks_today and get_events_today tools]

       "Here's your day:

       📅 Events:
       - Team meeting: 10am-11am
       - Dentist: 2pm

       ✅ Tasks (5 due):
       1. [HIGH] Finish proposal (~2 hours)
       2. [MEDIUM] Review PR (~30 min)
       3. [MEDIUM] Call insurance (~15 min)
       4. [LOW] Update blog (~1 hour)
       5. [LOW] Water plants (~10 min)

       You have 2 hours of meetings and ~4 hours of tasks.
       Need help prioritizing?"

You: "Yeah, I don't think I can finish the blog today"

Agent: [Uses update_task tool]

       "No problem! I'll move 'Update blog' to tomorrow.

       That leaves 3.5 hours of tasks, more manageable.

       Better?"

You: "Yes, remind me about the proposal at 9am"

Agent: [Uses create_reminder tool]

       "✓ Created reminder for 9am: 'Start proposal'
       You're all set!"
```

### Example 3: Food Logging

```
You: "Log that I ate food"

Agent: "I can log that! To make it useful:
       - What did you eat?
       - When? (breakfast, lunch, dinner, snack)
       - How would you rate it?"

You: "Had sushi for lunch, it was amazing"

Agent: "Sushi for lunch - nice! On a scale of 1-5?"

You: "5 out of 5"

Agent: "Awesome! Before I log it:
       - Did you make it or buy it?
       - Any specific type?
       - Want to add tags?"

You: "Bought it, salmon sashimi, yes add #japanese #seafood"

Agent: [Uses log_food tool → n8n → embeds → Qdrant]

       "✓ Logged: Salmon sashimi
       - Time: Lunch
       - Rating: 5/5
       - Source: Bought
       - Tags: #japanese, #seafood

       When you ask for recommendations, I'll remember you loved this!"
```

### Example 4: Ambiguous Request

```
You: "Create task to finish project next Friday"

Agent: "I can create that. Just to confirm - today is Tuesday Dec 19.

       By 'next Friday' do you mean:
       - This Friday (Dec 22) - 3 days away
       - Friday of next week (Dec 29) - 10 days away?"

You: "Dec 29"

Agent: "Perfect. Task: 'Finish project'
       Due: Friday December 29

       This is 10 days away. Would you like:
       - A reminder a few days before?
       - High priority?
       - Details about which project?"

You: "Yes reminder 2 days before, Q4 report"

Agent: "✓ Created:
       - Task: 'Finish Q4 report'
         Due: Friday Dec 29
       - Reminder: Wednesday Dec 27

       All set!"
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | postgres-ai-stack | PostgreSQL container hostname |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | aistack | Database name |
| `POSTGRES_USER` | aistack_user | Database username |
| `POSTGRES_PASSWORD` | - | Database password (required) |
| `N8N_BASE_URL` | http://n8n:5678/webhook | n8n webhook base URL |
| `OLLAMA_MODEL` | ollama:llama3.2:3b | Ollama model for agent |
| `OLLAMA_BASE_URL` | http://ollama-ai-stack:11434 | Ollama API URL |
| `DEFAULT_USER_ID` | 00000000... | Single-user mode UUID |

### Adjusting System Prompt

Edit the agent source in your cloned repository (`/mnt/user/appdata/pydantic-agent-source/containers/pydantic-agent/main.py`):

```python
task_agent = Agent(
    OLLAMA_MODEL,
    system_prompt='''Your custom prompt here...

    Be more/less verbose
    Focus on specific behaviors
    Adjust tone (formal/casual)
    '''
)
```

Rebuild container after changes:
```bash
docker stop pydantic-agent-ai-stack
docker rm pydantic-agent-ai-stack
# Clone repository for standalone installation
git clone https://github.com/sulaljuhani/ai_assistant_local_stack.git /mnt/user/appdata/pydantic-agent-source
cd /mnt/user/appdata/pydantic-agent-source/containers/pydantic-agent
docker build -t pydantic-agent:latest .
# Redeploy using template or docker run
```

---

## Troubleshooting

### Agent Service Won't Start

**Check logs:**
```bash
docker logs pydantic-agent-ai-stack
```

**Common issues:**
- PostgreSQL not accessible → Check network and credentials
- Ollama not running → `docker ps | grep ollama`
- Port 8000 in use → Change port in template

### "Can't connect to agent service" in AnythingLLM

**Verify agent is running:**
```bash
docker ps | grep pydantic-agent
```

**Test from AnythingLLM container:**
```bash
docker exec anythingllm-ai-stack curl http://pydantic-agent:8000/health
```

**Check network:**
```bash
docker network inspect ai-stack-network | grep pydantic-agent
```

### Agent Not Asking Questions

**Check Ollama model is loaded:**
```bash
docker exec ollama-ai-stack ollama list
```

**Should see:**
```
NAME              SIZE
llama3.2:3b      2.0 GB
```

**If missing:**
```bash
docker exec ollama-ai-stack ollama pull llama3.2:3b
```

**Check agent logs:**
```bash
docker logs -f pydantic-agent-ai-stack
```

Look for tool calls and responses.

### Conversations Not Connected

**View active conversations:**
```bash
curl http://localhost:8000/conversations
```

**Clear a stuck conversation:**
```bash
curl -X DELETE http://localhost:8000/conversation/anythingllm-workspace
```

### Agent Calling Wrong Tools

**Check tool docstrings in `main.py`** - They guide the agent's decisions

**Review logs to see reasoning:**
```bash
docker logs pydantic-agent-ai-stack | grep "tool_name"
```

**Adjust system prompt** to be more specific about when to use which tools

---

## Advanced Topics

### Adding New Tools

Edit the agent source in your cloned repository (`/mnt/user/appdata/pydantic-agent-source/containers/pydantic-agent/main.py`):

```python
@task_agent.tool
async def your_new_tool(
    ctx: RunContext[AgentDependencies],
    param1: str,
    param2: Optional[int] = None
) -> str:
    """
    Clear description of what this tool does.
    The agent uses this docstring to decide when to call it.

    Args:
        param1: Description
        param2: Optional parameter

    Returns:
        Result message
    """
    # Use ctx.deps to access database or n8n
    result = await ctx.deps.call_n8n("endpoint", {"data": param1})

    return f"Tool executed: {result}"
```

Rebuild and redeploy container.

### Using Different LLM Models

**Change model in template or environment:**
```bash
OLLAMA_MODEL=ollama:llama3.1:8b
```

**Or use cloud models (OpenAI, Anthropic):**

Edit `main.py`:
```python
# Change from
task_agent = Agent(OLLAMA_MODEL, ...)

# To
task_agent = Agent('openai:gpt-4', ...)
```

Set API key:
```bash
OPENAI_API_KEY=your-key
```

### Monitoring and Logging

**View real-time logs:**
```bash
docker logs -f pydantic-agent-ai-stack
```

**Check conversation stats:**
```bash
curl http://localhost:8000/health
```

**Export logs:**
```bash
docker logs pydantic-agent-ai-stack > agent-logs.txt
```

### Scaling Considerations

**Current setup:**
- Single instance
- In-memory conversation store
- Good for 1-10 users

**For more users:**
- Use Redis for conversation storage
- Add multiple agent instances
- Implement load balancing

---

## What's Next?

1. **Test thoroughly** - Try various requests and conversations
2. **Adjust system prompt** - Fine-tune based on behavior
3. **Add more tools** - Extend functionality as needed
4. **Monitor usage** - Check logs and adjust
5. **Iterate** - Refine based on experience

---

## Architecture Comparison

### Simple CRUD (Keep n8n)

✅ Direct, fast, deterministic

```
"Create task: Call dentist, Friday, High priority"
→ n8n webhook
→ Done
```

### Complex/Conversational (Use Agent)

✅ Smart, flexible, validating

```
"Help me plan my day"
→ Agent analyzes
→ Multi-turn conversation
→ Adjustments
→ Completion
```

---

## Support

**Documentation:**
- `unraid-templates/my-pydantic-agent.xml` - Standalone installation template
- `anythingllm-skills/ai-assistant.js` - Skill documentation

**Logs:**
```bash
docker logs pydantic-agent-ai-stack
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

---

Built with ❤️ for your AI Stack
