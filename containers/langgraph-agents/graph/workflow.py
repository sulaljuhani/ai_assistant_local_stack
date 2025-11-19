"""
LangGraph workflow definition for multi-agent system.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from .state import MultiAgentState, prune_messages, should_prune_state
from .routing import route_to_agent, should_route_to_new_agent
from .checkpointer import RedisCheckpointSaver
from agents import food_agent_node, task_agent_node, event_agent_node
from utils.logging import get_logger

logger = get_logger(__name__)


def create_routing_node():
    """Create the routing node function."""

    async def routing_node(state: MultiAgentState) -> MultiAgentState:
        """
        Route to appropriate agent based on user message.

        Uses hybrid routing:
        - Simple keyword matching for clear cases
        - LLM routing for complex/ambiguous cases
        """
        logger.info("Routing node activated")

        # Prune state if needed
        if should_prune_state(state):
            logger.info("Pruning state messages")
            state["messages"] = prune_messages(state["messages"])

        # Determine target agent
        target = await route_to_agent(state)

        logger.info(f"Routed to: {target}")

        # Update state with routing decision
        return {
            **state,
            "current_agent": target,
            "target_agent": None,  # Clear any previous handoff
            "handoff_reason": None,
        }

    return routing_node


def should_continue(state: MultiAgentState) -> Literal["route", "end"]:
    """
    Determine if we should continue or end the conversation.

    Args:
        state: Current state

    Returns:
        "route" to continue routing, "end" to finish
    """
    # Check if handoff was requested
    if state.get("target_agent"):
        logger.info(f"Handoff to {state['target_agent']}, continuing")
        return "route"

    # Check if we need to route to a new agent
    if should_route_to_new_agent(state):
        logger.info("Re-routing needed")
        return "route"

    # Otherwise, conversation ends
    logger.info("Conversation ending")
    return "end"


def route_to_agent_node(state: MultiAgentState) -> Literal["food_agent", "task_agent", "event_agent"]:
    """
    Conditional edge function to route to specific agent.

    Args:
        state: Current state

    Returns:
        Agent node name
    """
    agent = state.get("current_agent", "food_agent")
    logger.info(f"Routing to agent node: {agent}")
    return agent


def create_workflow(checkpointer: BaseCheckpointSaver = None) -> StateGraph:
    """
    Create the LangGraph workflow for multi-agent system.

    Workflow structure:
    1. START → routing → agent
    2. agent → decision (continue or end)
    3. If continue → routing → agent (for handoffs)
    4. If end → END

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled workflow graph
    """
    logger.info("Creating workflow graph")

    # Create graph
    workflow = StateGraph(MultiAgentState)

    # Add nodes
    workflow.add_node("routing", create_routing_node())
    workflow.add_node("food_agent", food_agent_node)
    workflow.add_node("task_agent", task_agent_node)
    workflow.add_node("event_agent", event_agent_node)

    # Set entry point
    workflow.set_entry_point("routing")

    # Add conditional edge from routing to specific agent
    workflow.add_conditional_edges(
        "routing",
        route_to_agent_node,
        {
            "food_agent": "food_agent",
            "task_agent": "task_agent",
            "event_agent": "event_agent",
        }
    )

    # Add edges from each agent back to routing or end
    for agent in ["food_agent", "task_agent", "event_agent"]:
        workflow.add_conditional_edges(
            agent,
            should_continue,
            {
                "route": "routing",
                "end": END,
            }
        )

    # Compile workflow
    if checkpointer is None:
        checkpointer = RedisCheckpointSaver()

    app = workflow.compile(checkpointer=checkpointer)

    logger.info("Workflow graph created successfully")

    return app
