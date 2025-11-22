"""Tool functions for agents to interact with databases and services."""

from .database import (
    search_food_log,
    log_food_entry,
    update_food_entry,
    get_food_by_rating,
    analyze_food_patterns,
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    get_tasks_due_soon,
    search_events,
    create_event,
    get_events_today,
    get_events_week,
    check_time_conflicts,
)

from .vector import (
    vector_search_foods,
    vector_search_memories,
)

from .hybrid import (
    get_food_recommendations,
)

from .documents import (
    embed_document,
    reembed_vault_file,
    search_embedded_documents,
)

from .memory import (
    store_chat_turn,
    search_memories,
)

# NEW: Task dependencies (from Atlas inspiration)
from .task_dependencies import (
    add_task_dependency,
    get_task_dependencies,
    get_available_tasks,
    complete_task_with_unblock,
)

# NEW: Task checklists/subtasks
from .task_checklists import (
    add_checklist_item,
    check_checklist_item,
    get_task_with_checklist,
    get_tasks_with_incomplete_checklists,
)

# NEW: Bulk operations
from .bulk_operations import (
    bulk_create_tasks,
    bulk_update_task_status,
    bulk_add_tags,
    bulk_set_priority,
    bulk_delete_tasks,
    bulk_move_to_project,
)

# NEW: Advanced search
from .advanced_search import (
    unified_search,
    search_by_tags,
    advanced_task_filter,
    get_task_statistics,
)

# Event bulk operations
from .event_bulk_operations import (
    bulk_create_events,
    bulk_update_event_status,
    bulk_reschedule_events,
    bulk_add_attendees,
    bulk_delete_events,
)

# Event recurring
from .event_recurring import (
    create_recurring_event,
    update_recurring_series,
    skip_recurring_instance,
    delete_recurring_series,
    get_recurring_series,
)

# Event advanced search
from .event_advanced_search import (
    search_by_attendees,
    search_by_location,
    advanced_event_filter,
    get_event_statistics,
)

# Event scheduling
from .event_scheduling import (
    find_available_slots,
    suggest_meeting_times,
    bulk_check_conflicts,
    get_busy_free_times,
)

# Reminder tools
from .reminders import (
    search_reminders,
    create_reminder,
    update_reminder,
    complete_reminder,
    get_reminders_today,
    get_reminders_due_soon,
)

__all__ = [
    # Database - Food
    "search_food_log",
    "log_food_entry",
    "update_food_entry",
    "get_food_by_rating",
    "analyze_food_patterns",
    # Database - Tasks
    "search_tasks",
    "create_task",
    "update_task",
    "get_tasks_by_priority",
    "get_tasks_due_soon",
    # Database - Events
    "search_events",
    "create_event",
    "get_events_today",
    "get_events_week",
    "check_time_conflicts",
    # Vector
    "vector_search_foods",
    "vector_search_memories",
    # Hybrid
    "get_food_recommendations",
    # Documents
    "embed_document",
    "reembed_vault_file",
    "search_embedded_documents",
    # Memory
    "store_chat_turn",
    "search_memories",
    # NEW: Task Dependencies
    "add_task_dependency",
    "get_task_dependencies",
    "get_available_tasks",
    "complete_task_with_unblock",
    # NEW: Task Checklists
    "add_checklist_item",
    "check_checklist_item",
    "get_task_with_checklist",
    "get_tasks_with_incomplete_checklists",
    # NEW: Bulk Operations
    "bulk_create_tasks",
    "bulk_update_task_status",
    "bulk_add_tags",
    "bulk_set_priority",
    "bulk_delete_tasks",
    "bulk_move_to_project",
    # NEW: Advanced Search
    "unified_search",
    "search_by_tags",
    "advanced_task_filter",
    "get_task_statistics",
    # Event bulk operations
    "bulk_create_events",
    "bulk_update_event_status",
    "bulk_reschedule_events",
    "bulk_add_attendees",
    "bulk_delete_events",
    # Event recurring
    "create_recurring_event",
    "update_recurring_series",
    "skip_recurring_instance",
    "delete_recurring_series",
    "get_recurring_series",
    # Event advanced search
    "search_by_attendees",
    "search_by_location",
    "advanced_event_filter",
    "get_event_statistics",
    # Event scheduling
    "find_available_slots",
    "suggest_meeting_times",
    "bulk_check_conflicts",
    "get_busy_free_times",
    # Reminders
    "search_reminders",
    "create_reminder",
    "update_reminder",
    "complete_reminder",
    "get_reminders_today",
    "get_reminders_due_soon",
]
