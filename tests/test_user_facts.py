"""Tests for cross-conversation user facts (repo + manager + build_context)."""

import json
from unittest.mock import AsyncMock, patch

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


# --- Repo tests ---


@pytest.mark.asyncio
async def test_get_all_facts_empty(repo):
    facts = await repo.get_all_facts()
    assert facts == []


@pytest.mark.asyncio
async def test_replace_all_facts(repo, session):
    await repo.replace_all_facts([
        {"category": "demographic", "content": "来自山东省"},
        {"category": "education", "content": "2025年高考580分"},
    ])
    await session.flush()

    facts = await repo.get_all_facts()
    assert len(facts) == 2
    assert facts[0].content == "来自山东省"
    assert facts[1].content == "2025年高考580分"


@pytest.mark.asyncio
async def test_replace_all_facts_overwrites(repo, session):
    # Initial facts
    await repo.replace_all_facts([
        {"category": "demographic", "content": "来自山东省"},
    ])
    await session.flush()

    # Replace with new set
    await repo.replace_all_facts([
        {"category": "demographic", "content": "来自北京市"},
        {"category": "career", "content": "目标岗位前端开发"},
    ])
    await session.flush()

    facts = await repo.get_all_facts()
    assert len(facts) == 2
    contents = [f.content for f in facts]
    assert "来自北京市" in contents
    assert "来自山东省" not in contents


@pytest.mark.asyncio
async def test_delete_fact(repo, session):
    await repo.replace_all_facts([
        {"category": "demographic", "content": "test fact"},
    ])
    await session.flush()

    facts = await repo.get_all_facts()
    assert len(facts) == 1

    deleted = await repo.delete_fact(facts[0].id)
    assert deleted is True

    facts = await repo.get_all_facts()
    assert len(facts) == 0


@pytest.mark.asyncio
async def test_delete_fact_nonexistent(repo):
    deleted = await repo.delete_fact("nonexistent")
    assert deleted is False


# --- build_context with facts ---


@pytest.mark.asyncio
async def test_build_context_includes_user_facts(manager, repo, session):
    # Add some facts
    await repo.replace_all_facts([
        {"category": "demographic", "content": "来自山东省"},
        {"category": "education", "content": "高考580分"},
    ])
    await session.flush()

    # Create conversation with a message
    conv = await repo.create_conversation()
    await session.flush()
    await repo.add_message(conv.id, Message(role=Role.USER, content="帮我选学校"), token_count=10)
    await session.flush()

    ctx = await manager.build_context(conv.id)

    # First message should be the user facts system message
    assert ctx[0].role == Role.SYSTEM
    assert "来自山东省" in ctx[0].content
    assert "高考580分" in ctx[0].content
    assert "User profile" in ctx[0].content

    # User message should still be there
    assert ctx[-1].content == "帮我选学校"


@pytest.mark.asyncio
async def test_build_context_no_facts_no_system_msg(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()
    await repo.add_message(conv.id, Message(role=Role.USER, content="hi"), token_count=5)
    await session.flush()

    ctx = await manager.build_context(conv.id)
    # No system message for facts since there are none
    assert all(m.role != Role.SYSTEM for m in ctx)


# --- extract_and_save_facts ---


@pytest.mark.asyncio
async def test_extract_and_save_facts(manager, repo, session):
    conv = await repo.create_conversation()
    await session.flush()
    await repo.add_message(
        conv.id, Message(role=Role.USER, content="我是山东考生，今年高考580分")
    )
    await repo.add_message(
        conv.id, Message(role=Role.ASSISTANT, content="好的，580分在山东排名大约...")
    )
    await session.flush()

    fake_response = json.dumps([
        {"category": "demographic", "content": "山东考生"},
        {"category": "education", "content": "2025年高考580分"},
    ])

    # Mock the LLM call
    mock_llm = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = fake_response
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("backend.memory.fact_extractor.create_chat_model", return_value=mock_llm):
        await manager.extract_and_save_facts(conv.id)
        await session.flush()

    facts = await repo.get_all_facts()
    assert len(facts) == 2
    contents = [f.content for f in facts]
    assert "山东考生" in contents
    assert "2025年高考580分" in contents


@pytest.mark.asyncio
async def test_extract_facts_nonexistent_conversation(manager):
    # Should not raise
    await manager.extract_and_save_facts("nonexistent")
