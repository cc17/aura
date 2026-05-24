"""Repository layer — data access for conversations and messages.

Defines a Protocol for testability and a SQLAlchemy implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.schemas import Message, Role, ToolCall, ToolResult
from backend.memory.models import (
    ConversationModel,
    ConversationSummaryModel,
    MessageModel,
    UserFactModel,
)


# ---------------------------------------------------------------------------
# Protocol (interface)
# ---------------------------------------------------------------------------


class ConversationRepository(Protocol):
    async def create_conversation(self, user_id: int | None = None) -> ConversationModel: ...
    async def get_conversation(self, conversation_id: str) -> ConversationModel | None: ...
    async def list_conversations(
        self,
        include_archived: bool = False,
        user_id: int | None = None,
        since: datetime | None = None,
    ) -> Sequence[ConversationModel]: ...
    async def add_message(
        self,
        conversation_id: str,
        message: Message,
        *,
        token_count: int | None = None,
        is_pinned: bool = False,
    ) -> MessageModel | None: ...
    async def get_messages(
        self,
        conversation_id: str,
        after_idx: int | None = None,
    ) -> Sequence[MessageModel]: ...
    async def update_summary(
        self,
        conversation_id: str,
        summary_text: str,
        through_idx: int,
    ) -> None: ...
    async def archive_conversation(self, conversation_id: str) -> None: ...
    async def unarchive_conversation(self, conversation_id: str) -> None: ...


# ---------------------------------------------------------------------------
# SQLAlchemy implementation
# ---------------------------------------------------------------------------


class SQLAlchemyConversationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(self, user_id: int | None = None) -> ConversationModel:
        conv = ConversationModel(user_id=user_id)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def get_conversation(self, conversation_id: str) -> ConversationModel | None:
        return await self._session.get(ConversationModel, conversation_id)

    async def list_conversations(
        self,
        include_archived: bool = False,
        user_id: int | None = None,
        since: datetime | None = None,
    ) -> Sequence[ConversationModel]:
        stmt = select(ConversationModel).order_by(ConversationModel.updated_at.desc())
        if not include_archived:
            stmt = stmt.where(ConversationModel.archived_at.is_(None))
        if user_id is not None:
            stmt = stmt.where(ConversationModel.user_id == user_id)
        if since is not None:
            stmt = stmt.where(ConversationModel.created_at >= since)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def add_message(
        self,
        conversation_id: str,
        message: Message,
        *,
        token_count: int | None = None,
        is_pinned: bool = False,
    ) -> MessageModel | None:
        conv = await self.get_conversation(conversation_id)
        if conv is None:
            return None

        idx = conv.message_count

        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = [tc.model_dump() for tc in message.tool_calls]

        tool_result_json = None
        if message.tool_result:
            tool_result_json = message.tool_result.model_dump()

        msg = MessageModel(
            conversation_id=conversation_id,
            idx=idx,
            role=message.role.value,
            content=message.content,
            tool_calls=tool_calls_json,
            tool_result=tool_result_json,
            token_count=token_count,
            is_pinned=is_pinned,
        )
        self._session.add(msg)

        conv.message_count = idx + 1
        conv.updated_at = datetime.now(timezone.utc)

        # Auto-title from first user message
        if conv.title == "New conversation" and message.role == Role.USER and message.content:
            conv.title = message.content[:50] + ("..." if len(message.content) > 50 else "")

        await self._session.flush()
        return msg

    async def get_messages(
        self,
        conversation_id: str,
        after_idx: int | None = None,
    ) -> Sequence[MessageModel]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.idx)
        )
        if after_idx is not None:
            stmt = stmt.where(MessageModel.idx > after_idx)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_summary(
        self,
        conversation_id: str,
        summary_text: str,
        through_idx: int,
    ) -> None:
        conv = await self.get_conversation(conversation_id)
        if conv is None:
            return
        conv.summary = summary_text
        conv.summary_through_idx = through_idx

        # Audit log
        audit = ConversationSummaryModel(
            conversation_id=conversation_id,
            summary_text=summary_text,
            covers_through_idx=through_idx,
        )
        self._session.add(audit)
        await self._session.flush()

    async def archive_conversation(self, conversation_id: str) -> None:
        conv = await self.get_conversation(conversation_id)
        if conv:
            conv.archived_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def unarchive_conversation(self, conversation_id: str) -> None:
        conv = await self.get_conversation(conversation_id)
        if conv:
            conv.archived_at = None
            await self._session.flush()

    async def set_pending_agent(self, conversation_id: str, agent: str) -> None:
        conv = await self.get_conversation(conversation_id)
        if conv:
            conv.pending_agent = agent
            await self._session.flush()

    # --- User Facts (cross-conversation) ---

    async def get_all_facts(self) -> Sequence[UserFactModel]:
        stmt = select(UserFactModel).order_by(UserFactModel.category, UserFactModel.created_at)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def replace_all_facts(
        self,
        facts: list[dict],
        source_conversation_id: str | None = None,
    ) -> None:
        """Replace all user facts with a new set.

        Each dict should have 'category' and 'content' keys.
        This is a full replace — the LLM extraction prompt sees existing facts
        and outputs the merged result.
        """
        # Delete existing
        existing = await self.get_all_facts()
        for f in existing:
            await self._session.delete(f)

        # Insert new
        for item in facts:
            fact = UserFactModel(
                category=item.get("category", "general"),
                content=item["content"],
                source_conversation_id=source_conversation_id,
            )
            self._session.add(fact)
        await self._session.flush()

    async def delete_fact(self, fact_id: str) -> bool:
        fact = await self._session.get(UserFactModel, fact_id)
        if fact:
            await self._session.delete(fact)
            await self._session.flush()
            return True
        return False


def msg_model_to_schema(m: MessageModel) -> Message:
    """Convert a DB MessageModel back to an agent schema Message."""
    tool_calls = None
    if m.tool_calls:
        tool_calls = [ToolCall(**tc) for tc in m.tool_calls]

    tool_result = None
    if m.tool_result:
        tool_result = ToolResult(**m.tool_result)

    return Message(
        role=Role(m.role),
        content=m.content,
        tool_calls=tool_calls,
        tool_result=tool_result,
        timestamp=m.created_at,
    )
