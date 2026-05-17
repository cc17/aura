"""General-purpose chat agent — handles everyday conversations."""

from __future__ import annotations

from backend.graph.agents.base import create_worker_node

SYSTEM_PROMPT = (
    "You are Aura, a helpful AI assistant. "
    "Answer the user's questions clearly and concisely. "
    "You do not have any special tools — just use your knowledge."
)


def create_general_agent(model: str | None = None):
    return create_worker_node(
        agent_name="general_agent",
        system_prompt=SYSTEM_PROMPT,
        tools=None,
        model=model,
    )
