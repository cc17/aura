from __future__ import annotations

from datetime import datetime, timezone

from backend.agent.schemas import Conversation, Message


class MemoryStorage:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    def create_conversation(self) -> Conversation:
        conv = Conversation()
        self._conversations[conv.id] = conv
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> list[Conversation]:
        return sorted(self._conversations.values(), key=lambda c: c.updated_at, reverse=True)

    def add_message(self, conversation_id: str, message: Message) -> None:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return
        conv.messages.append(message)
        conv.updated_at = datetime.now(timezone.utc)

        # Auto-title from first user message
        if conv.title == "New conversation" and message.role == "user" and message.content:
            conv.title = message.content[:50] + ("..." if len(message.content) > 50 else "")


# Singleton
storage = MemoryStorage()
