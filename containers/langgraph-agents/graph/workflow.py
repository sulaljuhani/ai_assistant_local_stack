"""
LangGraph workflow definition for multi-agent system.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from .state import MultiAgentState, prune_messages, should_prune_state
from .routing import route_to_agent, should_route_to_new_agent
from .checkpointer import RedisCheckpointSaver
from agents import food_agent_node, task_agent_node, event_agent_node, reminder_agent_node
from utils.logging import get_logger

logger = get_logger(__name__)


def create_routing_node():
    """
    Create the classifier + router node.

    Following LangGraph tutorial pattern but combined for efficiency.
    This node performs both classification (determining message type)
    and routing (selecting appropriate agent).

    Tutorial equivalent:
    - Tutorial: separate "classifier" + "router" nodes
    - This system: combined into one "routing" node (more efficient for 3+ agents)
    """

    async def routing_node(state: MultiAgentState) -> MultiAgentState:
        """
        Classify message type and route to appropriate agent.

        Hybrid routing strategy (more sophisticated than tutorial):
        1. Keyword classification (fast path) - O(1) lookup
        2. LLM classification (fallback) - For ambiguous cases
        3. Context-aware routing - Considers previous agent, handoff requests

        Returns:
            State update with routing decision
        """
        logger.info("Routing node: classifying and routing message")

        # Prune state if needed (prevent memory bloat)
        if should_prune_state(state):
            logger.info("Pruning state messages to maintain context window")
            state["messages"] = prune_messages(state["messages"])

        # Classify message type and determine target agent
        # (Combined classifier + router logic in route_to_agent)
        target = await route_to_agent(state)

        logger.info(f"Classification complete → routed to: {target}")

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


def route_to_agent_node(state: MultiAgentState) -> Literal["food_agent", "task_agent", "event_agent", "reminder_agent"]:
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

    Workflow structure (enhanced from LangGraph tutorial):

    START → routing (classifier+router) → [food_agent | task_agent | event_agent | reminder_agent]
                ↑                                                   ↓
                └────────────────────────── should_continue ───────┘
                                           ↓
                                         END

    Differences from tutorial:
    - Tutorial: START → classifier → router → agent → END (linear)
    - This: START → routing → agent → (loop or end) (supports handoffs)

    Nodes:
    1. START (implicit entry point)
    2. routing - Combined classifier + router (more efficient than 2 nodes)
    3. food_agent, task_agent, event_agent, reminder_agent - Specialized agents
    4. should_continue - Decision function (route for handoff, or end)
    5. END (terminal state)

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled workflow graph
    """
    logger.info("Creating workflow graph")

    # Create graph
    workflow = StateGraph(MultiAgentState)

    # Add nodes (following tutorial pattern with enhancements)
    workflow.add_node("routing", create_routing_node())  # Classifier + Router combined
    workflow.add_node("food_agent", food_agent_node)     # Specialist agent
    workflow.add_node("task_agent", task_agent_node)     # Specialist agent
    workflow.add_node("event_agent", event_agent_node)   # Specialist agent
    workflow.add_node("reminder_agent", reminder_agent_node)   # Specialist agent

    # Set entry point (like tutorial's START → first_node)
    workflow.set_entry_point("routing")

    # Add conditional edge from routing to specific agent
    workflow.add_conditional_edges(
        "routing",
        route_to_agent_node,
        {
            "food_agent": "food_agent",
            "task_agent": "task_agent",
            "event_agent": "event_agent",
            "reminder_agent": "reminder_agent",
        }
    )

    # Add edges from each agent back to routing or end
    for agent in ["food_agent", "task_agent", "event_agent", "reminder_agent"]:
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
