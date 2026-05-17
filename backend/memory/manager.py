"""MemoryManager — builds LLM context with sliding window and triggers summarization.

Responsibilities:
- build_context(): assemble messages within token budget
- save_message(): persist with token count
- maybe_summarize(): check threshold and compress if needed
"""

from __future__ import annotations

import logging
from typing import Sequence

from backend.agent.schemas import Message, Role
from backend.config import settings
from backend.memory.models import ConversationModel, MessageModel
from backend.memory.repo import SQLAlchemyConversationRepo, msg_model_to_schema
from backend.memory.token_counter import count_message_tokens

logger = logging.getLogger(__name__)

# Minimum messages to always include in context (even if over budget)
_MIN_RECENT_MESSAGES = 4


class MemoryManager:
    def __init__(self, repo: SQLAlchemyConversationRepo) -> None:
        self._repo = repo

    async def build_context(
        self, conversation_id: str, user_id: int | None = None
    ) -> list[Message]:
        """Build message list for LLM within token budget.

        Algorithm:
        1. If user has a profile, inject as system message (persona context)
        2. If summary exists, prepend as system message
        3. Load messages after summary_through_idx
        4. Force-include pinned messages
        5. Fill from newest to oldest within token budget
        6. Always include at least _MIN_RECENT_MESSAGES
        """
        conv = await self._repo.get_conversation(conversation_id)
        if conv is None:
            return []

        budget = settings.context_max_tokens
        result_messages: list[Message] = []
        used_tokens = 0

        # 0a. User profile + long-term memories as persona system prompt (Phase 2/4)
        if user_id is not None:
            from backend.services.prompt_builder import build_system_prompt
            from backend.services.memory_service import retrieve_memories
            from backend.memory.database import get_session_factory

            async with get_session_factory()() as profile_session:
                from backend.memory.models import UserModel
                user = await profile_session.get(UserModel, user_id)
                profile = user.profile if user else None

            # Retrieve memories using the latest user message as query
            memories: list[str] = []
            try:
                all_msgs = await self._repo.get_messages(conversation_id)
                query = ""
                for m in reversed(all_msgs):
                    if m.role == "user":
                        query = m.content[:500]
                        break
                if query:
                    async with get_session_factory()() as mem_session:
                        memories = await retrieve_memories(user_id, query, mem_session, top_k=5)
            except Exception:
                logger.warning("Memory retrieval failed (non-fatal)", exc_info=True)

            persona_prompt = build_system_prompt(profile, memories=memories or None)
            if persona_prompt:
                persona_msg = Message(role=Role.SYSTEM, content=persona_prompt)
                persona_tokens = count_message_tokens("system", persona_prompt)
                result_messages.append(persona_msg)
                used_tokens += persona_tokens

        # 0b. User facts (cross-conversation, legacy) as system message
        facts = await self._repo.get_all_facts()
        if facts:
            facts_text = "\n".join(f"- {f.content}" for f in facts)
            facts_msg = Message(
                role=Role.SYSTEM,
                content=f"[User profile — remembered across conversations]\n{facts_text}",
            )
            facts_tokens = count_message_tokens("system", facts_msg.content)
            result_messages.append(facts_msg)
            used_tokens += facts_tokens

        # 1. Summary as system message
        if conv.summary:
            summary_msg = Message(
                role=Role.SYSTEM,
                content=f"[Previous conversation summary]\n{conv.summary}",
            )
            summary_tokens = count_message_tokens("system", summary_msg.content)
            result_messages.append(summary_msg)
            used_tokens += summary_tokens

        # 2. Load messages after summary
        after_idx = conv.summary_through_idx if conv.summary_through_idx is not None else None
        db_messages = await self._repo.get_messages(conversation_id, after_idx=after_idx)

        if not db_messages:
            return result_messages

        # 3. Identify pinned messages and compute their cost
        pinned_indices: set[int] = set()
        for i, m in enumerate(db_messages):
            if m.is_pinned:
                pinned_indices.add(i)
                tokens = m.token_count or count_message_tokens(m.role, m.content)
                used_tokens += tokens

        # 4. Fill from newest to oldest
        selected_indices: set[int] = set(pinned_indices)
        remaining = len(db_messages)

        # Always include at least the most recent _MIN_RECENT_MESSAGES
        min_start = max(0, remaining - _MIN_RECENT_MESSAGES)
        for i in range(remaining - 1, min_start - 1, -1):
            selected_indices.add(i)
            if i not in pinned_indices:
                tokens = db_messages[i].token_count or count_message_tokens(
                    db_messages[i].role, db_messages[i].content
                )
                used_tokens += tokens

        # Continue backwards adding more if within budget
        for i in range(min_start - 1, -1, -1):
            if i in pinned_indices:
                continue  # already counted
            tokens = db_messages[i].token_count or count_message_tokens(
                db_messages[i].role, db_messages[i].content
            )
            if used_tokens + tokens > budget:
                break
            selected_indices.add(i)
            used_tokens += tokens

        # 5. Assemble in order
        for i in sorted(selected_indices):
            result_messages.append(msg_model_to_schema(db_messages[i]))

        logger.info(
            "Context built: %d/%d messages, ~%d tokens (budget %d)",
            len(selected_indices),
            len(db_messages),
            used_tokens,
            budget,
        )
        return result_messages

    async def maybe_summarize(self, conversation_id: str) -> None:
        """Check if summarization is needed and trigger it."""
        conv = await self._repo.get_conversation(conversation_id)
        if conv is None:
            return

        # Count unsummarized messages
        after_idx = conv.summary_through_idx
        unsummarized = await self._repo.get_messages(conversation_id, after_idx=after_idx)

        if len(unsummarized) < settings.summarize_threshold:
            return

        logger.info(
            "Triggering summarization for conv %s (%d unsummarized messages)",
            conversation_id,
            len(unsummarized),
        )

        from backend.memory.summarizer import summarize_messages

        # Determine which messages to summarize (all except the most recent few)
        keep_recent = _MIN_RECENT_MESSAGES
        to_summarize = unsummarized[:-keep_recent] if len(unsummarized) > keep_recent else []
        if not to_summarize:
            return

        messages_for_llm = [msg_model_to_schema(m) for m in to_summarize]
        existing_summary = conv.summary

        new_summary = await summarize_messages(messages_for_llm, existing_summary)
        if new_summary:
            through_idx = to_summarize[-1].idx
            await self._repo.update_summary(conversation_id, new_summary, through_idx)
            logger.info("Summary updated through idx %d", through_idx)

    async def extract_and_save_facts(self, conversation_id: str) -> None:
        """Extract user facts from recent messages and update the global fact store."""
        conv = await self._repo.get_conversation(conversation_id)
        if conv is None:
            return

        # Load recent messages (last 10 — enough context for extraction)
        all_msgs = await self._repo.get_messages(conversation_id)
        recent = list(all_msgs[-10:]) if len(all_msgs) > 10 else list(all_msgs)
        if not recent:
            return

        # Get existing facts
        existing_db = await self._repo.get_all_facts()
        existing = [{"category": f.category, "content": f.content} for f in existing_db]

        from backend.memory.fact_extractor import extract_facts

        schema_msgs = [msg_model_to_schema(m) for m in recent]
        new_facts = await extract_facts(schema_msgs, existing)

        if new_facts is not None:
            await self._repo.replace_all_facts(new_facts, source_conversation_id=conversation_id)
            logger.info(
                "User facts updated: %d facts (from conv %s)", len(new_facts), conversation_id
            )
