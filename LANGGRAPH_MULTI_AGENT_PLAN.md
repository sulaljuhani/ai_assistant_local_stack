# LangGraph Multi-Agent Implementation Plan

**Date:** 2025-11-19
**Purpose:** Implement specialized agents using LangGraph for domain-specific expertise
**Replaces:** Single Pydantic AI agent with multiple specialized agents

---

## 🎯 Goals

1. **Specialized Agents** - Each agent is an expert in one domain (food, tasks, events, etc.)
2. **Direct DB Access** - Agents use tools for structured queries + vector search for semantic operations
3. **Intelligent Handoffs** - Agents can hand off to each other when needed
4. **State Management** - Shared state across agents for context preservation
5. **No Required Router** - AnythingLLM or first agent determines routing

---

## 🏗️ Architecture

### **Current (Pydantic AI - Single Agent):**
```
AnythingLLM
    ↓
Single Agent (does everything)
    ↓ Has all tools
    ↓
Tools (n8n/DB)
```

### **Proposed (LangGraph - Multi-Agent):**
```
AnythingLLM
    ↓
┌─────────────────────────────────┐
│      LangGraph Orchestrator     │
│                                 │
│  ┌──────────┐  ┌──────────┐   │
│  │   Food   │  │   Task   │   │
│  │  Agent   │  │  Agent   │   │
│  └────┬─────┘  └────┬─────┘   │
│       │             │          │
│  ┌────┴─────┐  ┌────┴─────┐   │
│  │  Event   │  │  Memory  │   │
│  │  Agent   │  │  Agent   │   │
│  └──────────┘  └──────────┘   │
└─────────────────────────────────┘
    ↓
Tools (DB/n8n/Qdrant)
```

---

## 🤖 Agent Specifications

### **1. Food Agent**

**Domain:** Food logging, meal suggestions, dietary patterns

**Responsibilities:**
- Log food entries with full details
- Suggest meals based on history, ratings, recency
- Analyze eating patterns
- Handle dietary preferences and restrictions
- Generate shopping lists

**Tools:**
- `search_food_log(filters)` - Direct DB query (structured)
- `get_food_by_rating(min_rating, days_ago)` - Direct DB
- `log_food_entry(details)` - Insert to DB + n8n for embedding
- `update_food_entry(id, changes)` - Direct DB
- `vector_search_similar_foods(description)` - Qdrant semantic search
- `analyze_food_patterns(timeframe)` - Direct DB aggregation
- `get_food_recommendations(preferences)` - Hybrid: DB + vector search

**Data Access:**
- **Structured queries:** PostgreSQL food_log table
- **Semantic search:** Qdrant food_memories collection
- **Embeddings:** Via n8n workflow (existing)

**System Prompt Focus:**
- Expert in nutrition and food preferences
- Conversational and iterative suggestions
- Respects dietary restrictions
- Considers variety and balance

**Handoff Triggers:**
- User asks about tasks → Task Agent
- User asks about calendar → Event Agent
- User asks to create reminder → Task Agent
- User asks about notes/memories → Memory Agent

---

### **2. Task Agent**

**Domain:** Task management, planning, productivity

**Responsibilities:**
- Create tasks with intelligent defaults
- Update and organize tasks
- Suggest task prioritization
- Break down complex projects
- Daily/weekly planning

**Tools:**
- `create_task(details)` - Direct DB or n8n webhook
- `search_tasks(filters)` - Direct DB
- `update_task(id, changes)` - Direct DB
- `get_tasks_by_priority(priority)` - Direct DB
- `get_tasks_due_soon(days)` - Direct DB
- `analyze_task_patterns()` - Direct DB aggregation
- `suggest_task_breakdown(description)` - LLM reasoning + DB context

**Data Access:**
- **Structured queries:** PostgreSQL tasks table
- **Context:** Check calendar (via Event Agent) for deadline conflicts

**System Prompt Focus:**
- Productivity expert
- Helps with planning and organization
- Asks about priorities and deadlines
- Suggests realistic timelines

**Handoff Triggers:**
- User mentions food/meals → Food Agent
- User asks about calendar/schedule → Event Agent
- User wants to take notes → Memory Agent

---

### **3. Event Agent**

**Domain:** Calendar management, scheduling, time blocking

**Responsibilities:**
- Create calendar events
- Check schedule conflicts
- Suggest meeting times
- Time block planning
- Reminder coordination

**Tools:**
- `create_event(details)` - Direct DB or n8n
- `search_events(date_range, filters)` - Direct DB
- `get_events_today()` - Direct DB
- `get_events_week()` - Direct DB
- `check_time_conflicts(start, end)` - Direct DB
- `suggest_available_times(date, duration)` - Direct DB logic

**Data Access:**
- **Structured queries:** PostgreSQL events table
- **Context:** Check tasks (via Task Agent) for workload

**System Prompt Focus:**
- Scheduling expert
- Prevents conflicts
- Suggests optimal meeting times
- Considers work-life balance

**Handoff Triggers:**
- User asks about tasks → Task Agent
- User mentions food/meals → Food Agent
- User wants to remember something → Memory Agent

---

### **4. Memory Agent (Optional/Future)**

**Domain:** Note-taking, memory search, knowledge organization

**Responsibilities:**
- Store notes and memories
- Semantic search across memories
- Connect related concepts
- Organize knowledge
- Retrieve context

**Tools:**
- `store_memory(content, sector)` - OpenMemory + Qdrant
- `search_memories(query)` - Vector search
- `get_related_memories(id)` - Vector similarity
- `search_notes(keywords)` - Direct DB
- `organize_notes_by_topic()` - LLM + vector clustering

**Data Access:**
- **Semantic search:** OpenMemory + Qdrant
- **Structured notes:** PostgreSQL notes table
- **Obsidian vault:** File system + embeddings

**System Prompt Focus:**
- Knowledge management expert
- Helps connect ideas
- Surfaces relevant context
- Organizes information

**Handoff Triggers:**
- User asks about tasks → Task Agent
- User asks about schedule → Event Agent
- User mentions food → Food Agent

---

## 🔄 LangGraph State Design

### **Shared State Structure:**

```python
class MultiAgentState(TypedDict):
    # Conversation
    messages: Annotated[list, "Full conversation history"]
    current_agent: str  # Which agent is active

    # User context
    user_id: str
    workspace: str

    # Domain contexts (agents populate these)
    food_context: dict  # Recent food discussions
    task_context: dict  # Active task planning
    event_context: dict  # Calendar context

    # Handoff metadata
    handoff_reason: Optional[str]
    target_agent: Optional[str]

    # Results
    pending_actions: list  # Actions to execute
    completed_actions: list
```

### **State Updates:**

Each agent can:
- **Read:** Full state (see what other agents discussed)
- **Write:** Its own domain context
- **Update:** Messages, current_agent, handoff signals

**Example Flow:**
```
User: "Suggest something to eat"

State = {
    messages: ["Suggest something to eat"],
    current_agent: "food_agent",
    food_context: {},
    ...
}

Food Agent updates:
    food_context: {
        "suggested_items": ["Thai curry", "Sushi"],
        "rejected": [],
        "preferences": "hasn't had in a while"
    }

User: "Not Thai, something else"

Food Agent updates:
    food_context: {
        "suggested_items": ["Sushi", "Mexican"],
        "rejected": ["Thai curry"],
        ...
    }

User: "Create a task to buy groceries"

Food Agent detects handoff:
    target_agent: "task_agent"
    handoff_reason: "User wants to create task for groceries"

Task Agent receives state:
    Can see food_context (knows about food discussion)
    Creates grocery task with context
```

---

## 🔀 Routing & Handoff Logic

### **Option 1: First-Agent Routing (Recommended)**

```
AnythingLLM → LangGraph Entry Point
    ↓
    Routing Node (lightweight decision)
    ↓
    ├─→ Food Agent
    ├─→ Task Agent
    ├─→ Event Agent
    └─→ Memory Agent
```

**Routing logic:**
- Analyze first message
- Determine primary domain (food, task, event, memory)
- Route to specialist
- Specialist can hand off if needed

---

### **Option 2: No Router (Direct Skills)**

```
AnythingLLM decides
    ↓
    ├─→ food-assistant.js → Food Agent
    ├─→ task-assistant.js → Task Agent
    └─→ event-assistant.js → Event Agent
```

**Each skill talks to separate LangGraph instance**
- Simpler initial routing
- Handoffs happen within LangGraph
- AnythingLLM picks initial agent via skills

---

### **Handoff Mechanism:**

Each agent has a **handoff detector**:

```python
def should_handoff(messages, current_domain):
    """Detect if user switched domains"""
    last_message = messages[-1]

    # Keyword detection
    if current_domain == "food":
        if any(word in last_message for word in ["task", "todo", "remind"]):
            return "task_agent"
        if any(word in last_message for word in ["calendar", "schedule", "meeting"]):
            return "event_agent"

    # Or use LLM to decide
    decision = llm.run(
        f"User was talking about {current_domain}. "
        f"New message: {last_message}. "
        f"Should we handoff to another agent? Which one?"
    )

    return decision.target_agent or "continue"
```

---

## 🛠️ Tool Implementation Strategy

### **Shared Tool Layer:**

All agents access the same tool functions, but each agent only "knows about" relevant tools.

```python
# tools/database.py
async def search_food_log(filters):
    """Direct PostgreSQL query"""

async def search_tasks(filters):
    """Direct PostgreSQL query"""

async def search_events(filters):
    """Direct PostgreSQL query"""

# tools/vector.py
async def vector_search_foods(query):
    """Qdrant semantic search"""

async def vector_search_memories(query):
    """OpenMemory + Qdrant"""

# tools/hybrid.py
async def get_food_recommendations(preferences):
    """Combines DB query + vector search"""
    # 1. DB: Get foods matching criteria
    # 2. Vector: Find semantically similar
    # 3. Merge and rank
```

### **Tool Registration per Agent:**

```python
# Food Agent sees these tools
food_tools = [
    search_food_log,
    log_food_entry,
    vector_search_foods,
    get_food_recommendations,
    analyze_food_patterns
]

# Task Agent sees these tools
task_tools = [
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    analyze_task_patterns
]
```

### **DB Access Patterns:**

**Structured Data (Use Direct SQL):**
- Getting all tasks due today
- Filtering food by rating
- Searching events by date
- Aggregating statistics

**Unstructured/Semantic (Use Vector Search):**
- "Find foods similar to Thai curry"
- "Search memories about Docker"
- "Foods I might like based on past preferences"
- "Notes related to this topic"

**Hybrid (Both):**
- Food recommendations: DB for filters + vector for similarity
- Task suggestions: DB for context + LLM for breakdown
- Memory retrieval: Vector for search + DB for metadata

---

## 📦 Implementation Phases

### **Phase 1: Foundation (Week 1)**

**Goal:** Set up LangGraph infrastructure

**Tasks:**
1. Install LangGraph dependencies
2. Define shared state schema
3. Create base agent class
4. Implement simple routing node
5. Build one agent (Food Agent) as proof of concept
6. Test basic conversation flow

**Deliverables:**
- `containers/langgraph-agents/` directory structure
- Base state management
- Food Agent working with 3 tools
- Simple routing logic

**Success Criteria:**
- Can route to Food Agent
- Food Agent can log food
- Food Agent can suggest meals
- Conversation maintains context

---

### **Phase 2: Multi-Agent (Week 2)**

**Goal:** Add Task and Event agents

**Tasks:**
1. Implement Task Agent with tools
2. Implement Event Agent with tools
3. Add handoff logic between agents
4. Test agent-to-agent handoffs
5. Refine state management

**Deliverables:**
- Task Agent with 5 tools
- Event Agent with 4 tools
- Handoff mechanism working
- State preservation across agents

**Success Criteria:**
- Can discuss food, then switch to tasks
- Task Agent sees food context
- All three agents can handoff smoothly
- State is preserved

---

### **Phase 3: Tool Enhancement (Week 3)**

**Goal:** Add vector search and hybrid tools

**Tasks:**
1. Integrate Qdrant vector search
2. Implement hybrid recommendation tools
3. Add OpenMemory integration (optional)
4. Optimize DB queries
5. Add caching layer

**Deliverables:**
- Vector search working for food
- Hybrid food recommendations
- Performance optimizations
- Tool response times < 500ms

**Success Criteria:**
- Semantic food search works
- Recommendations are intelligent
- Fast response times
- No redundant DB calls

---

### **Phase 4: AnythingLLM Integration (Week 4)**

**Goal:** Connect to AnythingLLM

**Tasks:**
1. Create AnythingLLM skills for each agent
2. Add conversation ID management
3. Test full flow from chat to agents
4. Add error handling
5. Polish UX

**Deliverables:**
- 3 AnythingLLM skills (food, task, event)
- Proper error messages
- Conversation continuity
- User documentation

**Success Criteria:**
- Works from AnythingLLM chat
- Errors are graceful
- Handoffs are smooth
- Users understand which agent is active

---

### **Phase 5: Polish & Production (Week 5)**

**Goal:** Production-ready deployment

**Tasks:**
1. Add comprehensive logging
2. Implement monitoring
3. Create health checks
4. Write deployment docs
5. Performance testing
6. Security review

**Deliverables:**
- Structured logging for all agents
- Health check endpoints
- Deployment guide
- Performance benchmarks
- Security audit

**Success Criteria:**
- Can deploy on unRAID
- Logs are useful for debugging
- Performance is acceptable (< 2s responses)
- No security vulnerabilities

---

## 🗂️ File Structure

```
containers/langgraph-agents/
├── main.py                    # FastAPI entry point
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container build
├── README.md                  # Documentation
│
├── graph/
│   ├── __init__.py
│   ├── state.py              # State schema
│   ├── workflow.py           # LangGraph workflow definition
│   └── routing.py            # Routing logic
│
├── agents/
│   ├── __init__.py
│   ├── base.py               # Base agent class
│   ├── food_agent.py         # Food specialist
│   ├── task_agent.py         # Task specialist
│   ├── event_agent.py        # Event specialist
│   └── memory_agent.py       # Memory specialist (optional)
│
├── tools/
│   ├── __init__.py
│   ├── database.py           # Direct DB queries
│   ├── vector.py             # Qdrant vector search
│   ├── hybrid.py             # Hybrid DB + vector
│   └── n8n.py                # n8n webhook calls
│
├── prompts/
│   ├── food_agent.txt        # System prompts
│   ├── task_agent.txt
│   └── event_agent.txt
│
└── utils/
    ├── __init__.py
    ├── db.py                 # Database connection
    ├── logging.py            # Structured logging
    └── monitoring.py         # Health checks
```

---

## 🔌 Technology Stack

### **Core:**
- **LangGraph** 0.2.x - Multi-agent orchestration
- **LangChain** 0.3.x - LLM framework (LangGraph dependency)
- **FastAPI** 0.115.0 - API service
- **Python** 3.11 - Runtime

### **Database:**
- **asyncpg** 0.29.0 - PostgreSQL async driver
- **qdrant-client** 1.7.x - Vector search

### **LLM:**
- **Ollama** - Local inference (llama3.2:3b or llama3.1:8b)
- **OpenAI SDK** (optional) - For cloud models

### **Utilities:**
- **httpx** 0.27.x - HTTP client for n8n
- **python-dateutil** 2.9.0 - Date parsing
- **pydantic** 2.9.x - Data validation

---

## 🧪 Testing Strategy

### **Unit Tests:**
- Each tool function
- State updates
- Routing logic
- Handoff detection

### **Integration Tests:**
- Agent → Tool → Database
- Agent → Agent handoffs
- State preservation
- Error handling

### **End-to-End Tests:**
```
Test 1: Food Logging
  User: "Log that I ate pizza"
  Expect: Food Agent asks questions, logs successfully

Test 2: Food → Task Handoff
  User: "Suggest food"
  Food Agent: Suggests
  User: "Create grocery task"
  Expect: Handoff to Task Agent with context

Test 3: Multi-Turn Conversation
  User: "Show my day"
  Event Agent: Shows events
  Task Agent: Shows tasks
  User: "Move task to tomorrow"
  Expect: Task Agent updates with context

Test 4: Semantic Search
  User: "Find something like Thai curry"
  Expect: Vector search + DB filtering works
```

---

## 📊 Success Metrics

### **Performance:**
- Response time < 2 seconds (95th percentile)
- Tool execution < 500ms
- Handoff latency < 300ms

### **Quality:**
- Agent picks correct domain 95%+ of time
- Handoffs preserve context 100%
- Tool calls are appropriate 90%+ of time

### **User Experience:**
- Users understand which agent is active
- Handoffs feel natural
- Suggestions are relevant
- Conversations flow smoothly

---

## 🚧 Challenges & Solutions

### **Challenge 1: State Management Complexity**
**Problem:** State grows large with long conversations
**Solution:**
- Implement state pruning (keep last N messages)
- Summarize old context
- Store full history in DB, lightweight state in memory

### **Challenge 2: Agent Doesn't Know When to Hand Off**
**Problem:** Food Agent tries to handle task questions
**Solution:**
- Clear system prompts about domain boundaries
- Add explicit handoff keywords
- Use LLM to detect domain shift
- Log handoff decisions for refinement

### **Challenge 3: Vector Search + DB Queries Are Slow**
**Problem:** Hybrid recommendations take too long
**Solution:**
- Cache frequent queries
- Parallel execution (DB + vector simultaneously)
- Limit vector search results
- Pre-compute common patterns

### **Challenge 4: Conversation Context Gets Lost**
**Problem:** Task Agent doesn't know about food discussion
**Solution:**
- Rich state with domain contexts
- Message history passed to all agents
- Explicit context fields (food_context, task_context)

### **Challenge 5: Too Many LLM Calls**
**Problem:** Every routing, handoff, tool call = LLM call
**Solution:**
- Cache routing decisions
- Use smaller/faster model for routing
- Batch tool calls when possible
- Use function calling instead of chain-of-thought for tools

---

## 🔄 Migration from Current System

### **Phase A: Parallel Deployment**
1. Keep existing Pydantic AI agent running
2. Deploy LangGraph agents alongside
3. Create new AnythingLLM skills for LangGraph
4. Test with subset of requests

### **Phase B: Gradual Cutover**
1. Route food questions to LangGraph Food Agent
2. Keep other domains on Pydantic AI
3. Monitor performance and quality
4. Add Task Agent to LangGraph
5. Add Event Agent to LangGraph

### **Phase C: Full Migration**
1. All traffic to LangGraph agents
2. Deprecate Pydantic AI agent
3. Archive old code

### **Rollback Plan:**
- Keep Pydantic AI agent container
- Switch AnythingLLM skills back
- LangGraph can coexist indefinitely

---

## 📈 Future Enhancements

### **After Initial Implementation:**

1. **Memory Agent**
   - Full OpenMemory integration
   - Obsidian vault semantic search
   - Knowledge graph connections

2. **Proactive Agents**
   - Daily summary agent (runs scheduled)
   - Pattern detection agent
   - Reminder optimization agent

3. **Multi-Agent Collaboration**
   - Food Agent asks Task Agent about schedule before suggesting
   - Task Agent checks Event Agent for conflicts
   - Agents coordinate complex workflows

4. **Learning & Optimization**
   - Track which handoffs work well
   - Learn user preferences
   - Optimize tool selection
   - Personalize system prompts

5. **Advanced Features**
   - Voice input/output
   - Image analysis (food photos)
   - Recipe suggestions with images
   - Automated grocery ordering

---

## 🎯 Decision Points

### **Before Implementation, Decide:**

**1. Routing Strategy:**
- [ ] First-agent routing (LangGraph decides)
- [ ] AnythingLLM routing (separate skills)
- [ ] Hybrid (simple → direct, complex → router)

**2. State Persistence:**
- [ ] In-memory only (simple, lost on restart)
- [ ] Redis (persistent, scalable)
- [ ] PostgreSQL (full history, slower)

**3. LLM Models:**
- [ ] Single model for all agents (consistent, simpler)
- [ ] Different models per agent (optimized, complex)
- [ ] Local only (Ollama)
- [ ] Cloud option (OpenAI for complex reasoning)

**4. Vector Search:**
- [ ] Start with Qdrant only
- [ ] Add OpenMemory later
- [ ] Hybrid from the start

**5. Deployment:**
- [ ] Single container (all agents)
- [ ] Multiple containers (one per agent)
- [ ] Serverless functions

---

## 📝 Next Steps

1. **Review this plan** - Validate approach
2. **Make decisions** - Answer decision points above
3. **Set up environment** - Install LangGraph
4. **Prototype** - Build Food Agent as proof of concept
5. **Iterate** - Refine based on results
6. **Scale** - Add more agents

---

## 📚 Resources

**LangGraph:**
- Docs: https://langchain-ai.github.io/langgraph/
- Multi-agent tutorial: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/
- State management: https://langchain-ai.github.io/langgraph/concepts/low_level/

**Reference Implementations:**
- LangGraph multi-agent examples
- OpenAI Swarm (similar concept)
- AutoGen framework

**Your Existing Code:**
- Pydantic AI agent: `containers/pydantic-agent/main.py`
- n8n workflows: For tool implementation reference
- Database schema: `migrations/`

---

**Estimated Timeline:** 4-5 weeks for full implementation
**Estimated LOC:** ~2,000 lines (agents + tools + infrastructure)
**Complexity:** Medium-High (LangGraph learning curve)

**Ready to proceed?** Start with Phase 1: Foundation
