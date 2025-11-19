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
]
