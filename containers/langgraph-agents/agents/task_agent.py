"""
Task Agent - Specialized in task management, planning, and productivity.
"""

from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from graph.state import MultiAgentState
from tools import (
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    get_tasks_due_soon,
)
from utils.llm import get_agent_llm
from utils.logging import get_logger
from .base import load_system_prompt, create_agent_prompt, detect_handoff

logger = get_logger(__name__)


# Load system prompt
TASK_AGENT_PROMPT = load_system_prompt("task_agent")


# Define tools available to task agent
TASK_TOOLS = [
    search_tasks,
    create_task,
    update_task,
    get_tasks_by_priority,
    get_tasks_due_soon,
]


async def task_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Task Agent node for LangGraph workflow.

    Handles task-related queries and actions, detects handoffs.

    Args:
        state: Current conversation state

    Returns:
        State updates
    """
    logger.info("Task Agent activated")

    # Create agent with tools
    llm = get_agent_llm(temperature=0.7)
    prompt = create_agent_prompt("task_agent", TASK_AGENT_PROMPT)

    agent = create_react_agent(
        model=llm,
        tools=TASK_TOOLS,
        state_modifier=prompt.partial(
            user_id=state["user_id"],
            workspace=state["workspace"],
            turn_count=state["turn_count"],
            food_context=str(state.get("food_context", {})),
            task_context=str(state.get("task_context", {})),
            event_context=str(state.get("event_context", {})),
        )
    )

    # Run agent
    try:
        result = await agent.ainvoke({"messages": state["messages"]})

        # Get agent's response
        last_message = result["messages"][-1]
        response_content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        logger.info(f"Task Agent response: {response_content[:100]}...")

        # Detect handoff
        should_handoff, target_agent, handoff_reason = await detect_handoff(
            state,
            "task_agent",
            response_content
        )

        # Update task context
        task_context = state.get("task_context", {})
        task_context["last_interaction"] = datetime.utcnow().isoformat()
        task_context["last_topic"] = response_content[:200]

        # Prepare state updates
        updates = {
            "messages": result["messages"],
            "current_agent": "task_agent",
            "previous_agent": state.get("current_agent"),
            "task_context": task_context,
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
        logger.error(f"Error in Task Agent: {e}")
        error_msg = AIMessage(content=f"I encountered an error: {str(e)}")
        return {
            "messages": [error_msg],
            "current_agent": "task_agent",
            "turn_count": state["turn_count"] + 1,
        }
