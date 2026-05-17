"""Agent core — bridges LangGraph multi-agent graph to SSE StreamEvent iterator.

Output gating strategy
──────────────────────
Only the FINAL reflection-approved iteration's text/tool output is sent as
real content events.  Everything in between is surfaced as THINKING events
so the user can see progress without polluting the final answer.

What gets emitted as THINKING:
  • Tool calls in intermediate iterations  →  "🔍 搜索中: {query}" etc.
  • Reflection retry decision              →  score + critique text
  • Reflection approving on 2nd+ try      →  "✓ 回答已优化 (第N轮)"

What stays buffered until final flush:
  • AGENT_START / TEXT_DELTA / TOOL_CALL / TOOL_RESULT from the approved run
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from backend.agent.schemas import (
    Message,
    Role,
    StreamEvent,
    StreamEventType,
)
from backend.graph.supervisor import WORKER_AGENTS, get_graph

# Agents that stream tokens directly to the client without buffering.
# They skip the reflection LLM call (reflection returns immediately) so
# there is no retry risk — safe to stream before approval.
_DIRECT_STREAM_AGENTS = frozenset({"general_agent"})
from backend.observability import trace

logger = logging.getLogger(__name__)

# Human-readable labels for tools shown in THINKING events
_TOOL_THINKING_LABELS: dict[str, str] = {
    "web_search":      "🔍 搜索网络",
    "url_scraper":     "📄 读取网页",
    "search_jobs":     "💼 搜索职位",
    "resume_advisor":  "📋 分析简历",
    "ppt_builder":     "📊 生成PPT",
    "find_schools":    "🏫 查询院校",
    "score_to_rank":   "📈 换算位次",
    "career_outlook":  "🔭 分析就业",
    "export_docx":     "📝 导出文档",
}


def _tool_thinking_text(tool_name: str, tool_input: dict) -> str:
    label = _TOOL_THINKING_LABELS.get(tool_name, f"🔧 调用 {tool_name}")
    # Append the most informative argument as context
    detail = (
        tool_input.get("query")
        or tool_input.get("url")
        or tool_input.get("resume_text", "")[:40]
        or ""
    )
    return f"{label}: {detail}".strip().rstrip(":")


def _convert_history(history: list[Message]) -> list[Any]:
    from langchain_core.messages import AIMessage, HumanMessage as LCHuman, SystemMessage

    lc_messages = []
    for msg in history:
        if msg.role == Role.USER:
            lc_messages.append(LCHuman(content=msg.content or ""))
        elif msg.role == Role.ASSISTANT:
            lc_messages.append(AIMessage(content=msg.content or ""))
        elif msg.role == Role.SYSTEM:
            lc_messages.append(SystemMessage(content=msg.content or ""))
    return lc_messages


def _thinking(text: str) -> StreamEvent:
    return StreamEvent(event=StreamEventType.THINKING, data={"text": text})


class AgentCore:
    """Streams LangGraph execution as SSE events.

    Intermediate reflection-loop iterations produce THINKING events only.
    The final approved iteration is flushed as normal content events.
    """

    async def run(
        self,
        history: list[Message],
        model: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        graph = get_graph()
        lc_messages = _convert_history(history)
        input_state = {
            "messages": lc_messages,
            "loop_count": 0,
            "critique": "",
            "reflection_done": False,
        }

        _iter_buffer: list[StreamEvent] = []
        _current_agent: str | None = None
        _is_retry: bool = False  # True after the first iteration is rejected
        _tool_start_times: dict[str, float] = {}  # run_id → start time
        _direct_mode: bool = False  # True when streaming general_agent without buffer
        _done_sent: bool = False

        try:
            async for event in graph.astream_events(input_state, version="v2"):
                kind = event.get("event", "")
                name = event.get("name", "")
                metadata = event.get("metadata", {})
                node = metadata.get("langgraph_node", "")

                # ── agent start ───────────────────────────────────────────
                if kind == "on_chain_start" and node in WORKER_AGENTS:
                    _current_agent = node
                    _direct_mode = node in _DIRECT_STREAM_AGENTS
                    start_evt = StreamEvent(event=StreamEventType.AGENT_START, data={"agent": node})
                    if _direct_mode:
                        yield start_evt
                    else:
                        _iter_buffer.append(start_evt)

                # ── text tokens ───────────────────────────────────────────
                if kind == "on_chat_model_stream" and node in WORKER_AGENTS:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        delta = StreamEvent(event=StreamEventType.TEXT_DELTA, data={"text": chunk.content})
                        if _direct_mode:
                            yield delta
                        else:
                            _iter_buffer.append(delta)

                # ── tool call start ───────────────────────────────────────
                if kind == "on_tool_start" and node in WORKER_AGENTS:
                    tool_input = event.get("data", {}).get("input", {})
                    run_id = event.get("run_id", "")
                    _tool_start_times[run_id] = __import__("time").perf_counter()

                    trace(
                        "tool_call_start",
                        tool=name,
                        agent=_current_agent,
                        input_preview=str(tool_input)[:120],
                    )

                    # Always show tool activity as THINKING (immediate, not buffered)
                    thinking_text = _tool_thinking_text(
                        name, tool_input if isinstance(tool_input, dict) else {}
                    )
                    yield _thinking(thinking_text)

                    # Also buffer the structured TOOL_CALL event for the final flush
                    _iter_buffer.append(
                        StreamEvent(
                            event=StreamEventType.TOOL_CALL,
                            data={
                                "tool_call_id": run_id,
                                "name": name,
                                "arguments": tool_input if isinstance(tool_input, dict) else {},
                            },
                        )
                    )

                # ── tool result → buffer ──────────────────────────────────
                if kind == "on_tool_end" and node in WORKER_AGENTS:
                    run_id = event.get("run_id", "")
                    output = event.get("data", {}).get("output", "")
                    elapsed = round(
                        (__import__("time").perf_counter() - _tool_start_times.pop(run_id, __import__("time").perf_counter())) * 1000, 1
                    )
                    error = event.get("data", {}).get("error")
                    trace(
                        "tool_call_error" if error else "tool_call_end",
                        tool=name,
                        agent=_current_agent,
                        elapsed_ms=elapsed,
                        result_len=len(str(output)),
                        **({"error": str(error)[:120]} if error else {}),
                    )
                    _iter_buffer.append(
                        StreamEvent(
                            event=StreamEventType.TOOL_RESULT,
                            data={
                                "tool_call_id": run_id,
                                "name": name,
                                "result": str(output),
                            },
                        )
                    )

                # ── reflection gate ───────────────────────────────────────
                # LangGraph fires on_chain_end for both the node itself and any
                # sub-chains it calls (e.g. the LLM call inside reflection).
                # Guard: only process events whose output dict contains
                # "reflection_done" — that's exclusively our node's return value.
                if kind == "on_chain_end" and node == "reflection":
                    output_data = event.get("data", {}).get("output", {})
                    if not isinstance(output_data, dict) or "reflection_done" not in output_data:
                        continue
                    done: bool = (
                        output_data.get("reflection_done", True)
                        if isinstance(output_data, dict)
                        else True
                    )
                    loop_count: int = (
                        output_data.get("loop_count", 0)
                        if isinstance(output_data, dict)
                        else 0
                    )
                    critique: str = (
                        output_data.get("critique", "")
                        if isinstance(output_data, dict)
                        else ""
                    )

                    if _direct_mode:
                        # Tokens were already streamed — just close out the agent
                        if done and not _done_sent:
                            if _current_agent:
                                yield StreamEvent(
                                    event=StreamEventType.AGENT_END,
                                    data={"agent": _current_agent},
                                )
                            yield StreamEvent(event=StreamEventType.DONE, data={})
                            _done_sent = True
                            logger.debug("Reflection gate: direct-stream DONE agent=%s", _current_agent)
                        _iter_buffer = []
                        _current_agent = None
                        _direct_mode = False
                        continue

                    if done:
                        if _is_retry:
                            yield _thinking(f"✓ 回答已优化完成（共 {loop_count} 轮迭代）")

                        # Flush approved iteration to client.
                        # TEXT_DELTA events get a small inter-token delay so the
                        # browser receives them in separate SSE frames and React
                        # renders each one individually — producing a typing effect.
                        import asyncio as _asyncio
                        for buffered in _iter_buffer:
                            yield buffered
                            if buffered.event == StreamEventType.TEXT_DELTA:
                                await _asyncio.sleep(0.012)
                        if _current_agent:
                            yield StreamEvent(
                                event=StreamEventType.AGENT_END,
                                data={"agent": _current_agent},
                            )
                        logger.debug("Reflection gate: FLUSH agent=%s", _current_agent)
                    else:
                        # Move the draft text into THINKING so the user can see
                        # what was attempted and why it was rejected — then discard
                        # it from the real output stream.
                        draft_text = "".join(
                            e.data["text"]
                            for e in _iter_buffer
                            if e.event == StreamEventType.TEXT_DELTA
                        )
                        if draft_text:
                            preview = draft_text[:300] + ("…" if len(draft_text) > 300 else "")
                            yield _thinking(f"📝 第 {loop_count} 轮草稿：{preview}")

                        hint = critique or "回答质量不足，继续优化…"
                        yield _thinking(f"💭 评估：{hint}")

                        _is_retry = True
                        logger.info(
                            "Reflection gate: DISCARD (retry) agent=%s loop=%s critique=%r",
                            _current_agent, loop_count, critique,
                        )

                    _iter_buffer = []
                    _current_agent = None

            if not _done_sent:
                yield StreamEvent(event=StreamEventType.DONE, data={})

        except Exception:
            logger.exception("Error in LangGraph execution")
            yield StreamEvent(
                event=StreamEventType.ERROR,
                data={"message": "Internal agent error"},
            )
