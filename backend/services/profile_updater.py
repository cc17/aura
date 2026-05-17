"""Async profile updater — infers profile field updates from a conversation turn."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.langchain_bridge import create_chat_model
from backend.memory.models import UserModel
from backend.services.profile_service import update_profile

logger = logging.getLogger(__name__)

_UPDATE_PROMPT = """\
基于用户的提问，推断或更新用户画像。

【当前画像】
{current_profile_json}

【用户刚刚问】
{user_input}

【更新规则】
1. 只更新有新信号的字段，其他字段保持不变
2. 每个字段带 confidence(0-1)，累积式更新：
   - 首次推断：confidence=0.4
   - 再次确认：在原值上 +0.2，封顶 1.0
   - 矛盾信息：confidence 降到 0.3
3. 不确定就别更新
4. 可推断的字段：industry / role / pain_points / ai_proficiency / style_preference

【输出】更新后的完整 profile JSON，严格 JSON 格式。
如果没有需要更新的内容，返回空对象 {{}}
"""


async def maybe_update_profile(
    user_id: int,
    user_input: str,
    session: AsyncSession,
) -> None:
    """Infer profile updates from user_input and persist them.

    Called asynchronously post-response; failures are logged but never propagate.
    """
    if not user_input.strip():
        return

    try:
        user = await session.get(UserModel, user_id)
        if user is None:
            return

        current_profile = user.profile or {}
        prompt = _UPDATE_PROMPT.format(
            current_profile_json=json.dumps(current_profile, ensure_ascii=False),
            user_input=user_input[:1000],
        )

        llm = create_chat_model()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        updates = json.loads(raw)
        if not isinstance(updates, dict) or not updates:
            return

        # Filter out fields that didn't actually change meaningfully
        meaningful = {}
        for k, v in updates.items():
            existing = current_profile.get(k)
            if v != existing:
                meaningful[k] = v

        if meaningful:
            await update_profile(session, user_id, meaningful, confidence=0.4)
            await session.flush()
            logger.info("Profile updated for user %d: %s", user_id, list(meaningful.keys()))

    except (json.JSONDecodeError, ValueError):
        logger.debug("No profile updates from this turn (non-fatal)")
    except Exception:
        logger.exception("Profile updater failed (non-fatal)")
