"""LLM-based conversation summarization.

Compresses older messages into a concise summary, preserving key facts.
"""

from __future__ import annotations

import logging

from backend.agent.schemas import Message
from backend.llm.langchain_bridge import create_chat_model

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """\
You are a conversation summarizer. Compress the following conversation into a concise summary.

RULES:
- Preserve all key facts: user information, scores, uploaded files, decisions, action items
- Keep entity names, dates, and specific numbers
- Write in the same language the conversation uses
- Target ~800 tokens or less
- Use bullet points for clarity
- If there is an existing summary, merge it with the new messages

{existing_section}

CONVERSATION TO SUMMARIZE:
{conversation}

SUMMARY:"""


async def summarize_messages(
    messages: list[Message],
    existing_summary: str | None = None,
) -> str | None:
    """Call LLM to summarize a list of messages.

    Returns the summary text, or None if summarization fails.
    """
    if not messages:
        return None

    # Format messages
    lines = []
    for msg in messages:
        role = msg.role.value.upper()
        content = msg.content or "(no content)"
        lines.append(f"[{role}]: {content}")
    conversation_text = "\n".join(lines)

    existing_section = ""
    if existing_summary:
        existing_section = f"EXISTING SUMMARY (merge with new information):\n{existing_summary}\n"

    prompt = _SUMMARIZE_PROMPT.format(
        existing_section=existing_section,
        conversation=conversation_text,
    )

    try:
        llm = create_chat_model()
        from langchain_core.messages import HumanMessage

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip() if response.content else None
    except Exception:
        logger.exception("Summarization LLM call failed")
        return None
