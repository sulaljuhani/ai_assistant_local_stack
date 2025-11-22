# Proposed Event Tools - Inspired by Task Tool Expansion

## Current State Analysis

### Existing Event Tools (6 tools)
1. `search_events` - Basic search by date range
2. `create_event` - Create single event
3. `get_events_today` - Today's events
4. `get_events_week` - Week's events
5. `check_time_conflicts` - Check one time slot
6. `unified_search` - Search across all types (already includes events)

### Unused Schema Features

The events table has powerful fields that aren't exposed through tools:

| Schema Field | Currently Used? | Potential Use |
|--------------|----------------|---------------|
| `attendees JSONB` | ❌ No | Search by attendee, bulk add attendees |
| `tags TEXT[]` | ❌ No | Tag events, search by tags |
| `status` (confirmed/tentative/cancelled) | ❌ No | Bulk status updates |
| `is_recurring` + `recurrence_rule` | ❌ No | Recurring event management |
| `recurrence_parent_id` | ❌ No | Series management |
| `location TEXT` | ✅ Partial | Search by location |
| `conference_link` | ❌ No | Add/manage meeting links |
| `metadata JSONB` | ❌ No | Custom event data |
| Full-text search index | ❌ No | Already indexed but not used |

---

## Proposed New Tools (18 tools)

### Category 1: Bulk Operations (5 tools)

Similar to task bulk operations, but for calendar management.

#### 1.1 `bulk_create_events`
Create multiple events at once.

**Use Cases**:
- "Schedule 5 meetings: Monday 9am, Tuesday 2pm, ..."
- "Add weekly team standups for the next month"
- "Block my calendar for the conference: travel, sessions, meals"

**Schema Fields**: All event fields

**Example**:
```python
events = [
    {"title": "Team Meeting", "start_time": "2025-01-15 09:00", "end_time": "2025-01-15 10:00"},
    {"title": "Client Call", "start_time": "2025-01-15 14:00", "end_time": "2025-01-15 15:00"},
]
await bulk_create_events(events, user_id)
```

#### 1.2 `bulk_update_event_status`
Update status for multiple events (confirm/tentative/cancel).

**Use Cases**:
- "Cancel all meetings tomorrow" (sick day)
- "Mark all client meetings as confirmed"
- "Make all next week's events tentative"

**Schema Fields**: `status`

#### 1.3 `bulk_reschedule_events`
Shift multiple events by a time delta.

**Use Cases**:
- "Move all tomorrow's meetings to next week"
- "Shift afternoon meetings back 1 hour"
- "Push all January meetings to February"

**Schema Fields**: `start_time`, `end_time`

#### 1.4 `bulk_delete_events`
Delete multiple events at once.

**Use Cases**:
- "Delete all cancelled meetings"
- "Remove all old events from 2024"
- "Clear all placeholder events"

**Schema Fields**: All

#### 1.5 `bulk_add_attendees`
Add attendees to multiple events.

**Use Cases**:
- "Add Sarah to all client meetings this week"
- "Add the team to all planning sessions"
- "Add external consultant to project meetings"

**Schema Fields**: `attendees JSONB`

---

### Category 2: Advanced Search (4 tools)

Leverage unused search capabilities.

#### 2.1 `search_by_attendees`
Find events by participant.

**Use Cases**:
- "Show all meetings with John"
- "Find events where both Sarah and Mike are invited"
- "What meetings am I having with the client?"

**Schema Fields**: `attendees JSONB`

**Example**:
```python
# Find all events with John
await search_by_attendees(["john@company.com"], user_id)

# Find events with both Sarah AND Mike
await search_by_attendees(["sarah@company.com", "mike@company.com"], match_all=True, user_id)
```

#### 2.2 `search_by_location`
Find events by location or conference link.

**Use Cases**:
- "Show all meetings in Conference Room A"
- "Find all Zoom meetings"
- "What events are at the downtown office?"

**Schema Fields**: `location`, `conference_link`

#### 2.3 `advanced_event_filter`
Multi-criteria filtering like tasks.

**Use Cases**:
- "Show confirmed meetings with clients next week"
- "Find all-day events with no location"
- "Show meetings tagged 'important' with more than 5 attendees"

**Schema Fields**: `status`, `tags`, `attendees`, `location`, `is_all_day`, `start_time`, `end_time`

**Example**:
```python
await advanced_event_filter(
    user_id=user_id,
    status=["confirmed"],
    tags=["client", "important"],
    has_attendees=True,
    start_date="2025-01-15",
    end_date="2025-01-22"
)
```

#### 2.4 `get_event_statistics`
Analytics on calendar usage.

**Use Cases**:
- "How much time do I spend in meetings?"
- "Show my calendar statistics for last month"
- "What's my busiest day of the week?"

**Metrics**:
- Total meeting time per week/month
- Average meeting length
- Meetings by day of week
- Time by location (office vs remote)
- Events by status
- Attendee frequency

**Example**:
```python
{
    "total_events": 45,
    "total_meeting_hours": 28.5,
    "avg_meeting_length": 38,  # minutes
    "busiest_day": "Tuesday",
    "status_breakdown": {"confirmed": 40, "tentative": 5},
    "location_breakdown": {"Zoom": 30, "Conference Room A": 10, "Other": 5}
}
```

---

### Category 3: Recurring Events (5 tools)

The schema already supports recurring events but no tools expose this!

#### 3.1 `create_recurring_event`
Create a recurring event series.

**Use Cases**:
- "Schedule weekly team meeting every Monday at 9am"
- "Add monthly 1-on-1s on the first Friday"
- "Create daily standup for the next 2 weeks"

**Schema Fields**: `is_recurring`, `recurrence_rule`, `recurrence_end_date`, `recurrence_parent_id`

**Example**:
```python
await create_recurring_event(
    title="Team Standup",
    start_time="2025-01-15 09:00",
    end_time="2025-01-15 09:30",
    recurrence_rule="FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",  # Weekdays only
    recurrence_end_date="2025-03-31",
    user_id=user_id
)
```

#### 3.2 `update_recurring_series`
Update all events in a recurring series.

**Use Cases**:
- "Move weekly meeting to Tuesdays"
- "Change standup time to 10am for all future occurrences"
- "Add location to all recurring team meetings"

**Schema Fields**: `recurrence_parent_id`, all event fields

#### 3.3 `skip_recurring_instance`
Skip one occurrence of a recurring event.

**Use Cases**:
- "Cancel standup on Friday (holiday)"
- "Skip next week's meeting (vacation)"
- "No team meeting this Monday"

**Schema Fields**: `status`, `recurrence_parent_id`

#### 3.4 `delete_recurring_series`
Delete all events in a series.

**Use Cases**:
- "Delete weekly sync meetings (project ended)"
- "Remove all standup meetings"
- "Cancel recurring 1-on-1s"

**Schema Fields**: `recurrence_parent_id`

#### 3.5 `get_recurring_series`
Get all instances of a recurring event.

**Use Cases**:
- "Show all occurrences of weekly meeting"
- "List all standup meetings for January"
- "What recurring meetings do I have?"

**Schema Fields**: `recurrence_parent_id`, `is_recurring`

---

### Category 4: Scheduling Helpers (4 tools)

Smart scheduling assistance.

#### 4.1 `find_available_slots`
Find free time slots in calendar.

**Use Cases**:
- "When am I free tomorrow?"
- "Find 1-hour slots this week"
- "Show available times for a 30-minute meeting"

**Logic**: Query events, find gaps between them

**Example**:
```python
await find_available_slots(
    start_date="2025-01-15",
    end_date="2025-01-19",
    duration_minutes=60,
    business_hours_only=True,  # 9am-5pm
    user_id=user_id
)

# Returns:
[
    {"start": "2025-01-15 10:00", "end": "2025-01-15 11:00"},
    {"start": "2025-01-15 14:00", "end": "2025-01-15 15:00"},
    ...
]
```

#### 4.2 `suggest_meeting_times`
AI-powered meeting time suggestions.

**Use Cases**:
- "Suggest times for a 2-hour meeting next week"
- "When should I schedule this client call?"
- "Find best time for team meeting"

**Logic**:
- Find available slots
- Prefer morning/afternoon based on user patterns
- Avoid back-to-back meetings
- Consider meeting type

#### 4.3 `bulk_check_conflicts`
Check multiple time slots for conflicts.

**Use Cases**:
- "Check if any of these 5 times work: ..."
- "Find which proposed times are free"
- "Validate meeting poll options"

**Schema Fields**: Uses existing events for conflict detection

**Example**:
```python
proposed_times = [
    {"start": "2025-01-15 09:00", "end": "2025-01-15 10:00"},
    {"start": "2025-01-15 14:00", "end": "2025-01-15 15:00"},
    {"start": "2025-01-16 10:00", "end": "2025-01-16 11:00"},
]

result = await bulk_check_conflicts(proposed_times, user_id)

# Returns:
[
    {"slot": 0, "available": False, "conflicts": [...]},
    {"slot": 1, "available": True, "conflicts": []},
    {"slot": 2, "available": True, "conflicts": []},
]
```

#### 4.4 `get_busy_free_times`
Get busy/free blocks for a date range (like Google Calendar's free/busy).

**Use Cases**:
- "Show my availability for next week"
- "When am I busy vs free today?"
- "Create a free/busy report"

**Returns**: Array of busy/free blocks

---

## Priority Ranking

### High Priority (Most Valuable) - 8 tools

1. **bulk_create_events** - High user value, common use case
2. **create_recurring_event** - Schema supports it, major missing feature
3. **bulk_reschedule_events** - Unique calendar feature, very useful
4. **search_by_attendees** - Natural query pattern for calendars
5. **find_available_slots** - Core scheduling functionality
6. **bulk_update_event_status** - Useful for cancellations
7. **get_event_statistics** - Analytics always valuable
8. **advanced_event_filter** - Consistency with task tools

### Medium Priority - 6 tools

9. **update_recurring_series** - Complements recurring creation
10. **skip_recurring_instance** - Common recurring event pattern
11. **bulk_add_attendees** - Useful for team organization
12. **suggest_meeting_times** - AI-powered, nice-to-have
13. **search_by_location** - Useful but less common
14. **bulk_check_conflicts** - Scheduling helper

### Lower Priority - 4 tools

15. **get_recurring_series** - Mostly informational
16. **delete_recurring_series** - Less common operation
17. **bulk_delete_events** - Dangerous, less common
18. **get_busy_free_times** - Nice visualization, less critical

---

## Implementation Plan

### Phase 1: Core Bulk Operations (4 tools)
**Estimated effort**: 3-4 hours

1. Create `tools/event_bulk_operations.py`
   - bulk_create_events
   - bulk_update_event_status
   - bulk_reschedule_events
   - bulk_add_attendees

### Phase 2: Recurring Events (3 tools)
**Estimated effort**: 4-5 hours (more complex logic)

1. Create `tools/event_recurring.py`
   - create_recurring_event
   - update_recurring_series
   - skip_recurring_instance

### Phase 3: Advanced Search (4 tools)
**Estimated effort**: 2-3 hours

1. Create `tools/event_advanced_search.py`
   - search_by_attendees
   - advanced_event_filter
   - search_by_location
   - get_event_statistics

### Phase 4: Scheduling Helpers (3 tools)
**Estimated effort**: 3-4 hours

1. Create `tools/event_scheduling.py`
   - find_available_slots
   - suggest_meeting_times
   - bulk_check_conflicts

---

## Schema Compatibility

### No Migration Needed! ✅

All proposed tools use **existing schema fields**:

| Field | Used By |
|-------|---------|
| `attendees JSONB` | search_by_attendees, bulk_add_attendees |
| `tags TEXT[]` | advanced_event_filter (already exists) |
| `status` | bulk_update_event_status |
| `is_recurring` | All recurring tools |
| `recurrence_rule` | create_recurring_event, update_recurring_series |
| `recurrence_parent_id` | All recurring tools |
| `recurrence_end_date` | create_recurring_event |
| `location` | search_by_location, advanced_event_filter |
| `conference_link` | search_by_location |
| `start_time`, `end_time` | All tools |

**Result**: Can implement all 18 tools without any database changes!

---

## Performance Considerations

### Bulk Operations
- **Expected improvement**: 70-80% faster for multiple operations
- **Example**: Creating 5 events: 5 calls × 7ms = 35ms → 1 call × 10ms = 10ms

### Recurring Events
- **Challenge**: May create many database rows for long series
- **Solution**:
  - Option 1: Create all instances upfront (simple, works with existing schema)
  - Option 2: Create on-demand (complex, requires query changes)
  - **Recommendation**: Start with Option 1

### Advanced Search
- **Already optimized**: Full-text indexes exist
- **JSONB queries**: Attendee searches may be slower, add GIN index if needed:
  ```sql
  CREATE INDEX idx_events_attendees ON events USING GIN(attendees);
  ```

---

## Comparison: Task vs Event Tools

| Category | Task Tools | Event Tools | Notes |
|----------|-----------|-------------|-------|
| **Basic Operations** | 5 tools | 6 tools | Events have more |
| **Bulk Operations** | 6 tools | 5 proposed | Similar patterns |
| **Advanced Search** | 4 tools | 4 proposed | Parallel structure |
| **Dependencies** | 4 tools | - | N/A for events |
| **Checklists** | 4 tools | - | N/A for events |
| **Recurring** | - | 5 proposed | Events-only feature |
| **Scheduling** | - | 4 proposed | Events-only feature |
| **Total** | 26 tools | 24 tools (6 + 18) | Similar scope |

---

## User Experience Examples

### Before
```
User: "Schedule team meetings for the next 4 weeks, every Monday at 9am"
Agent: *Has to create 4 separate events one by one*
Result: Slow, tedious, error-prone
```

### After
```
User: "Schedule team meetings for the next 4 weeks, every Monday at 9am"
Agent: *Uses create_recurring_event with FREQ=WEEKLY rule*
Result: Fast, clean, professional
```

### Before
```
User: "I'm sick tomorrow, cancel all my meetings"
Agent: *Would need to search events, then cancel each individually*
Result: Many tool calls, slow
```

### After
```
User: "I'm sick tomorrow, cancel all my meetings"
Agent: *Uses bulk_update_event_status with tomorrow's events*
Result: Single operation, fast
```

### Before
```
User: "When am I free tomorrow afternoon?"
Agent: *Would need to search events, manually calculate gaps*
Result: Complex, error-prone
```

### After
```
User: "When am I free tomorrow afternoon?"
Agent: *Uses find_available_slots with business hours filter*
Result: Accurate, instant
```

---

## Recommendation

**Start with Phase 1 + Phase 2** (7 high-value tools):

1. Bulk operations (4 tools) - Quick wins, immediate value
2. Recurring events (3 tools) - Biggest missing feature

**Estimated total effort**: 7-9 hours
**User value**: High - covers most common calendar management patterns
**Risk**: Low - all use existing schema

This would bring event tools to **13 total** (6 existing + 7 new), making them much more capable while maintaining parity with task tools.

---

## Next Steps

If approved:
1. Create the 4 new tool files
2. Update `tools/__init__.py` with imports
3. Update `agents/event_agent.py` with new tools
4. Update `prompts/event_agent.txt` with documentation
5. Test imports
6. Rebuild container
7. Test via API

Let me know which phases you'd like to implement!
