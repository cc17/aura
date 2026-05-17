"""Extract user facts from conversation for cross-conversation memory.

Called after each assistant response to update the global user profile.
"""

from __future__ import annotations

import json
import logging

from backend.agent.schemas import Message
from backend.llm.langchain_bridge import create_chat_model

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """\
You are a fact extraction system. Analyze the conversation below and maintain a list of facts about the USER.

RULES:
- Only extract facts about the user themselves (identity, preferences, decisions, scores, goals)
- Ignore assistant responses, chitchat, and questions
- Each fact should be one concise sentence
- Categorize each fact into one of: demographic, education, career, preferences, relationships, plans
- If the conversation contradicts an existing fact, update it (keep the newer version)
- If no new facts are found, return the existing facts unchanged
- Write facts in the same language the user uses
- Output valid JSON only

EXISTING FACTS:
{existing_facts}

CONVERSATION:
{conversation}

Output a JSON array of objects, each with "category" and "content" keys. Example:
[
  {{"category": "demographic", "content": "来自山东省"}},
  {{"category": "education", "content": "2025年高考理科580分"}}
]

JSON OUTPUT:"""


def _format_existing_facts(facts: list[dict]) -> str:
    if not facts:
        return "(none)"
    lines = []
    for f in facts:
        lines.append(f"- [{f['category']}] {f['content']}")
    return "\n".join(lines)


def _format_conversation(messages: list[Message]) -> str:
    lines = []
    for msg in messages:
        role = msg.role.value.upper()
        content = msg.content or "(no content)"
        # Truncate very long messages to save tokens
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


async def extract_facts(
    messages: list[Message],
    existing_facts: list[dict],
) -> list[dict] | None:
    """Call LLM to extract/update user facts from conversation.

    Returns list of {"category": ..., "content": ...} dicts, or None on failure.
    """
    if not messages:
        return None

    prompt = _EXTRACT_PROMPT.format(
        existing_facts=_format_existing_facts(existing_facts),
        conversation=_format_conversation(messages),
    )

    try:
        llm = create_chat_model()
        from langchain_core.messages import HumanMessage

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = response.content.strip() if response.content else ""

        # Clean up markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        facts = json.loads(text)
        if not isinstance(facts, list):
            logger.warning("Fact extraction returned non-list: %s", type(facts))
            return None

        # Validate structure
        valid = []
        for item in facts:
            if isinstance(item, dict) and "content" in item:
                valid.append({
                    "category": item.get("category", "general"),
                    "content": item["content"],
                })
        return valid if valid else None

    except (json.JSONDecodeError, Exception):
        logger.exception("Fact extraction failed")
        return None
