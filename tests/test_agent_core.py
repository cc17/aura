"""Tests for AgentCore output-gating and THINKING event logic."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.agent.core import AgentCore
from backend.agent.schemas import Message, Role, StreamEventType


class FakeChunk:
    def __init__(self, text: str):
        self.content = text


def _reflection_end(done: bool, loop_count: int = 0, critique: str = ""):
    return {
        "event": "on_chain_end",
        "name": "reflection",
        "metadata": {"langgraph_node": "reflection"},
        "data": {
            "output": {
                "reflection_done": done,
                "loop_count": loop_count,
                "critique": critique,
            }
        },
    }


def _tool_start(agent: str, tool: str, run_id: str, args: dict):
    return {
        "event": "on_tool_start",
        "name": tool,
        "run_id": run_id,
        "metadata": {"langgraph_node": agent},
        "data": {"input": args},
    }


def _tool_end(agent: str, tool: str, run_id: str, output: str):
    return {
        "event": "on_tool_end",
        "name": tool,
        "run_id": run_id,
        "metadata": {"langgraph_node": agent},
        "data": {"output": output},
    }


def _text_chunk(agent: str, text: str):
    return {
        "event": "on_chat_model_stream",
        "name": "ChatLiteLLM",
        "metadata": {"langgraph_node": agent},
        "data": {"chunk": FakeChunk(text)},
    }


def _agent_start(agent: str):
    return {
        "event": "on_chain_start",
        "name": agent,
        "metadata": {"langgraph_node": agent},
        "data": {},
    }


# ── mock streams ──────────────────────────────────────────────────────────────

async def _stream_single_pass(input_state, *, version="v2"):
    yield _agent_start("general_agent")
    yield _text_chunk("general_agent", "Hello ")
    yield _text_chunk("general_agent", "world!")
    yield _reflection_end(done=True)


async def _stream_with_tool(input_state, *, version="v2"):
    yield _agent_start("resume_agent")
    yield _tool_start("resume_agent", "resume_modify", "call_abc",
                      {"resume_text": "my resume", "instructions": "improve it"})
    yield _tool_end("resume_agent", "resume_modify", "call_abc", "[Resume Tool] stub response")
    yield _text_chunk("resume_agent", "Here is your improved resume.")
    yield _reflection_end(done=True)


async def _stream_retry_then_done(input_state, *, version="v2"):
    """Iteration 1 rejected, iteration 2 approved (buffered agent)."""
    # ── Iteration 1 (rejected) ────────────────────────────────────────────
    yield _agent_start("resume_agent")
    yield _text_chunk("resume_agent", "DRAFT — should be discarded")
    yield _reflection_end(done=False, loop_count=1, critique="回答不够具体")

    # ── Iteration 2 (approved) ────────────────────────────────────────────
    yield _agent_start("resume_agent")
    yield _text_chunk("resume_agent", "FINAL — approved response")
    yield _reflection_end(done=True, loop_count=1)


async def _stream_tool_in_retry(input_state, *, version="v2"):
    """Tool call happens in an intermediate iteration — should appear as THINKING."""
    # ── Iteration 1: tool call, then rejected ─────────────────────────────
    yield _agent_start("research_agent")
    yield _tool_start("research_agent", "web_search", "run1", {"query": "climate change 2024"})
    yield _tool_end("research_agent", "web_search", "run1", "search results...")
    yield _text_chunk("research_agent", "DRAFT")
    yield _reflection_end(done=False, loop_count=1, critique="缺少数据来源")

    # ── Iteration 2: approved ─────────────────────────────────────────────
    yield _agent_start("research_agent")
    yield _text_chunk("research_agent", "FINAL report")
    yield _reflection_end(done=True, loop_count=1)


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_single_pass_text():
    """Single iteration: text is flushed after reflection approves."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_single_pass

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="Hi")]):
            events.append(e)

    texts = [e for e in events if e.event == StreamEventType.TEXT_DELTA]
    assert len(texts) == 2
    assert texts[0].data["text"] == "Hello "
    assert texts[1].data["text"] == "world!"

    assert events[0].event == StreamEventType.AGENT_START
    assert events[-2].event == StreamEventType.AGENT_END
    assert events[-1].event == StreamEventType.DONE


@pytest.mark.asyncio
async def test_tool_call_flushed_on_approval():
    """Tool call events are buffered and flushed with the approved iteration."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_with_tool

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="improve resume")]):
            events.append(e)

    types = [e.event for e in events]
    assert StreamEventType.TOOL_CALL in types
    assert StreamEventType.TOOL_RESULT in types
    assert StreamEventType.AGENT_END in types

    tool_result = next(e for e in events if e.event == StreamEventType.TOOL_RESULT)
    assert "stub response" in tool_result.data["result"]


@pytest.mark.asyncio
async def test_intermediate_text_discarded():
    """Draft text from rejected iterations must not reach the client."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_retry_then_done

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="Hi")]):
            events.append(e)

    texts = [e for e in events if e.event == StreamEventType.TEXT_DELTA]
    assert len(texts) == 1
    assert "FINAL" in texts[0].data["text"]
    assert not any("DRAFT" in t.data["text"] for t in texts)


@pytest.mark.asyncio
async def test_retry_emits_thinking_with_draft_and_critique():
    """When reflection rejects, both the draft preview and the critique appear in THINKING."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_retry_then_done

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="Hi")]):
            events.append(e)

    thinking = [e for e in events if e.event == StreamEventType.THINKING]
    texts = [e.data["text"] for e in thinking]

    # Draft preview must appear in THINKING
    assert any("草稿" in t for t in texts), f"No draft preview found in thinking: {texts}"
    # The rejected draft content must be visible in the thinking panel
    assert any("DRAFT" in t for t in texts), f"Draft text not surfaced: {texts}"
    # Critique must also appear
    assert any("评估" in t for t in texts), f"No critique found in thinking: {texts}"


@pytest.mark.asyncio
async def test_tool_in_retry_shows_thinking():
    """Tool calls during intermediate iterations appear as THINKING (not buffered)."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_tool_in_retry

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="research")]):
            events.append(e)

    thinking = [e for e in events if e.event == StreamEventType.THINKING]
    # At least one THINKING from the tool call in iteration 1
    tool_thinking = [e for e in thinking if "搜索" in e.data["text"] or "climate" in e.data["text"]]
    assert len(tool_thinking) >= 1

    # Final text must only be the approved response
    texts = [e for e in events if e.event == StreamEventType.TEXT_DELTA]
    assert len(texts) == 1
    assert "FINAL" in texts[0].data["text"]


@pytest.mark.asyncio
async def test_approved_after_retry_emits_confirmation():
    """After a retry succeeds, a THINKING confirmation event is emitted."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_retry_then_done

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="Hi")]):
            events.append(e)

    thinking = [e for e in events if e.event == StreamEventType.THINKING]
    confirm = next((e for e in thinking if "✓" in e.data["text"] or "优化已" in e.data["text"] or "已优化" in e.data["text"]), None)
    assert confirm is not None


@pytest.mark.asyncio
async def test_exactly_one_agent_start_end_per_run():
    """Regardless of retry count, only one AGENT_START/END reaches the client."""
    mock_graph = AsyncMock()
    mock_graph.astream_events = _stream_retry_then_done

    with patch("backend.agent.core.get_graph", return_value=mock_graph):
        events = []
        async for e in AgentCore().run([Message(role=Role.USER, content="Hi")]):
            events.append(e)

    assert sum(1 for e in events if e.event == StreamEventType.AGENT_START) == 1
    assert sum(1 for e in events if e.event == StreamEventType.AGENT_END) == 1
