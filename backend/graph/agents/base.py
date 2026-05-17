"""Factory for creating worker agent nodes."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool as LCBaseTool

from backend.graph.state import AuraState
from backend.llm.langchain_bridge import create_chat_model

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def create_worker_node(
    agent_name: str,
    system_prompt: str,
    tools: list[LCBaseTool] | None = None,
    model: str | None = None,
):
    """Create a worker agent node for the LangGraph.

    Each worker runs a ReAct loop (tool calls → observe → respond) for up to
    MAX_TOOL_ROUNDS rounds, then returns.  If the reflection node injected a
    critique into state.critique, it is appended to the conversation as a
    HumanMessage before the LLM call so the agent can improve its response.
    """
    llm = create_chat_model(model)
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    tools_by_name = {t.name: t for t in tools} if tools else {}

    async def node(state: AuraState) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        messages: list[Any] = [SystemMessage(content=system_prompt)] + list(state["messages"])

        # Inject reflection critique as a fresh human turn when retrying
        critique = state.get("critique", "")
        if critique:
            messages.append(
                HumanMessage(
                    content=(
                        f"[Self-critique — please improve your previous response]\n{critique}"
                    )
                )
            )

        for _ in range(MAX_TOOL_ROUNDS):
            response: AIMessage = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return {
                    "messages": [response],
                    "active_agent": agent_name,
                    "critique": "",  # clear critique after use
                }

            tool_messages = []
            for tc in response.tool_calls:
                tool = tools_by_name.get(tc["name"])
                if tool:
                    try:
                        result = await tool.ainvoke(tc["args"])
                    except Exception as exc:
                        logger.exception("Tool '%s' raised", tc["name"])
                        result = f"Error executing tool {tc['name']}: {exc}"
                else:
                    result = f"Error: Tool '{tc['name']}' not found"
                tool_messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            messages.extend(tool_messages)

        # Exceeded tool rounds — return whatever we have
        return {
            "messages": messages[len(state["messages"]) + 1 :],
            "active_agent": agent_name,
            "critique": "",
        }

    return node
