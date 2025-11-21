# Prompt Management Guide

Complete guide to finding and modifying all prompts in the multi-agent system.

---

## Prompt Locations Overview

| Node/Component | Prompt Type | Location | Format |
|---------------|-------------|----------|--------|
| **Food Agent** | System prompt | `prompts/food_agent.txt` | File |
| **Task Agent** | System prompt | `prompts/task_agent.txt` | File |
| **Event Agent** | System prompt | `prompts/event_agent.txt` | File |
| **Routing Node** | Classification prompt | `graph/routing.py:102-124` | Inline |
| **Handoff Detection** | Detection prompt | `agents/base.py:121-143` | Inline |

---

## 1. Agent System Prompts (File-Based) ✅ Easy to Edit

### **Food Agent**
```bash
File: prompts/food_agent.txt
Used by: agents/food_agent.py
Loaded at: Module initialization (once)
```

**How to change:**
```bash
cd /mnt/user/appdata/ai_stack/containers/langgraph-agents
nano prompts/food_agent.txt

# After changes, restart container:
docker restart langgraph-agents
```

**Current structure:**
```
You are a specialized Food Assistant Agent...

## Your Domain
[What you handle]

## Your Expertise
[What you know]

## Your Approach
[How you behave]

## Tools at Your Disposal
[What tools you have]

## Domain Boundaries
[When to hand off]
```

**Tips for editing:**
- Keep markdown format (## headers)
- Be specific about domain boundaries
- List all available tools
- Provide example interactions
- Define personality clearly

---

### **Task Agent**
```bash
File: prompts/task_agent.txt
Used by: agents/task_agent.py
Loaded at: Module initialization (once)
```

Same structure and editing process as Food Agent.

---

### **Event Agent**
```bash
File: prompts/event_agent.txt
Used by: agents/event_agent.py
Loaded at: Module initialization (once)
```

Same structure and editing process as Food Agent.

---

## 2. Routing Node Prompt (Code-Based) ⚠️ Requires Code Change

### **Classification/Routing Prompt**

```bash
File: graph/routing.py
Lines: 102-124
Function: llm_routing()
```

**Current prompt:**
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a routing agent that determines which specialized agent should handle a user's request.

Available agents:
- food_agent: Handles food logging, meal suggestions, dietary patterns, nutrition
- task_agent: Handles task creation, planning, productivity, todos, reminders
- event_agent: Handles calendar events, scheduling, meetings, time management
- memory_agent: Handles notes, knowledge storage, information retrieval

Analyze the user's message and determine which agent is most appropriate.
Consider:
1. The primary intent of the message
2. Which agent has the most relevant expertise
3. Context from previous conversation if available

Be decisive - pick the single most appropriate agent."""),
    ("user", """Message: {message}

Previous agent: {previous_agent}
Context: {context}

Which agent should handle this request? Provide your reasoning.""")
])
```

**How to change:**
```bash
# Edit the file
nano graph/routing.py

# Find line 103 (system message)
# Modify the prompt text
# Save and exit

# Rebuild and restart
docker build -t langgraph-agents:latest .
docker restart langgraph-agents
```

**When to modify:**
- Adding new agent types
- Changing routing criteria
- Adjusting decision factors
- Improving classification accuracy

---

### **Keyword Routing (Simple Routing)**

```bash
File: graph/routing.py
Lines: 28-49
```

**Current keywords:**
```python
FOOD_KEYWORDS = [
    "food", "meal", "eat", "ate", "eating", "lunch", "dinner", "breakfast",
    "snack", "hungry", "diet", "nutrition", "recipe", "cook", "restaurant",
    "suggest something to eat", "what should i eat", "food recommendation"
]

TASK_KEYWORDS = [
    "task", "todo", "do", "complete", "finish", "deadline", "priority",
    "remind", "reminder", "project", "work on", "need to", "have to",
    "create a task", "add task", "task list"
]

EVENT_KEYWORDS = [
    "event", "calendar", "schedule", "meeting", "appointment", "plan",
    "time", "date", "today", "tomorrow", "week", "available", "busy",
    "book", "reserve", "add to calendar"
]
```

**How to add keywords:**
```python
# Edit graph/routing.py
FOOD_KEYWORDS = [
    # ... existing keywords
    "breakfast ideas",  # Add new keyword
    "meal prep",        # Add new keyword
]

# Restart container
docker restart langgraph-agents
```

**Tips:**
- Add multi-word phrases for specific queries
- Include common typos if needed
- Keep keywords lowercase (compared with `.lower()`)
- More keywords = faster routing (avoids LLM call)

---

## 3. Handoff Detection Prompt (Code-Based) ⚠️

### **Handoff Detection System Prompt**

```bash
File: agents/base.py
Lines: 121-143
Function: detect_handoff()
```

**Current prompt:**
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a handoff detection system for a multi-agent system.

Current agent: {current_agent}

Agent domains:
- food_agent: Food, meals, eating, nutrition, dietary preferences
- task_agent: Tasks, todos, reminders, productivity, planning
- event_agent: Calendar, schedule, meetings, appointments, availability
- memory_agent: Notes, memories, information storage and retrieval

Analyze if the user's request requires a different agent.
Look for:
1. Explicit requests ("create a task", "add to calendar", etc.)
2. Domain-specific keywords
3. Context shift from current domain

Be decisive but don't over-trigger handoffs for casual mentions."""),
    ("user", """User's message: {user_message}
Agent's response: {agent_response}

Should we hand off to a different agent?""")
])
```

**How to change:**
```bash
nano agents/base.py

# Find line 122 (system message)
# Modify the prompt text
# Save and rebuild

docker build -t langgraph-agents:latest .
docker restart langgraph-agents
```

**When to modify:**
- Handoffs triggering too often (make more conservative)
- Handoffs not triggering enough (make more sensitive)
- Adding new agent domains
- Changing handoff criteria

---

## 4. Context Messages (Dynamic) 🔄

These are generated dynamically based on state, not static prompts.

### **Agent Context Message**

```bash
File: agents/base.py
Lines: 142-188
Function: create_context_message()
```

**Generated format:**
```
{system_prompt from file}

## Current Session Context

- User: {user_id}
- Session: {session_id}
- Turn: {turn_count}
- Previous Agent: {previous_agent}

## Shared Context from Other Agents

{context from other agents}

## Your Recent Context

{agent's own recent context}
```

**How to modify:**
```python
# Edit agents/base.py, function create_context_message()

def create_context_message(state, agent_name, system_prompt):
    # Modify the template string:
    context_content = f"""{system_prompt}

## Current Session Context

- User: {state['user_id']}
- Session: {state['session_id']}
# Add more fields here if needed
"""
```

---

## 5. Testing Prompt Changes

### **Quick Test (No Container Rebuild)**

For **file-based prompts** (agent system prompts):

```bash
# 1. Edit the prompt file
nano prompts/food_agent.txt

# 2. Restart container (loads new file)
docker restart langgraph-agents

# 3. Test immediately
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What should I eat?",
    "user_id": "00000000-0000-0000-0000-000000000001",
    "workspace": "default",
    "session_id": "test-prompt"
  }'
```

### **Full Test (Requires Rebuild)**

For **code-based prompts** (routing, handoff):

```bash
# 1. Edit the code
nano graph/routing.py

# 2. Rebuild container
cd /mnt/user/appdata/ai_stack
docker build -t langgraph-agents:latest containers/langgraph-agents/

# 3. Restart with new image
docker stop langgraph-agents
docker rm langgraph-agents
docker run -d --name langgraph-agents \
  --network ai-stack-network \
  -p 8080:8080 \
  --env-file .env \
  langgraph-agents:latest

# 4. Test
curl -X POST http://localhost:8080/chat ...
```

---

## 6. Best Practices for Prompt Engineering

### **Agent System Prompts**

✅ **Do:**
- Use clear section headers (##)
- Provide specific examples
- Define boundaries explicitly
- List all available tools
- Describe personality/tone
- Include handoff guidelines

❌ **Don't:**
- Make prompts too long (>1000 words)
- Use ambiguous language
- Overlap with other agents' domains
- Forget to list new tools

### **Routing Prompts**

✅ **Do:**
- Be explicit about agent capabilities
- Provide clear decision criteria
- Keep agent descriptions consistent with system prompts
- Include examples of edge cases

❌ **Don't:**
- Make descriptions too similar
- Use subjective language
- Create ambiguous boundaries

### **Handoff Detection**

✅ **Do:**
- List explicit trigger phrases
- Balance sensitivity (not too aggressive)
- Consider multi-turn context
- Test edge cases

❌ **Don't:**
- Trigger on casual mentions
- Be too conservative (miss needed handoffs)
- Forget to update when adding agents

---

## 7. Prompt Update Checklist

When modifying prompts, ensure:

- [ ] **Consistency**: All prompts use same agent names/descriptions
- [ ] **Completeness**: All agents mentioned in routing prompts
- [ ] **Testing**: Test with various message types
- [ ] **Documentation**: Update this guide if structure changes
- [ ] **Backup**: Keep copy of old prompts before major changes
- [ ] **Validation**: Check for typos, broken formatting
- [ ] **Performance**: Monitor if LLM routing accuracy changes

---

## 8. Common Prompt Modifications

### **Adding a New Agent**

1. Create new system prompt file:
   ```bash
   nano prompts/shopping_agent.txt
   ```

2. Update routing keywords:
   ```python
   # graph/routing.py
   SHOPPING_KEYWORDS = ["buy", "purchase", "shop", "store", ...]
   ```

3. Update routing LLM prompt:
   ```python
   # graph/routing.py line 106
   - shopping_agent: Handles shopping lists, purchases, product recommendations
   ```

4. Update handoff detection:
   ```python
   # agents/base.py line 127
   - shopping_agent: Shopping, purchases, products, stores
   ```

5. Update routing decision type:
   ```python
   # graph/routing.py line 22
   agent: Literal["food_agent", "task_agent", "event_agent", "shopping_agent"]
   ```

### **Changing Agent Personality**

Edit the agent's system prompt file:
```
## Your Approach

1. **Be [trait]**: [description]
2. **Be [trait]**: [description]
...

## Personality

[Detailed personality description]
```

### **Adjusting Handoff Sensitivity**

```python
# agents/base.py, line 139 (in the prompt)

# More conservative (fewer handoffs):
"Only hand off when the user explicitly requests a different domain..."

# More aggressive (more handoffs):
"Hand off whenever the user mentions topics related to other domains..."
```

---

## 9. Prompt Performance Monitoring

### **Check Routing Accuracy**

```bash
# View logs to see routing decisions
docker logs langgraph-agents -f | grep "routed to"

# Count routing to each agent
docker logs langgraph-agents | grep "routed to" | sort | uniq -c
```

### **Check Handoff Frequency**

```bash
# View handoff detections
docker logs langgraph-agents -f | grep "Handoff detected"

# Count handoffs by target
docker logs langgraph-agents | grep "Handoff detected" | cut -d'→' -f2 | sort | uniq -c
```

---

## Summary

| Prompt Type | Location | Edit Method | Requires Rebuild |
|-------------|----------|-------------|------------------|
| Agent system prompts | `prompts/*.txt` | Text editor | No (just restart) |
| Routing classification | `graph/routing.py` | Code editor | Yes |
| Routing keywords | `graph/routing.py` | Code editor | Yes |
| Handoff detection | `agents/base.py` | Code editor | Yes |
| Context messages | `agents/base.py` | Code editor | Yes |

**Quick Changes:** Edit `prompts/*.txt` files → restart container
**Advanced Changes:** Edit `.py` files → rebuild → restart container

---

**Pro Tip:** Keep a changelog of prompt modifications to track what works best!
