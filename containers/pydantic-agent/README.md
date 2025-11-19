# Pydantic AI Agent Service

Intelligent conversational agent middleware for AI Stack. This service sits between AnythingLLM and your tools (n8n webhooks, database), providing:

- 🧠 **Intent Understanding**: Parses natural language requests
- ❓ **Clarifying Questions**: Asks when information is missing or ambiguous
- ✅ **Validation**: Ensures data is complete before executing actions
- 💡 **Smart Suggestions**: Offers helpful defaults and improvements
- 💬 **Conversation Memory**: Maintains context across multiple turns
- 🔧 **Tool Orchestration**: Calls appropriate tools (n8n, database) to complete requests

## Architecture

```
AnythingLLM (User Interface)
    ↓
Pydantic AI Agent (This Service)
    ↓ evaluates, clarifies, validates
    ↓
Tools:
    - n8n webhooks (complex workflows with embeddings)
    - Direct database (simple CRUD operations)
    ↓
PostgreSQL + Qdrant
```

## Why This Service?

**Without agent layer (direct to n8n):**
```
You: "Add a task"
n8n: ERROR - Missing title

You: "Add task to call dentist"
n8n: Created (but no due date, no reminder, incomplete)
```

**With agent layer:**
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

## Available Tools

The agent has access to these tools:

### Task Management
- `create_task` - Create new tasks with validation
- `search_tasks` - Search tasks by status, priority, due date
- `get_tasks_today` - Get today's tasks
- `update_task` - Update existing tasks

### Reminders
- `create_reminder` - Create reminders with time parsing

### Calendar
- `get_events_today` - Get today's calendar events

### Food Logging
- `log_food` - Log meals with ratings (calls n8n for embedding)

## API Endpoints

### `POST /chat`
Main conversational endpoint. Handles all user requests.

**Request:**
```json
{
  "message": "Help me plan my day",
  "conversation_id": "user-123-session",
  "user_id": "00000000-0000-0000-0000-000000000001"
}
```

**Response:**
```json
{
  "response": "Here's your day:\n\n📅 Events:...",
  "conversation_id": "user-123-session"
}
```

### `GET /health`
Health check endpoint showing service status.

### `DELETE /conversation/{conversation_id}`
Clear conversation history for a specific session.

## Environment Variables

```bash
# Database
POSTGRES_HOST=postgres-ai-stack
POSTGRES_PORT=5432
POSTGRES_DB=aistack
POSTGRES_USER=aistack_user
POSTGRES_PASSWORD=changeme

# n8n
N8N_BASE_URL=http://n8n:5678/webhook

# Ollama
OLLAMA_MODEL=ollama:llama3.2:3b
OLLAMA_BASE_URL=http://ollama-ai-stack:11434

# Default user
DEFAULT_USER_ID=00000000-0000-0000-0000-000000000001
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export N8N_BASE_URL=http://localhost:5678/webhook
export OLLAMA_BASE_URL=http://localhost:11434

# Run the service
python main.py
```

Service runs on http://localhost:8000

## Running with Docker

```bash
# Build image
docker build -t pydantic-agent:latest .

# Run container
docker run -d \
  --name pydantic-agent-ai-stack \
  --network ai-stack-network \
  -p 8000:8000 \
  -e POSTGRES_HOST=postgres-ai-stack \
  -e N8N_BASE_URL=http://n8n:5678/webhook \
  -e OLLAMA_BASE_URL=http://ollama-ai-stack:11434 \
  pydantic-agent:latest
```

## Testing the Agent

```bash
# Health check
curl http://localhost:8000/health

# Chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a task to call dentist next Friday",
    "conversation_id": "test-session"
  }'

# Multi-turn conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me my day",
    "conversation_id": "daily-planning"
  }'

# Follow-up in same conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Move the blog task to tomorrow",
    "conversation_id": "daily-planning"
  }'
```

## Conversation Examples

### Example 1: Task Creation with Clarification
```
User: "Add a task"
Agent: "I'd be happy to help! What task would you like to add?"

User: "Call dentist"
Agent: "Got it - call dentist. A few questions:
       - When do you need to do this by?
       - Is this urgent, or can it wait?
       - Would you like a reminder?"

User: "It's urgent"
Agent: "Since it's urgent, I'd suggest:
       - Due: Tomorrow
       - Priority: High
       - Reminder: In 1 hour
       Sound good?"

User: "Yes"
Agent: "✓ Created: 'Call dentist' (Due: Tomorrow, Priority: High)
       ✓ Reminder: Today at 3pm"
```

### Example 2: Daily Planning
```
User: "Show me my day"
Agent: [Uses get_tasks_today and get_events_today tools]
       "Here's your day:

       📅 Events:
       - Team meeting: 10am-11am
       - Dentist: 2pm

       ✅ Tasks (3 due):
       1. [HIGH] Finish proposal (~2 hours)
       2. [MEDIUM] Review PR (~30 min)
       3. [LOW] Water plants (~10 min)

       Need help prioritizing?"

User: "Move the plants to weekend"
Agent: [Uses update_task tool]
       "✓ Moved 'Water plants' to Saturday
       That leaves 2 tasks for today. More manageable!"
```

### Example 3: Food Logging
```
User: "Log that I ate food"
Agent: "I can log that! To make it useful, could you tell me:
       - What did you eat?
       - When? (breakfast, lunch, dinner, snack)
       - How would you rate it?"

User: "Had sushi for lunch, it was amazing"
Agent: "Sushi for lunch - nice! On a scale of 1-5, how would you rate it?"

User: "5 out of 5"
Agent: "Awesome! Before I log it:
       - Did you make it or buy it?
       - Want to add tags?"

User: "Bought it, add #japanese #seafood"
Agent: [Uses log_food tool → calls n8n → embeds → stores in Qdrant]
       "✓ Logged: Sushi (Lunch, 5/5, bought, #japanese #seafood)
       When you ask for recommendations, I'll remember you loved this!"
```

## Adding New Tools

To add a new tool:

```python
@task_agent.tool
async def your_new_tool(
    ctx: RunContext[AgentDependencies],
    param1: str,
    param2: Optional[int] = None
) -> str:
    """
    Tool description - the agent uses this to decide when to call it.

    Args:
        param1: Description of parameter
        param2: Optional parameter

    Returns:
        Result message
    """
    # Use ctx.deps to access database or call n8n
    result = await ctx.deps.call_n8n("endpoint", {"data": param1})

    return f"Tool executed: {result}"
```

The agent will automatically:
- Understand when to use this tool
- Extract parameters from user messages
- Validate before calling
- Handle errors

## Logs

The service logs all interactions:

```
2025-11-19 10:30:15 - pydantic_agent - INFO - Started new conversation: user-123
2025-11-19 10:30:16 - pydantic_agent - INFO - [user-123] User: Create a task to call dentist...
2025-11-19 10:30:17 - pydantic_agent - INFO - Created task: abc-123 - Call dentist
2025-11-19 10:30:17 - pydantic_agent - INFO - [user-123] Agent: ✓ Task created...
```

## Troubleshooting

**Agent not calling tools:**
- Check system prompt includes current date/time
- Verify tool docstrings are clear
- Check Ollama model is loaded: `docker exec ollama-ai-stack ollama list`

**Database errors:**
- Verify PostgreSQL is running and accessible
- Check environment variables are correct
- Test connection: `docker exec pydantic-agent curl http://postgres-ai-stack:5432`

**n8n webhook errors:**
- Verify n8n workflows are imported and active
- Check webhook URLs match: `/webhook/create-task` etc.
- Test webhook directly: `curl http://n8n:5678/webhook/create-task`

**Conversation context not maintained:**
- Check conversation_id is consistent across messages
- Verify conversation_store is not being cleared

## Next Steps

1. **Test the agent** - Deploy and try various requests
2. **Add more tools** - Extend functionality as needed
3. **Integrate with AnythingLLM** - Create ai-assistant skill
4. **Monitor performance** - Check response times and adjust prompts
5. **Iterate** - Refine system prompt based on agent behavior

## License

MIT License
