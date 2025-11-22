"""
Reminder Agent - Specialized in scheduling and managing reminders.

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
    search_reminders,
    create_reminder,
    update_reminder,
    complete_reminder,
    get_reminders_today,
    get_reminders_due_soon,
    unified_search,
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
REMINDER_AGENT_PROMPT = load_system_prompt("reminder_agent")

# Define tools once
REMINDER_TOOLS = [
    search_reminders,
    create_reminder,
    update_reminder,
    complete_reminder,
    get_reminders_today,
    get_reminders_due_soon,
    unified_search,
]

# Create ReAct agent once (following tutorial pattern)
_reminder_react_agent = None


def _get_reminder_agent():
    """
    Get or create the reminder agent.

    Following LangGraph tutorial pattern: agent created once, reused forever.

    Returns:
        Cached ReAct agent
    """
    global _reminder_react_agent
    if _reminder_react_agent is None:
        _reminder_react_agent = create_cached_react_agent(
            agent_name="reminder_agent",
            tools=REMINDER_TOOLS,
            temperature=0.7,
        )
    return _reminder_react_agent


# ============================================================================
# AGENT NODE (Simple function following tutorial pattern)
# ============================================================================

async def reminder_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Reminder Agent node for LangGraph workflow.

    Follows the same pattern as other agents: cached agent, context message,
    simple invocation, and optional handoff.
    """
    logger.info("Reminder Agent activated")

    try:
        agent = _get_reminder_agent()

        context_message = create_context_message(state, "reminder", REMINDER_AGENT_PROMPT)
        messages_with_context = [context_message] + list(state["messages"])

        result = await agent.ainvoke(
            {"messages": messages_with_context},
            config={"recursion_limit": 60},
        )

        last_message = result["messages"][-1]
        response_content = (
            last_message.content if hasattr(last_message, "content") else str(last_message)
        )

        logger.info(f"Reminder Agent response: {response_content[:100]}...")

        should_handoff, target_agent, handoff_reason = await detect_handoff(
            state, "reminder_agent", response_content
        )

        agent_contexts = state.get("agent_contexts", {})
        agent_contexts["reminder"] = {
            "last_interaction": datetime.utcnow().isoformat(),
            "last_topic": response_content[:200],
        }

        updates = {
            "messages": result["messages"],
            "current_agent": "reminder_agent",
            "previous_agent": state.get("current_agent"),
            "agent_contexts": agent_contexts,
            "turn_count": state["turn_count"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if should_handoff and target_agent:
            updates["target_agent"] = target_agent
            updates["handoff_reason"] = handoff_reason

            handoff_msg = AIMessage(
                content=f"I'm transferring you to the {target_agent.replace('_', ' ').title()} who can better assist with that."
            )
            updates["messages"] = updates["messages"] + [handoff_msg]

        return updates

    except Exception as e:
        logger.error(f"Error in Reminder Agent: {e}", exc_info=True)
        error_msg = AIMessage(content="I encountered an error processing your request.")
        return {
            "messages": [error_msg],
            "current_agent": "reminder_agent",
            "turn_count": state["turn_count"] + 1,
        }
