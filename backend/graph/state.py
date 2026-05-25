"""Shared state for the Aura multi-agent graph."""

from __future__ import annotations

from langgraph.graph import MessagesState


class AuraState(MessagesState):
    """Graph state shared across supervisor, worker agents and reflection."""

    active_agent: str = ""
    route_decision: str = ""

    # Set by an agent when it needs more info from the user (multi-turn clarification).
    # Supervisor reads this to decide whether to run the continuation check instead of
    # re-classifying from scratch.  Cleared when the agent delivers its final answer.
    pending_agent: str = ""

    # User-selected model for worker agents (supervisor/reflection always use their own models)
    worker_model: str = ""

    # Reflection loop controls
    loop_count: int = 0       # how many times we've looped back through a worker
    critique: str = ""        # feedback injected by reflection node on retry
    reflection_done: bool = False  # True once we exit the loop (quality OK or max loops)
