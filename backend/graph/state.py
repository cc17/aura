"""Shared state for the Aura multi-agent graph."""

from __future__ import annotations

from langgraph.graph import MessagesState


class AuraState(MessagesState):
    """Graph state shared across supervisor, worker agents and reflection."""

    active_agent: str = ""
    route_decision: str = ""

    # Reflection loop controls
    loop_count: int = 0       # how many times we've looped back through a worker
    critique: str = ""        # feedback injected by reflection node on retry
    reflection_done: bool = False  # True once we exit the loop (quality OK or max loops)
