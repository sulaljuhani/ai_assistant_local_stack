# LangGraph Multi-Agent System Architecture

## Overview

This document describes the technical architecture of the LangGraph multi-agent system, including design decisions, data flow, and component interactions.

## System Components

### 1. API Layer (FastAPI)

**File**: `main.py`

The FastAPI application provides REST endpoints for:
- Chat interactions (`POST /chat`)
- Session management (`GET/DELETE /session/{id}`)
- Health checks (`GET /health`)
- Configuration inspection (`GET /config`)

**Key Features**:
- Async/await for non-blocking I/O
- CORS middleware for cross-origin requests
- Structured error handling
- Lifespan management for startup/shutdown

### 2. LangGraph Workflow

**Files**: `graph/workflow.py`, `graph/state.py`

The workflow orchestrates agent interactions using a state machine:

```
START → Routing Node → Agent Node → Decision → (Routing or END)
```

**State Schema** (`MultiAgentState`):
- `messages`: Conversation history (with `add_messages` reducer for automatic appending)
- `current_agent`: Active agent
- `user_id`, `workspace`, `session_id`: User context
- `agent_contexts`: Consolidated domain contexts ({"food": {...}, "task": {...}, "event": {...}})
- `target_agent`, `handoff_reason`: Handoff metadata
- `turn_count`, timestamps: Tracking info

**Recent Improvements** (following LangGraph tutorial best practices):
- Module-level agent caching (agents created once, reused forever)
- Context injection via messages (not template variables)
- Simplified state structure with consolidated contexts
- Uses `add_messages` reducer for automatic message handling

**State Pruning**:
- Keeps first message (context)
- Keeps last N messages (default: 20)
- Prevents memory bloat in long conversations

### 3. Routing System

**File**: `graph/routing.py`

**Hybrid Strategy**:

1. **Keyword Matching** (Fast Path)
   - Predefined keywords for each domain
   - Scoring based on keyword frequency
   - Requires 2+ matches and clear winner
   - Returns immediately if confident

2. **LLM Routing** (Fallback)
   - Used for complex/ambiguous queries
   - Structured output (RoutingDecision)
   - Considers conversation context
   - More expensive but accurate

**Routing Keywords**:
- Food: food, meal, eat, lunch, dinner, nutrition, etc.
- Task: task, todo, remind, deadline, priority, etc.
- Event: calendar, schedule, meeting, appointment, etc.

### 4. Agents

**Files**: `agents/*.py`

Each agent is a specialized LangGraph node that:
1. Receives state with conversation history
2. Executes with domain-specific tools
3. Generates response
4. Detects need for handoff
5. Updates domain context
6. Returns updated state

**Agent Structure** (refactored for performance):
```python
# Module-level caching (created once, reused forever)
_agent_instance = None

def _get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_cached_react_agent(...)
    return _agent_instance

async def agent_node(state: MultiAgentState) -> Dict[str, Any]:
    # 1. Get cached agent (no recreation!)
    agent = _get_agent()
    # 2. Create context message with system prompt
    context_msg = create_context_message(state, "agent_name", PROMPT)
    # 3. Prepend context to messages
    messages = [context_msg] + state["messages"]
    # 4. Execute agent
    result = await agent.ainvoke({"messages": messages})
    # 5. Detect handoff
    # 6. Update agent context
    # 7. Return state updates
```

**System Prompts**:
- Define agent expertise
- Specify domain boundaries
- Provide handoff guidelines
- Set personality and approach

### 5. Handoff Detection

**File**: `agents/base.py::detect_handoff()`

**Detection Strategy**:

1. **Explicit Handoffs**
   - Check `state["target_agent"]`
   - Immediate handoff if set

2. **Domain Shift Detection**
   - Extract last user message
   - Use LLM to analyze intent
   - Compare against current agent domain
   - Return structured decision

**HandoffDecision**:
```python
class HandoffDecision:
    should_handoff: bool
    target_agent: Optional[str]
    reason: Optional[str]
```

### 6. Tool Layer

**Files**: `tools/*.py`

**Categories**:

1. **Database Tools** (`database.py`)
   - Direct SQL queries
   - Structured filters
   - Fast for exact matches
   - Used for: filtering, CRUD operations

2. **Vector Tools** (`vector.py`)
   - Qdrant semantic search
   - Similarity-based retrieval
   - Used for: "find similar", recommendations

3. **Hybrid Tools** (`hybrid.py`)
   - Combines DB + vector
   - Deduplicates and ranks
   - Used for: intelligent suggestions

4. **n8n Tools** (`n8n.py`)
   - Webhook triggers
   - Workflow integration
   - Used for: embeddings, notifications

**Tool Registration**:
- Each agent sees only relevant tools
- Tools are LangChain-compatible
- Async execution supported

### 7. State Persistence

**File**: `graph/checkpointer.py`

**Redis Checkpointer**:
- Implements LangGraph `BaseCheckpointSaver`
- Stores serialized state in Redis
- TTL-based cleanup (default: 24 hours)
- Thread-based isolation

**Operations**:
- `aget()`: Load checkpoint by thread_id
- `aput()`: Save checkpoint with TTL
- `adelete()`: Remove thread checkpoints

**Key Format**: `checkpoint:{thread_id}:latest`

### 8. LLM Abstraction

**File**: `utils/llm.py`

**Factory Functions**:
- `get_llm()`: General purpose
- `get_routing_llm()`: Fast, low temp for routing
- `get_agent_llm()`: Standard for agents

**Supported Providers**:

1. **Ollama**
   ```python
   ChatOllama(
       base_url=settings.ollama_base_url,
       model=settings.ollama_model
   )
   ```

2. **OpenAI-Compatible**
   ```python
   ChatOpenAI(
       api_key=settings.openai_api_key,
       base_url=settings.openai_base_url,
       model=settings.openai_model
   )
   ```

**Switching**: Change `LLM_PROVIDER` environment variable

### 9. Configuration

**File**: `config.py`

**Pydantic Settings**:
- Type-safe configuration
- Environment variable loading
- Validation and defaults
- Computed properties (URLs)

**Key Settings**:
- LLM provider and models
- Database connections
- Redis configuration
- Qdrant settings
- State management (pruning, TTL)
- API configuration

## Data Flow

### Chat Request Flow

```
1. POST /chat
   ↓
2. Create/Load State
   - Load from Redis if exists
   - Create initial state if new
   ↓
3. Workflow Invocation
   - Pass state + config
   ↓
4. Routing Node
   - Keyword matching attempt
   - LLM routing if needed
   - Set current_agent
   ↓
5. Agent Execution
   - Load system prompt
   - Create ReAct agent with tools
   - Execute with state
   - Generate response
   ↓
6. Handoff Detection
   - Analyze response + user message
   - Determine if handoff needed
   ↓
7. Decision Point
   - Handoff? → Back to Routing
   - Done? → END
   ↓
8. State Persistence
   - Serialize state
   - Save to Redis with TTL
   ↓
9. Response
   - Extract AI message
   - Return to client
```

### State Updates

Each agent updates:
- `messages`: Appends new messages
- `current_agent`: Sets to self
- `previous_agent`: Tracks last agent
- `{domain}_context`: Updates own context
- `turn_count`: Increments
- `updated_at`: Current timestamp

Handoff triggers add:
- `target_agent`: Next agent name
- `handoff_reason`: Explanation
- Handoff message to conversation

## Design Patterns

### 1. Strategy Pattern (Routing)

Multiple routing strategies with fallback:
```python
def route():
    result = simple_keyword_routing()
    if result:
        return result
    return llm_routing()
```

### 2. Factory Pattern (LLM)

Centralized LLM creation:
```python
llm = get_llm(temperature=0.7)
# Hides provider details
```

### 3. Adapter Pattern (Tools)

LangChain tool decorator adapts functions:
```python
@tool
async def search_food_log(...) -> List[Dict]:
    # Regular Python function
    # Automatically converted to LangChain tool
```

### 4. Observer Pattern (State)

State changes trigger updates:
- Message append → Pruning check
- Handoff detected → Routing triggered
- Turn complete → State persisted

### 5. Template Method (Agents)

Base agent pattern with customization:
```python
# Base provides: handoff detection, context updates
# Subclass provides: tools, system prompt
```

## Performance Characteristics

### Time Complexity

- **Keyword Routing**: O(n×m) where n=keywords, m=message length
  - Fast: ~1ms for typical messages

- **LLM Routing**: O(LLM)
  - Depends on model: 50-500ms

- **Agent Execution**: O(LLM + tools)
  - Varies: 1-5 seconds typical

- **State Load/Save**: O(1)
  - Redis: <10ms typically

### Space Complexity

- **State Size**: O(messages)
  - Pruned: ~20 messages × ~500 bytes = ~10KB
  - Unpruned: Can grow large (managed by pruning)

- **Redis Storage**: O(active_sessions)
  - Per session: ~10-50KB
  - TTL cleanup prevents unbounded growth

### Scalability

**Horizontal Scaling**:
- Stateless API layer (FastAPI)
- Shared Redis for state
- Can run multiple instances

**Bottlenecks**:
1. LLM calls (slowest component)
2. Vector search (if large collections)
3. Database queries (optimized with indexes)

**Mitigation**:
- Keyword routing reduces LLM calls
- Tool call batching (future)
- Query result caching (future)

## Security Considerations

### Input Validation
- Pydantic models validate all inputs
- Type checking at API boundary
- SQL parameterization (no injection)

### Isolation
- User-level data isolation via user_id
- Session isolation via session_id
- No cross-user data leakage

### Secrets Management
- Environment variables for secrets
- No hardcoded credentials
- API keys not logged

### Error Handling
- Exceptions caught and logged
- Generic error messages to users
- Stack traces only in logs

## Monitoring & Debugging

### Logging

Structured logging at multiple levels:
```python
logger.info("Agent activated")
logger.debug("Detailed state info")
logger.error("Error details", exc_info=True)
```

**Log Locations**:
- Stdout (Docker logs)
- Optional: File logging to `/app/logs`

### Health Checks

- `/health` endpoint for liveness
- Docker HEALTHCHECK every 30s
- Checks: API responsive

### Debugging

**State Inspection**:
```bash
GET /session/{session_id}
# Returns full session info
```

**Configuration**:
```bash
GET /config
# Shows current settings
```

## Testing Strategy

### Unit Tests
- Tool functions
- Routing logic
- State pruning
- Configuration

### Integration Tests
- Agent → Tool → Database
- State persistence → Redis
- LLM provider switching

### End-to-End Tests
- Full conversation flows
- Agent handoffs
- Multi-turn conversations

## Future Enhancements

### Planned
1. **Streaming Responses**
   - WebSocket support
   - Token-by-token streaming

2. **Tool Call Batching**
   - Parallel tool execution
   - Reduced latency

3. **Advanced Caching**
   - Query result caching
   - Routing decision caching

4. **Memory Agent**
   - Fourth agent for notes
   - OpenMemory integration

5. **Metrics & Analytics**
   - Agent usage statistics
   - Performance tracking
   - Quality metrics

### Considered
- Multi-agent collaboration (agents consulting each other)
- Proactive agents (scheduled runs)
- Voice interface integration
- Image analysis capabilities

---

This architecture is designed for:
- ✅ Easy extension (new agents, tools)
- ✅ Performance optimization (hybrid routing)
- ✅ Reliability (state persistence, error handling)
- ✅ Maintainability (clear separation of concerns)
- ✅ Flexibility (model switching, configuration)
