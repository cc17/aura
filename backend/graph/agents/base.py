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

    The LLM is created dynamically per call so the user-selected model
    (state["worker_model"]) takes effect without rebuilding the graph.
    """
    tools_list = tools or []
    tools_by_name = {t.name: t for t in tools_list}

    async def node(state: AuraState) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        resolved_model = state.get("worker_model") or model
        llm = create_chat_model(resolved_model)
        llm_with_tools = llm.bind_tools(tools_list) if tools_list else llm

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

        tools_were_called = False
        for _ in range(MAX_TOOL_ROUNDS):
            response: AIMessage = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                # If the model returned an empty response after tool calls, nudge it once
                content = response.content if isinstance(response.content, str) else ""
                if not content.strip() and len(messages) > 2:
                    logger.warning("%s: empty response after tool calls — nudging", agent_name)
                    messages.append(
                        HumanMessage(content="请根据以上工具调用结果，立即给出你的完整回答。")
                    )
                    continue

                # Detect clarification: agent asked a question without calling any tools.
                # Set pending_agent so the supervisor knows to use continuation detection
                # for the user's next reply, rather than re-classifying from scratch.
                # Check both ASCII "?" and full-width Chinese "？".
                has_question = "?" in content or "？" in content
                is_clarification = (
                    not tools_were_called
                    and has_question
                    and len(content) < 600
                )
                return {
                    "messages": [response],
                    "active_agent": agent_name,
                    "pending_agent": agent_name if is_clarification else "",
                    "critique": "",
                }

            tools_were_called = True
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

        # Exceeded tool rounds — return whatever we have (task done, clear pending)
        return {
            "messages": messages[len(state["messages"]) + 1 :],
            "active_agent": agent_name,
            "pending_agent": "",
            "critique": "",
        }

    return node
