"""
Multi-agent state schema with Redis persistence and pruning.
"""

from typing import TypedDict, Annotated, Optional, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


class MultiAgentState(TypedDict):
    """
    Shared state across all agents with domain-specific contexts.

    This state is persisted in Redis and passed between agents during handoffs.

    Key improvements:
    - Uses add_messages reducer for automatic message handling
    - Consolidated agent_contexts dict (simpler than separate dicts)
    - Minimal state fields (following LangGraph best practices)
    """

    # Conversation history (with automatic message appending via add_messages)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Active agent tracking
    current_agent: str
    previous_agent: Optional[str]

    # User context
    user_id: str
    workspace: str
    session_id: str

    # Domain-specific contexts (consolidated - each agent updates its own key)
    agent_contexts: dict  # {"food": {...}, "task": {...}, "event": {...}, "memory": {...}}

    # Handoff metadata
    handoff_reason: Optional[str]
    target_agent: Optional[str]

    # Metadata
    turn_count: int
    created_at: str
    updated_at: str


def prune_messages(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """
    Prune message history to keep state manageable.

    Strategy:
    - Keep first message (context)
    - Keep last N messages (recent conversation)
    - Summarize middle if needed (future enhancement)

    Args:
        messages: Full message history

    Returns:
        Pruned message list
    """
    if not settings.state_pruning_enabled:
        return list(messages)

    max_messages = settings.state_max_messages

    if len(messages) <= max_messages:
        return list(messages)

    logger.info(f"Pruning messages: {len(messages)} -> {max_messages}")

    # Keep first message (initial context) and last N-1 messages
    pruned = [messages[0]] + list(messages[-(max_messages - 1):])

    # Log what we're dropping
    dropped_count = len(messages) - len(pruned)
    logger.debug(f"Dropped {dropped_count} messages from history")

    return pruned


def create_initial_state(
    user_id: str,
    workspace: str,
    session_id: str,
    initial_message: Optional[str] = None
) -> MultiAgentState:
    """
    Create initial state for a new conversation.

    Args:
        user_id: User identifier
        workspace: Workspace identifier
        session_id: Conversation session ID
        initial_message: Optional first message

    Returns:
        Initial state dictionary
    """
    from datetime import datetime

    now = datetime.utcnow().isoformat()

    messages = []
    if initial_message:
        messages.append(HumanMessage(content=initial_message))

    return MultiAgentState(
        messages=messages,
        current_agent="",  # Will be set by router
        previous_agent=None,
        user_id=user_id,
        workspace=workspace,
        session_id=session_id,
        agent_contexts={},  # Consolidated contexts
        handoff_reason=None,
        target_agent=None,
        turn_count=0,
        created_at=now,
        updated_at=now,
    )


def should_prune_state(state: MultiAgentState) -> bool:
    """
    Check if state should be pruned.

    Args:
        state: Current state

    Returns:
        True if pruning is needed
    """
    if not settings.state_pruning_enabled:
        return False

    return len(state["messages"]) > settings.state_max_messages
