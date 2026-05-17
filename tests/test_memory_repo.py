"""Tests for the memory repository layer."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.agent.schemas import Message, Role
from backend.memory.models import Base
from backend.memory.repo import SQLAlchemyConversationRepo, msg_model_to_schema


@pytest.fixture
async def session():
    """Create an in-memory SQLite database and yield a session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


@pytest.fixture
def repo(session: AsyncSession):
    return SQLAlchemyConversationRepo(session)


@pytest.mark.asyncio
async def test_create_and_get_conversation(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    assert conv.id is not None
    assert conv.title == "New conversation"
    assert conv.message_count == 0

    fetched = await repo.get_conversation(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id


@pytest.mark.asyncio
async def test_list_conversations(repo, session):
    await repo.create_conversation()
    await repo.create_conversation()
    await session.flush()

    convs = await repo.list_conversations()
    assert len(convs) == 2


@pytest.mark.asyncio
async def test_add_message_and_auto_title(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    msg = Message(role=Role.USER, content="Hello, I need help with my resume")
    result = await repo.add_message(conv.id, msg)
    await session.flush()

    assert result is not None
    assert result.idx == 0
    assert result.role == "user"
    assert result.content == "Hello, I need help with my resume"

    # Check auto-title
    updated_conv = await repo.get_conversation(conv.id)
    assert updated_conv.title == "Hello, I need help with my resume"
    assert updated_conv.message_count == 1


@pytest.mark.asyncio
async def test_add_multiple_messages_increments_idx(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    await repo.add_message(conv.id, Message(role=Role.USER, content="msg1"))
    await repo.add_message(conv.id, Message(role=Role.ASSISTANT, content="reply1"))
    await repo.add_message(conv.id, Message(role=Role.USER, content="msg2"))
    await session.flush()

    messages = await repo.get_messages(conv.id)
    assert len(messages) == 3
    assert [m.idx for m in messages] == [0, 1, 2]
    assert [m.role for m in messages] == ["user", "assistant", "user"]


@pytest.mark.asyncio
async def test_get_messages_after_idx(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    for i in range(5):
        await repo.add_message(
            conv.id, Message(role=Role.USER, content=f"msg{i}")
        )
    await session.flush()

    # Get messages after idx 2
    messages = await repo.get_messages(conv.id, after_idx=2)
    assert len(messages) == 2
    assert messages[0].idx == 3
    assert messages[1].idx == 4


@pytest.mark.asyncio
async def test_add_message_with_pin(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    await repo.add_message(
        conv.id,
        Message(role=Role.USER, content="important"),
        is_pinned=True,
    )
    await session.flush()

    messages = await repo.get_messages(conv.id)
    assert messages[0].is_pinned is True


@pytest.mark.asyncio
async def test_update_summary(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    await repo.update_summary(conv.id, "This is a summary", through_idx=5)
    await session.flush()

    updated = await repo.get_conversation(conv.id)
    assert updated.summary == "This is a summary"
    assert updated.summary_through_idx == 5


@pytest.mark.asyncio
async def test_archive_and_unarchive(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    # Archive
    await repo.archive_conversation(conv.id)
    await session.flush()

    # Should not appear in default list
    convs = await repo.list_conversations(include_archived=False)
    assert len(convs) == 0

    # Should appear when including archived
    convs = await repo.list_conversations(include_archived=True)
    assert len(convs) == 1

    # Unarchive
    await repo.unarchive_conversation(conv.id)
    await session.flush()

    convs = await repo.list_conversations(include_archived=False)
    assert len(convs) == 1


@pytest.mark.asyncio
async def test_add_message_to_nonexistent_conversation(repo):
    result = await repo.add_message("nonexistent", Message(role=Role.USER, content="hi"))
    assert result is None


@pytest.mark.asyncio
async def test_msg_model_to_schema(repo, session):
    conv = await repo.create_conversation()
    await session.flush()

    msg = Message(role=Role.USER, content="test content")
    db_msg = await repo.add_message(conv.id, msg, token_count=10)
    await session.flush()

    schema_msg = msg_model_to_schema(db_msg)
    assert schema_msg.role == Role.USER
    assert schema_msg.content == "test content"
