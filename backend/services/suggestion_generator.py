"""Async suggestion generator — produces 3 contextual next-step suggestions."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.langchain_bridge import create_chat_model
from backend.memory.models import UserModel, UserSuggestionModel
from backend.services.profile_service import get_profile
from backend.services.skill_registry import list_skills

logger = logging.getLogger(__name__)

_SUGGEST_PROMPT = """\
你是用户的工作搭子，刚回答完一个问题。
基于用户的身份和这轮对话，生成 3 条用户可能下一步想做的事。

【用户画像】
- 行业：{industry}
- 岗位：{role}
- 痛点：{pain_points}

【这轮对话】
问：{user_input}
答：{answer_summary}

【可用的 Skills】
{available_skills_list}

【输出要求】
3 条建议，满足：
- 至少 1 条 type="question"（继续问的问题）
- 至少 1 条 type="skill"（用某个 Skill 干活）
- 三条要有梯度：深入 / 横向扩展 / 引申到工作流层面
- 用用户的口吻表达，不要"还想了解什么"这种废话

【输出格式】严格 JSON 数组，不要任何其他文字：
[
  {{"type": "question", "text": "...", "skill_key": null}},
  {{"type": "skill", "text": "...", "skill_key": "weekly_report"}}
]
"""


async def generate_and_save_suggestions(
    user_id: int,
    message_id: str,
    user_input: str,
    answer: str,
    session: AsyncSession,
) -> None:
    """Generate suggestions and persist to user_suggestions table.

    Called asynchronously post-response; failures are logged but never propagate.
    """
    if not user_input.strip() or not answer.strip():
        return

    try:
        user = await session.get(UserModel, user_id)
        profile = user.profile or {} if user else {}

        def _field(key: str) -> str:
            v = profile.get(key)
            return v.get("value", "") if isinstance(v, dict) else str(v or "")

        industry = _field("industry")
        role = _field("role")
        pain_points_raw = profile.get("pain_points", [])
        pain_points = "、".join(pain_points_raw) if isinstance(pain_points_raw, list) else str(pain_points_raw or "")

        skills = list_skills(industry=industry or None, role=role or None)
        if not skills:
            skills = list_skills()
        skills_list = "\n".join(
            f"- {s['skill_key']}: {s['scenario_name']} — {s['description']}" for s in skills[:6]
        )

        prompt = _SUGGEST_PROMPT.format(
            industry=industry or "未知",
            role=role or "未知",
            pain_points=pain_points or "未知",
            user_input=user_input[:500],
            answer_summary=answer[:800],
            available_skills_list=skills_list or "暂无",
        )

        llm = create_chat_model()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            return

        # Keep only valid items
        clean = [
            s for s in suggestions
            if isinstance(s, dict) and s.get("type") in ("question", "skill") and s.get("text")
        ][:3]

        if not clean:
            return

        record = UserSuggestionModel(
            user_id=user_id,
            message_id=message_id,
            suggestions=clean,
        )
        session.add(record)
        await session.flush()
        logger.info("Suggestions saved for user %d, message %s", user_id, message_id)

    except (json.JSONDecodeError, ValueError):
        logger.debug("Suggestion generation produced no valid JSON (non-fatal)")
    except Exception:
        logger.exception("Suggestion generator failed (non-fatal)")
