"""
Task Agent - Specialized in task management, planning, and productivity.

Refactored following LangGraph tutorial best practices:
- Module-level agent caching (created once, reused forever)
- Context injection via messages (not templates)
- Simple agent function (minimal overhead)
"""

from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
from graph.state import MultiAgentState
from tools import (
    # Basic task operations
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    get_tasks_due_soon,
    # Task dependencies
    add_task_dependency,
    get_task_dependencies,
    get_available_tasks,
    complete_task_with_unblock,
    # Task checklists
    add_checklist_item,
    check_checklist_item,
    get_task_with_checklist,
    get_tasks_with_incomplete_checklists,
    # Bulk operations
    bulk_create_tasks,
    bulk_update_task_status,
    bulk_add_tags,
    bulk_set_priority,
    bulk_delete_tasks,
    bulk_move_to_project,
    # Advanced search
    unified_search,
    search_by_tags,
    advanced_task_filter,
    get_task_statistics,
)
from utils.logging import get_logger
from .base import (
    load_system_prompt,
    create_context_message,
    create_cached_react_agent,
    detect_handoff,
)

logger = get_logger(__name__)


# ============================================================================
# MODULE-LEVEL CONFIGURATION (Created once, reused forever)
# ============================================================================

# Load system prompt once
TASK_AGENT_PROMPT = load_system_prompt("task_agent")

# Define tools once (26 tools total including 21 new ones)
TASK_TOOLS = [
    # Basic task operations (5 tools)
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    get_tasks_due_soon,
    # Task dependencies (4 tools)
    add_task_dependency,
    get_task_dependencies,
    get_available_tasks,
    complete_task_with_unblock,
    # Task checklists (4 tools)
    add_checklist_item,
    check_checklist_item,
    get_task_with_checklist,
    get_tasks_with_incomplete_checklists,
    # Bulk operations (6 tools)
    bulk_create_tasks,
    bulk_update_task_status,
    bulk_add_tags,
    bulk_set_priority,
    bulk_delete_tasks,
    bulk_move_to_project,
    # Advanced search (4 tools)
    unified_search,
    search_by_tags,
    advanced_task_filter,
    get_task_statistics,
]

# Create ReAct agent once (following tutorial pattern)
_task_react_agent = None


def _get_task_agent():
    """
    Get or create the task agent.

    Following LangGraph tutorial pattern: agent created once, reused forever.

    Returns:
        Cached ReAct agent
    """
    global _task_react_agent
    if _task_react_agent is None:
        _task_react_agent = create_cached_react_agent(
            agent_name="task_agent",
            tools=TASK_TOOLS,
            temperature=0.7,
        )
    return _task_react_agent


# ============================================================================
# AGENT NODE (Simple function following tutorial pattern)
# ============================================================================

async def task_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Task Agent node for LangGraph workflow.

    Following LangGraph tutorial pattern:
    - Simple function taking state, returning state updates
    - Reuses cached agent (no recreation)
    - Context injected via messages (not templates)

    Args:
        state: Current conversation state

    Returns:
        State updates dict
    """
    logger.info("Task Agent activated")

    try:
        # Get cached agent (created once, reused forever)
        agent = _get_task_agent()

        # Create context message (following tutorial pattern)
        context_message = create_context_message(state, "task", TASK_AGENT_PROMPT)

        # Prepend context to messages
        messages_with_context = [context_message] + list(state["messages"])

        # Invoke agent (simple like tutorial)
        result = await agent.ainvoke(
            {"messages": messages_with_context},
            config={"recursion_limit": 60},
        )

        # Extract response
        last_message = result["messages"][-1]
        response_content = (
            last_message.content if hasattr(last_message, "content") else str(last_message)
        )

        logger.info(f"Task Agent response: {response_content[:100]}...")

        # Detect handoff
        should_handoff, target_agent, handoff_reason = await detect_handoff(
            state, "task_agent", response_content
        )

        # Update agent context (consolidated structure)
        agent_contexts = state.get("agent_contexts", {})
        agent_contexts["task"] = {
            "last_interaction": datetime.utcnow().isoformat(),
            "last_topic": response_content[:200],
        }

        # Prepare state updates (following tutorial pattern: return updates dict)
        updates = {
            "messages": result["messages"],
            "current_agent": "task_agent",
            "previous_agent": state.get("current_agent"),
            "agent_contexts": agent_contexts,
            "turn_count": state["turn_count"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Add handoff information if detected
        if should_handoff and target_agent:
            updates["target_agent"] = target_agent
            updates["handoff_reason"] = handoff_reason

            # Add handoff message
            handoff_msg = AIMessage(
                content=f"I'm transferring you to the {target_agent.replace('_', ' ').title()} who can better assist with that."
            )
            updates["messages"] = updates["messages"] + [handoff_msg]

        return updates

    except Exception as e:
        logger.error(f"Error in Task Agent: {e}", exc_info=True)
        error_msg = AIMessage(content="I encountered an error processing your request.")
        return {
            "messages": [error_msg],
            "current_agent": "task_agent",
            "turn_count": state["turn_count"] + 1,
        }
