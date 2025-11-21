"""
Food Agent - Specialized in food logging, recommendations, and dietary patterns.

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
    search_food_log,
    log_food_entry,
    update_food_entry,
    get_food_by_rating,
    analyze_food_patterns,
    vector_search_foods,
    get_food_recommendations,
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
FOOD_AGENT_PROMPT = load_system_prompt("food_agent")

# Define tools once
FOOD_TOOLS = [
    search_food_log,
    log_food_entry,
    update_food_entry,
    get_food_by_rating,
    analyze_food_patterns,
    vector_search_foods,
    get_food_recommendations,
]

# Create ReAct agent once (following tutorial pattern)
_food_react_agent = None


def _get_food_agent():
    """
    Get or create the food agent.

    Following LangGraph tutorial pattern: agent created once, reused forever.

    Returns:
        Cached ReAct agent
    """
    global _food_react_agent
    if _food_react_agent is None:
        _food_react_agent = create_cached_react_agent(
            agent_name="food_agent",
            tools=FOOD_TOOLS,
            temperature=0.7,
        )
    return _food_react_agent


# ============================================================================
# AGENT NODE (Simple function following tutorial pattern)
# ============================================================================

async def food_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Food Agent node for LangGraph workflow.

    Following LangGraph tutorial pattern:
    - Simple function taking state, returning state updates
    - Reuses cached agent (no recreation)
    - Context injected via messages (not templates)

    Args:
        state: Current conversation state

    Returns:
        State updates dict
    """
    logger.info("Food Agent activated")

    try:
        # Get cached agent (created once, reused forever)
        agent = _get_food_agent()

        # Create context message (following tutorial pattern)
        context_message = create_context_message(state, "food", FOOD_AGENT_PROMPT)

        # Prepend context to messages
        messages_with_context = [context_message] + list(state["messages"])

        # Invoke agent (simple like tutorial)
        result = await agent.ainvoke({"messages": messages_with_context})

        # Extract response
        last_message = result["messages"][-1]
        response_content = (
            last_message.content if hasattr(last_message, "content") else str(last_message)
        )

        logger.info(f"Food Agent response: {response_content[:100]}...")

        # Detect handoff
        should_handoff, target_agent, handoff_reason = await detect_handoff(
            state, "food_agent", response_content
        )

        # Update agent context (consolidated structure)
        agent_contexts = state.get("agent_contexts", {})
        agent_contexts["food"] = {
            "last_interaction": datetime.utcnow().isoformat(),
            "last_topic": response_content[:200],
        }

        # Prepare state updates (following tutorial pattern: return updates dict)
        updates = {
            "messages": result["messages"],
            "current_agent": "food_agent",
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
        logger.error(f"Error in Food Agent: {e}", exc_info=True)
        error_msg = AIMessage(content="I encountered an error processing your request.")
        return {
            "messages": [error_msg],
            "current_agent": "food_agent",
            "turn_count": state["turn_count"] + 1,
        }
