"""Tests for MemoryManager (build_context + sliding window)."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.agent.schemas import Message, Role
from backend.memory.manager import MemoryManager
from backend.memory.models import Base
from backend.memory.repo import SQLAlchemyConversationRepo


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture
def repo(session):
    return SQLAlchemyConversationRepo(session)


@pytest.fixture
def manager(repo):
    return MemoryManager(repo)


@pytest.mark.asyncio
async def test_build_context_empty_conversation(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    ctx = await manager.build_context(conv.id)
    assert ctx == []


@pytest.mark.asyncio
async def test_build_context_includes_all_messages_under_budget(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    for i in range(5):
        await repo.add_message(
            conv.id, Message(role=Role.USER, content=f"message {i}"), token_count=10
        )
    await session.flush()

    ctx = await manager.build_context(conv.id)
    assert len(ctx) == 5
    assert ctx[0].content == "message 0"
    assert ctx[-1].content == "message 4"


@pytest.mark.asyncio
async def test_build_context_with_summary(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    # Add 10 messages
    for i in range(10):
        await repo.add_message(
            conv.id, Message(role=Role.USER, content=f"msg {i}"), token_count=10
        )
    await session.flush()

    # Summarize first 5
    await repo.update_summary(conv.id, "Summary of messages 0-4", through_idx=4)
    await session.flush()

    ctx = await manager.build_context(conv.id)
    # Should have: 1 summary system msg + 5 remaining messages (idx 5-9)
    assert len(ctx) == 6
    assert ctx[0].role == Role.SYSTEM
    assert "Summary" in ctx[0].content
    assert ctx[1].content == "msg 5"


@pytest.mark.asyncio
async def test_build_context_pinned_always_included(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    # First message pinned
    await repo.add_message(
        conv.id,
        Message(role=Role.USER, content="pinned first"),
        token_count=10,
        is_pinned=True,
    )
    # Add many more
    for i in range(20):
        await repo.add_message(
            conv.id, Message(role=Role.USER, content=f"msg {i}"), token_count=10
        )
    await session.flush()

    ctx = await manager.build_context(conv.id)
    contents = [m.content for m in ctx]
    assert "pinned first" in contents


@pytest.mark.asyncio
async def test_build_context_nonexistent_conversation(manager):
    ctx = await manager.build_context("doesnotexist")
    assert ctx == []


@pytest.mark.asyncio
async def test_build_context_respects_min_recent(manager, repo, session, monkeypatch):
    """Even with tiny budget, at least 4 recent messages are included."""
    monkeypatch.setattr("backend.memory.manager.settings.context_max_tokens", 1)

    conv = await repo.create_conversation()
    await session.flush()

    for i in range(10):
        await repo.add_message(
            conv.id, Message(role=Role.USER, content=f"msg {i}"), token_count=100
        )
    await session.flush()

    ctx = await manager.build_context(conv.id)
    # At least 4 messages (the minimum recent)
    assert len(ctx) >= 4
