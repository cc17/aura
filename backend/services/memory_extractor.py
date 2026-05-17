"""Extract user memories from conversation turns and persist to user_memories table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.langchain_bridge import create_chat_model
from backend.memory.models import UserMemoryModel
from backend.services.embedder import embed_text

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """\
从下面的对话中，提取出值得长期记住的事实。

【用户】{user_input}
【助手】{answer}

【提取规则】
1. 只提取关于用户本人的具体事实，不提取一般性知识
2. 每条事实独立成句，简洁
3. 标注类别：
   - fact: 客观事实（用户的老板叫张总）
   - preference: 偏好（用户喜欢简洁回答）
   - goal: 短期目标（用户下周要做项目复盘）
   - context: 工作背景（用户的团队用 Jira）
4. 标注重要性 1-10：
   - 9-10: 长期身份信息（行业/岗位）
   - 7-8: 重要关系/项目
   - 4-6: 偏好/习惯
   - 1-3: 临时信息
5. 没有值得记的就返回空数组

【输出格式】严格的 JSON 数组，不要任何其他文字：
[{{"content": "...", "category": "...", "importance": N}}]
"""


async def extract_and_save_memories(
    user_id: int,
    user_input: str,
    answer: str,
    session: AsyncSession,
) -> None:
    """Extract facts from one conversation turn and write to user_memories.

    Called asynchronously after the main chat response; failures are logged
    but never propagate to the user.
    """
    if not user_input.strip() or not answer.strip():
        return

    prompt = _EXTRACT_PROMPT.format(
        user_input=user_input[:2000],
        answer=answer[:2000],
    )

    try:
        llm = create_chat_model()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        facts = json.loads(raw)
        if not isinstance(facts, list):
            return

        now = datetime.now(timezone.utc)
        for item in facts:
            content = item.get("content", "").strip()
            category = item.get("category", "fact")
            importance = int(item.get("importance", 5))
            if not content:
                continue

            vec = await embed_text(content)
            memory = UserMemoryModel(
                user_id=user_id,
                content=content,
                category=category,
                importance=importance,
                embedding=vec,
                created_at=now,
                last_accessed_at=now,
                access_count=0,
            )
            session.add(memory)

        await session.flush()
        logger.info("Saved %d memories for user %d", len(facts), user_id)

    except (json.JSONDecodeError, ValueError):
        logger.debug("No extractable memories from this turn (non-fatal)")
    except Exception:
        logger.exception("Memory extraction failed (non-fatal)")
