"""
Hybrid routing logic for agent selection.

Strategy: Simple queries → direct routing via keywords
         Complex queries → LLM-based routing
"""

from typing import Literal
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from .state import MultiAgentState
from utils.llm import get_routing_llm
from utils.logging import get_logger

logger = get_logger(__name__)


class RoutingDecision(BaseModel):
    """Structured routing decision."""

    agent: Literal["food_agent", "task_agent", "event_agent", "memory_agent"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


# Simple keyword patterns for direct routing
FOOD_KEYWORDS = [
    "food", "meal", "eat", "ate", "eating", "lunch", "dinner", "breakfast",
    "snack", "hungry", "diet", "nutrition", "recipe", "cook", "restaurant",
    "suggest something to eat", "what should i eat", "food recommendation"
]

TASK_KEYWORDS = [
    "task", "todo", "do", "complete", "finish", "deadline", "priority",
    "remind", "reminder", "project", "work on", "need to", "have to",
    "create a task", "add task", "task list"
]

EVENT_KEYWORDS = [
    "event", "calendar", "schedule", "meeting", "appointment", "plan",
    "time", "date", "today", "tomorrow", "week", "available", "busy",
    "book", "reserve", "add to calendar"
]

MEMORY_KEYWORDS = [
    "remember", "note", "save", "recall", "memory", "wrote", "document",
    "search for", "find", "notes", "knowledge", "information about"
]


def simple_keyword_routing(message: str) -> str | None:
    """
    Attempt simple keyword-based routing.

    Args:
        message: User message content

    Returns:
        Agent name if confident match, None otherwise
    """
    message_lower = message.lower()

    # Count keyword matches for each domain
    food_score = sum(1 for kw in FOOD_KEYWORDS if kw in message_lower)
    task_score = sum(1 for kw in TASK_KEYWORDS if kw in message_lower)
    event_score = sum(1 for kw in EVENT_KEYWORDS if kw in message_lower)
    memory_score = sum(1 for kw in MEMORY_KEYWORDS if kw in message_lower)

    scores = {
        "food_agent": food_score,
        "task_agent": task_score,
        "event_agent": event_score,
        "memory_agent": memory_score,
    }

    # Get highest scoring agent
    max_agent = max(scores.items(), key=lambda x: x[1])

    # Require at least 2 keyword matches and clear winner
    if max_agent[1] >= 2:
        # Check if it's a clear winner (2x more than others)
        other_scores = [s for a, s in scores.items() if a != max_agent[0]]
        if not other_scores or max_agent[1] >= 2 * max(other_scores):
            logger.info(f"Simple routing: '{message[:50]}...' → {max_agent[0]} (score: {max_agent[1]})")
            return max_agent[0]

    return None


async def llm_routing(message: str, context: dict) -> RoutingDecision:
    """
    Use LLM to make routing decision for complex/ambiguous queries.

    Args:
        message: User message content
        context: Additional context (previous agent, conversation history, etc.)

    Returns:
        Structured routing decision
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a routing agent that determines which specialized agent should handle a user's request.

Available agents:
- food_agent: Handles food logging, meal suggestions, dietary patterns, nutrition
- task_agent: Handles task creation, planning, productivity, todos, reminders
- event_agent: Handles calendar events, scheduling, meetings, time management
- memory_agent: Handles notes, knowledge storage, information retrieval

Analyze the user's message and determine which agent is most appropriate.
Consider:
1. The primary intent of the message
2. Which agent has the most relevant expertise
3. Context from previous conversation if available

Be decisive - pick the single most appropriate agent."""),
        ("user", """Message: {message}

Previous agent: {previous_agent}
Context: {context}

Which agent should handle this request? Provide your reasoning.""")
    ])

    llm = get_routing_llm()

    # Use structured output
    structured_llm = llm.with_structured_output(RoutingDecision)

    try:
        decision = await structured_llm.ainvoke(
            prompt.format_messages(
                message=message,
                previous_agent=context.get("previous_agent", "none"),
                context=str(context)
            )
        )

        logger.info(
            f"LLM routing: '{message[:50]}...' → {decision.agent} "
            f"(confidence: {decision.confidence:.2f}, reason: {decision.reason})"
        )

        return decision

    except Exception as e:
        logger.error(f"LLM routing failed: {e}, defaulting to food_agent")
        return RoutingDecision(
            agent="food_agent",
            confidence=0.5,
            reason="Default fallback due to routing error"
        )


async def route_to_agent(state: MultiAgentState) -> str:
    """
    Main routing function using hybrid strategy.

    Strategy:
    1. Try simple keyword routing first (fast)
    2. Fall back to LLM routing for complex/ambiguous cases

    Args:
        state: Current conversation state

    Returns:
        Agent name to route to
    """
    # Get last user message
    messages = state["messages"]
    if not messages:
        return "food_agent"  # Default

    last_message = messages[-1]
    message_content = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # Try simple routing first
    simple_result = simple_keyword_routing(message_content)
    if simple_result:
        return simple_result

    # Fall back to LLM routing
    context = {
        "previous_agent": state.get("previous_agent"),
        "current_agent": state.get("current_agent"),
        "turn_count": state.get("turn_count", 0),
    }

    decision = await llm_routing(message_content, context)
    return decision.agent


def should_route_to_new_agent(state: MultiAgentState) -> bool:
    """
    Check if we should re-route to a different agent.

    Args:
        state: Current conversation state

    Returns:
        True if routing is needed
    """
    # Route if:
    # 1. No current agent set
    # 2. Explicit handoff requested
    # 3. User message suggests domain shift

    if not state.get("current_agent"):
        return True

    if state.get("target_agent"):
        return True

    # Check if last message suggests domain shift
    # (This would be enhanced with more sophisticated detection)
    messages = state["messages"]
    if messages and len(messages) > 0:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            # Simple check for explicit agent requests
            content_lower = last_msg.content.lower()
            if any(phrase in content_lower for phrase in [
                "switch to", "talk to", "ask the", "different agent"
            ]):
                return True

    return False
