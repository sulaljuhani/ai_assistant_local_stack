"""
Base agent functionality with handoff detection.
"""

from typing import Literal, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from graph.state import MultiAgentState
from utils.llm import get_agent_llm
from utils.logging import get_logger

logger = get_logger(__name__)


class HandoffDecision(BaseModel):
    """Structured handoff decision."""

    should_handoff: bool
    target_agent: Optional[Literal["food_agent", "task_agent", "event_agent", "memory_agent"]] = None
    reason: Optional[str] = None


async def detect_handoff(
    state: MultiAgentState,
    current_agent: str,
    last_response: str
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Detect if handoff is needed based on conversation.

    Uses LLM to detect domain shifts and determine if another agent
    should handle the request.

    Args:
        state: Current conversation state
        current_agent: Name of current agent
        last_response: Agent's last response

    Returns:
        Tuple of (should_handoff, target_agent, reason)
    """
    # Check if explicit handoff was requested in state
    if state.get("target_agent"):
        target = state["target_agent"]
        reason = state.get("handoff_reason", "Explicit handoff requested")
        logger.info(f"Explicit handoff: {current_agent} → {target}")
        return True, target, reason

    # Get last user message
    messages = state["messages"]
    if not messages or len(messages) < 2:
        return False, None, None

    # Find last human message
    last_human_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_msg = msg.content
            break

    if not last_human_msg:
        return False, None, None

    # Use LLM to detect domain shift
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a handoff detection system for a multi-agent system.

Current agent: {current_agent}

Agent domains:
- food_agent: Food, meals, eating, nutrition, dietary preferences
- task_agent: Tasks, todos, reminders, productivity, planning
- event_agent: Calendar, schedule, meetings, appointments, availability
- memory_agent: Notes, memories, information storage and retrieval

Analyze if the user's request requires a different agent.
Look for:
1. Explicit requests ("create a task", "add to calendar", etc.)
2. Domain-specific keywords
3. Context shift from current domain

Be decisive but don't over-trigger handoffs for casual mentions."""),
        ("user", """User's message: {user_message}
Agent's response: {agent_response}

Should we hand off to a different agent?""")
    ])

    llm = get_agent_llm(temperature=0.3)
    structured_llm = llm.with_structured_output(HandoffDecision)

    try:
        decision = await structured_llm.ainvoke(
            prompt.format_messages(
                current_agent=current_agent,
                user_message=last_human_msg,
                agent_response=last_response
            )
        )

        if decision.should_handoff:
            logger.info(
                f"Handoff detected: {current_agent} → {decision.target_agent} "
                f"(reason: {decision.reason})"
            )
            return True, decision.target_agent, decision.reason
        else:
            return False, None, None

    except Exception as e:
        logger.error(f"Error detecting handoff: {e}")
        return False, None, None


def load_system_prompt(agent_name: str) -> str:
    """
    Load system prompt from file.

    Args:
        agent_name: Name of agent (food_agent, task_agent, etc.)

    Returns:
        System prompt text
    """
    import os

    prompt_file = f"prompts/{agent_name}.txt"

    try:
        if os.path.exists(prompt_file):
            with open(prompt_file, "r") as f:
                return f.read().strip()
        else:
            logger.warning(f"Prompt file not found: {prompt_file}")
            return f"You are a helpful {agent_name.replace('_', ' ')}."
    except Exception as e:
        logger.error(f"Error loading prompt: {e}")
        return f"You are a helpful {agent_name.replace('_', ' ')}."


def create_agent_prompt(agent_name: str, system_prompt: str) -> ChatPromptTemplate:
    """
    Create agent prompt template with system prompt and context.

    Args:
        agent_name: Name of agent
        system_prompt: System prompt text

    Returns:
        Prompt template
    """
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("system", """
## Context Information

User ID: {user_id}
Workspace: {workspace}
Turn: {turn_count}

## Domain Contexts (from other agents)

Food Context: {food_context}
Task Context: {task_context}
Event Context: {event_context}

Use this context to provide informed responses."""),
        MessagesPlaceholder(variable_name="messages"),
    ])
