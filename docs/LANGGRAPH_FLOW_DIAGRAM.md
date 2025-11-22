# LangGraph Multi-Agent Flow Diagram

## Complete Agent Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER MESSAGE INPUT                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              START (Entry Point)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROUTING NODE (Hybrid Router)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. State Pruning Check                                                      │
│     └─ Keep last 20 messages (prevents memory bloat)                        │
│                                                                              │
│  2. Keyword-Based Routing (Fast Path - O(1))                                │
│     ├─ Food keywords: "food", "meal", "eat", "restaurant"...                │
│     ├─ Task keywords: "task", "todo", "complete", "deadline"...             │
│     ├─ Event keywords: "event", "calendar", "meeting", "schedule"...        │
│     └─ Reminder keywords: "remind", "alert", "notify", "ping"...            │
│     └─ Requires 2+ keyword matches & clear winner (2x score)                │
│                                                                              │
│  3. LLM-Based Routing (Fallback for Complex/Ambiguous)                      │
│     ├─ Analyzes message intent, context, conversation history               │
│     ├─ Returns: {agent, confidence, reason}                                 │
│     └─ Handles edge cases & nuanced requests                                │
│                                                                              │
│  4. Update State                                                             │
│     └─ Set current_agent, clear handoff flags                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │ FOOD AGENT   │  │ TASK AGENT   │  │ EVENT AGENT  │  │REMINDER AGENT│
         └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                │                 │                 │                 │
                └─────────────────┴─────────────────┴─────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT NODE EXECUTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Agent receives state with messages and context                           │
│  2. Agent invokes LLM with specialized system prompt                         │
│  3. LLM decides to use tools or respond directly                             │
│  4. Tools execute (database queries, vector search, etc.)                    │
│  5. Agent formulates response based on tool outputs                          │
│  6. State updated with agent response                                        │
│  7. Agent can request handoff to another agent if needed                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SHOULD_CONTINUE (Decision Point)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Check if conversation should continue or end:                               │
│                                                                              │
│  ✓ Handoff Requested? (state.target_agent set)                              │
│     └─ YES → Return "route" (go back to ROUTING NODE)                       │
│                                                                              │
│  ✓ Need Re-routing? (domain shift detected, explicit agent switch)          │
│     └─ YES → Return "route" (go back to ROUTING NODE)                       │
│                                                                              │
│  ✓ Otherwise                                                                 │
│     └─ NO → Return "end" (conversation complete)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                                      │
                    │ "route"                              │ "end"
                    │                                      │
                    ▼                                      ▼
         ┌──────────────────┐                  ┌──────────────────┐
         │   ROUTING NODE   │                  │       END        │
         │   (loop back)    │                  │ (terminal state) │
         └──────────────────┘                  └──────────────────┘
                    │                                      │
                    │                                      ▼
                    └───────────────────────► ┌──────────────────────┐
                         (continues            │  RESPONSE TO USER    │
                          multi-turn           └──────────────────────┘
                          conversation)
```

## Agent Specializations & Tools

### 🍽️ Food Agent
**Domain:** Food logging, meal suggestions, dietary patterns

**Tools (7):**
- `search_food_log` - Search food entries
- `log_food_entry` - Log new meals
- `update_food_entry` - Update existing entries
- `get_food_by_rating` - Filter by preference
- `analyze_food_patterns` - Dietary analysis
- `vector_search_foods` - Semantic search
- `get_food_recommendations` - AI-powered suggestions

**Example Flow:**
```
User: "Suggest something to eat"
  ↓
Keyword Routing → Food Agent
  ↓
Agent: Use get_food_recommendations tool
  ↓
Agent: "How about Thai curry? You rated it 5/5 last time, and you haven't had it in 2 weeks"
```

### ✅ Task Agent
**Domain:** Task management, planning, productivity, memory/notes

**Tools (23):**
- **CRUD:** `create_task`, `update_task`, `search_tasks`
- **Priority:** `get_tasks_by_priority`, `get_tasks_due_soon`
- **Dependencies:** `add_task_dependency`, `get_task_dependencies`, `get_available_tasks`
- **Checklists:** `add_checklist_item`, `check_checklist_item`, `get_task_with_checklist`
- **Bulk Ops:** `bulk_create_tasks`, `bulk_update_task_status`, `bulk_add_tags`, `bulk_set_priority`, `bulk_delete_tasks`, `bulk_move_to_project`
- **Search:** `unified_search`, `search_by_tags`, `advanced_task_filter`
- **Analytics:** `get_task_statistics`
- **Memory:** Memory tools if enabled

**Example Flow:**
```
User: "Add a task to call dentist, it's urgent"
  ↓
Keyword Routing → Task Agent
  ↓
Agent: Use create_task tool
  ↓
Agent: "I've created a high-priority task 'Call dentist' with due date end of this week.
       Would you like me to add a reminder for tomorrow morning?"
```

### 📅 Event Agent
**Domain:** Calendar management, scheduling, time blocking

**Tools (20):**
- **CRUD:** `create_event`, `search_events`, `get_events_today`, `get_events_week`
- **Scheduling:** `find_available_slots`, `suggest_meeting_times`, `check_time_conflicts`, `get_busy_free_times`
- **Recurring:** `create_recurring_event`, `update_recurring_series`, `skip_recurring_instance`, `delete_recurring_series`, `get_recurring_series`
- **Bulk Ops:** `bulk_create_events`, `bulk_update_event_status`, `bulk_reschedule_events`, `bulk_add_attendees`, `bulk_delete_events`, `bulk_check_conflicts`
- **Search:** `search_by_attendees`, `search_by_location`, `advanced_event_filter`
- **Analytics:** `get_event_statistics`

**Example Flow:**
```
User: "Schedule a meeting with John tomorrow at 2pm"
  ↓
Keyword Routing → Event Agent
  ↓
Agent: Use check_time_conflicts & create_event tools
  ↓
Agent: "I've scheduled your meeting with John for tomorrow 2-3pm. No conflicts found."
```

### ⏰ Reminder Agent
**Domain:** Reminders, alerts, follow-ups, time-based notifications

**Tools:**
- Reminder CRUD operations
- Snooze functionality
- Multi-channel notifications

**Example Flow:**
```
User: "Remind me to check email in 30 minutes"
  ↓
Keyword Routing → Reminder Agent
  ↓
Agent: Use create_reminder tool
  ↓
Agent: "I'll remind you to check email at 3:30 PM via system notification"
```

## State Management & Persistence

### MultiAgentState Structure
```python
{
    "messages": [...],              # Conversation history (pruned to last 20)
    "current_agent": "food_agent",  # Active agent
    "previous_agent": "task_agent", # Last agent (for context)
    "target_agent": None,           # Handoff target (if requested)
    "handoff_reason": None,         # Why handoff was requested
    "turn_count": 5,                # Number of conversation turns
    "user_id": "00000...",         # Single-user ID
    "session_id": "abc123...",      # Conversation session
}
```

### Redis Checkpointing
- State persisted to Redis after each turn
- 24-hour TTL (auto-cleanup)
- Thread-based isolation
- Enables conversation resumption

## Routing Strategy Details

### 1. Keyword-Based Routing (Fast Path)
**When used:** Clear, unambiguous queries
**Speed:** ~1ms
**Accuracy:** ~85% for simple queries

```python
# Keyword matching with scoring
food_score = count_matches(message, FOOD_KEYWORDS)
task_score = count_matches(message, TASK_KEYWORDS)
# ... etc

# Requires 2+ matches AND 2x winner
if max_score >= 2 and max_score >= 2 * second_highest:
    route_to(winner)
```

### 2. LLM-Based Routing (Fallback)
**When used:** Complex/ambiguous queries
**Speed:** ~500ms (using llama3.2:3b)
**Accuracy:** ~95% with context

```python
# Structured output from LLM
{
    "agent": "food_agent",
    "confidence": 0.92,
    "reason": "User is asking for meal suggestions based on preferences"
}
```

## Handoff Mechanism

Agents can request handoffs to other agents:

```python
# Agent detects cross-domain request
Agent: "I see you want to schedule this. Let me hand you off to the Event Agent."

# State update
state["target_agent"] = "event_agent"
state["handoff_reason"] = "User needs calendar scheduling"

# Flow returns to ROUTING NODE
# Routing node sees target_agent set, routes to event_agent
```

## State Pruning (Memory Management)

**Problem:** Unlimited conversation history causes:
- Token limit exceeded
- Slow inference
- High memory usage

**Solution:** Keep last 20 messages
```python
if len(state["messages"]) > 20:
    # Keep system message + last 19 messages
    state["messages"] = [
        state["messages"][0],  # System prompt
        *state["messages"][-19:]  # Recent history
    ]
```

## Performance Characteristics

| Operation | Average Time | Notes |
|-----------|-------------|-------|
| Keyword routing | ~1ms | O(n) where n = keyword count |
| LLM routing | ~500ms | Using llama3.2:3b locally |
| Agent tool call | ~50-200ms | Database queries via asyncpg |
| Vector search | ~100ms | Qdrant semantic search |
| Full turn (simple) | ~600ms | Keyword route + tool + response |
| Full turn (complex) | ~1200ms | LLM route + multiple tools + response |

## Error Handling & Fallbacks

```
LLM Routing Fails
  ↓
Default to food_agent (most general)
  ↓
Log error for debugging

Tool Execution Fails
  ↓
Agent receives error message
  ↓
Agent responds with graceful error message
  ↓
Conversation continues

Checkpointing Fails
  ↓
Session continues without persistence
  ↓
Log warning
```

## Comparison to LangGraph Tutorial

| Aspect | LangGraph Tutorial | AI Stack Implementation |
|--------|-------------------|------------------------|
| Routing | Separate classifier + router nodes | Combined routing node (more efficient) |
| Agent Count | 2-3 agents | 4 specialized agents |
| Routing Strategy | LLM-only | Hybrid (keywords + LLM fallback) |
| Handoffs | Limited support | Full handoff with context |
| State Pruning | Not implemented | Automatic (last 20 messages) |
| Persistence | Memory-based | Redis with 24h TTL |
| Looping | Linear flow | Multi-turn with conditional looping |

## Example Multi-Turn Conversation with Handoff

```
User: "Suggest something to eat"
  ↓ [Keyword Routing]
Food Agent: "How about salmon? You rated it highly last time."

User: "Great! Remind me to buy salmon tomorrow"
  ↓ [should_continue detects domain shift]
  ↓ [Routes to Reminder Agent]
Reminder Agent: "I'll remind you tomorrow at 9 AM to buy salmon."

User: "Actually, make that a task instead"
  ↓ [should_continue detects domain shift]
  ↓ [Routes to Task Agent]
Task Agent: "I've created a task 'Buy salmon' due tomorrow.
            Should I keep the reminder too?"
```

---

**Key Insights:**
1. **Hybrid routing** balances speed (keywords) and accuracy (LLM)
2. **State pruning** prevents memory bloat
3. **Conditional looping** enables natural multi-turn conversations
4. **Specialized agents** provide deep domain expertise
5. **Redis persistence** enables session resumption
6. **Handoff mechanism** allows seamless agent transitions
