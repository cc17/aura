"""Skills API — list, market, my library, execute."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.schemas import Message, Role
from backend.core.auth import get_current_user, get_db
from backend.memory.database import get_session_factory
from backend.memory.models import UserModel, UserSkillModel
from backend.memory.repo import SQLAlchemyConversationRepo
from backend.services.quota_service import check_and_increment
from backend.services.skill_executor import execute_skill_stream
from backend.services.skill_registry import (
    all_skills,
    get_skill,
    get_skill_by_id,
    list_skills,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills")

_MAX_CHATBOX = 6
_MAX_PINS = 4


def _val(profile: dict, field: str) -> str:
    f = profile.get(field)
    return f.get("value", "") if isinstance(f, dict) else (f or "")


# ---------------------------------------------------------------------------
# GET /api/skills  — Chatbox cards (pin + recommendations, up to 6)
# ---------------------------------------------------------------------------


@router.get("")
async def get_skills(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    profile = current_user.profile or {}
    industry = _val(profile, "industry")
    role = _val(profile, "role")

    # Pinned skills (ordered by added_at so pin order is stable)
    pinned_rows = (
        await session.execute(
            select(UserSkillModel)
            .where(
                UserSkillModel.user_id == current_user.id,
                UserSkillModel.is_pinned == True,  # noqa: E712
            )
            .order_by(UserSkillModel.added_at)
        )
    ).scalars().all()

    pinned_ids = {row.skill_id for row in pinned_rows}
    pinned_skills = [s for row in pinned_rows if (s := get_skill_by_id(row.skill_id))]

    # Fill remaining slots with profile-matched recommendations
    slots_left = max(0, _MAX_CHATBOX - len(pinned_skills))
    if slots_left > 0:
        recommended = list_skills(industry=industry or None, role=role or None)
        if not recommended:
            recommended = list_skills()
        fill = [s for s in recommended if s["id"] not in pinned_ids][:slots_left]
    else:
        fill = []

    return {"skills": pinned_skills + fill}


# ---------------------------------------------------------------------------
# GET /api/skills/market  — All skills with is_added flag
# ---------------------------------------------------------------------------


@router.get("/market")
async def get_market_skills(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    added_ids = set(
        (
            await session.execute(
                select(UserSkillModel.skill_id).where(
                    UserSkillModel.user_id == current_user.id
                )
            )
        ).scalars().all()
    )

    return {
        "skills": [
            {**s, "is_added": s["id"] in added_ids}
            for s in all_skills()
        ]
    }


# ---------------------------------------------------------------------------
# GET /api/skills/my  — User's library (added skills)
# ---------------------------------------------------------------------------


@router.get("/my")
async def get_my_skills(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    rows = (
        await session.execute(
            select(UserSkillModel)
            .where(UserSkillModel.user_id == current_user.id)
            .order_by(UserSkillModel.is_pinned.desc(), UserSkillModel.added_at)
        )
    ).scalars().all()

    skills = []
    for row in rows:
        s = get_skill_by_id(row.skill_id)
        if s:
            skills.append({**s, "is_pinned": row.is_pinned, "use_count": row.use_count})

    return {"skills": skills}


# ---------------------------------------------------------------------------
# POST /api/skills/{key}/add
# ---------------------------------------------------------------------------


@router.post("/{skill_key}/add", status_code=201)
async def add_skill(
    skill_key: str,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    skill = get_skill(skill_key)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_key}' not found")

    existing = await session.scalar(
        select(UserSkillModel).where(
            UserSkillModel.user_id == current_user.id,
            UserSkillModel.skill_id == skill["id"],
        )
    )
    if existing:
        return {"ok": True, "already_added": True}

    session.add(UserSkillModel(user_id=current_user.id, skill_id=skill["id"]))
    await session.commit()
    return {"ok": True, "already_added": False}


# ---------------------------------------------------------------------------
# DELETE /api/skills/{key}/remove
# ---------------------------------------------------------------------------


@router.delete("/{skill_key}/remove")
async def remove_skill(
    skill_key: str,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    skill = get_skill(skill_key)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_key}' not found")

    row = await session.scalar(
        select(UserSkillModel).where(
            UserSkillModel.user_id == current_user.id,
            UserSkillModel.skill_id == skill["id"],
        )
    )
    if row:
        await session.delete(row)
        await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# PATCH /api/skills/{key}/pin
# ---------------------------------------------------------------------------


class PinRequest(BaseModel):
    pinned: bool


@router.patch("/{skill_key}/pin")
async def pin_skill(
    skill_key: str,
    body: PinRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    skill = get_skill(skill_key)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_key}' not found")

    row = await session.scalar(
        select(UserSkillModel).where(
            UserSkillModel.user_id == current_user.id,
            UserSkillModel.skill_id == skill["id"],
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="请先将技能添加到我的技能库")

    if body.pinned:
        other_pin_count = await session.scalar(
            select(func.count()).select_from(UserSkillModel).where(
                UserSkillModel.user_id == current_user.id,
                UserSkillModel.is_pinned == True,  # noqa: E712
                UserSkillModel.skill_id != skill["id"],
            )
        )
        if other_pin_count >= _MAX_PINS:
            raise HTTPException(status_code=400, detail=f"最多固定 {_MAX_PINS} 个技能")

    row.is_pinned = body.pinned
    await session.commit()
    return {"ok": True, "is_pinned": row.is_pinned}


# ---------------------------------------------------------------------------
# POST /api/skills/{key}/execute  — SSE stream
# ---------------------------------------------------------------------------


class ExecuteRequest(BaseModel):
    input_data: dict
    conversation_id: str | None = None
    user_message: str | None = None


@router.post("/{skill_key}/execute")
async def execute_skill(
    skill_key: str,
    body: ExecuteRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    skill = get_skill(skill_key)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_key}' not found")

    session_factory = get_session_factory()
    user_id = current_user.id
    profile = current_user.profile or {}

    async with session_factory() as quota_session:
        await check_and_increment(user_id, quota_session)
        await quota_session.commit()

    async with session_factory() as conv_session:
        repo = SQLAlchemyConversationRepo(conv_session)
        conv = None
        if body.conversation_id:
            conv = await repo.get_conversation(body.conversation_id)
            if conv and conv.user_id is not None and conv.user_id != user_id:
                conv = None  # reject cross-user injection
        if not conv:
            conv = await repo.create_conversation(user_id=user_id)
            await conv_session.commit()
        conv_id = conv.id

        user_content = body.user_message or f"【技能：{skill['scenario_name']}】"
        user_msg = Message(role=Role.USER, content=user_content)
        is_first = conv.message_count == 0
        await repo.add_message(conv_id, user_msg, is_pinned=is_first)
        await conv_session.commit()

    async def event_stream():
        yield {"event": "conversation_id", "data": json.dumps({"conversation_id": conv_id})}

        full_response = []
        try:
            async with session_factory() as exec_session:
                async for chunk in execute_skill_stream(
                    skill_key=skill_key,
                    input_data=body.input_data,
                    user_id=user_id,
                    session=exec_session,
                    profile=profile,
                ):
                    full_response.append(chunk)
                    yield {"event": "text_delta", "data": json.dumps({"text": chunk})}
                await exec_session.commit()

        except Exception:
            logger.exception("Error in skill SSE stream: %s", skill_key)
            yield {"event": "error", "data": json.dumps({"message": "执行出错，请重试"})}
            return

        if full_response:
            async with session_factory() as save_session:
                save_repo = SQLAlchemyConversationRepo(save_session)
                await save_repo.add_message(
                    conv_id,
                    Message(role=Role.ASSISTANT, content="".join(full_response)),
                )
                await save_session.commit()

        yield {"event": "done", "data": json.dumps({})}

    return EventSourceResponse(event_stream())
