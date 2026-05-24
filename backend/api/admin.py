"""Admin dashboard API — protected by AURA_ADMIN_TOKEN."""

from __future__ import annotations

import hmac
import pathlib
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.memory.database import get_session_factory
from backend.memory.models import (
    ConversationModel,
    IndustrySkillModel,
    MessageModel,
    SkillExecutionModel,
    SkillSignalModel,
    UserModel,
    UserQuotaModel,
)

router = APIRouter(prefix="/admin")

_ERROR_LOG = pathlib.Path("aura_error.log")
_AGENT_COUNT = 6  # matches frontend config/agents.ts


async def _require_admin(authorization: Annotated[str, Header()] = ""):
    token = settings.admin_token
    if not token:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=403, detail="Invalid admin token")


def _db():
    factory = get_session_factory()
    return factory


async def _get_session():
    async with get_session_factory()() as session:
        yield session


@router.get("/dashboard", dependencies=[Depends(_require_admin)])
async def dashboard(session: AsyncSession = Depends(_get_session)):
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # --- Users ---
    total_users = (
        await session.execute(select(func.count()).select_from(UserModel))
    ).scalar_one()

    new_today = (
        await session.execute(
            select(func.count()).where(UserModel.created_at >= today_start)
        )
    ).scalar_one()

    new_this_week = (
        await session.execute(
            select(func.count()).where(UserModel.created_at >= week_start)
        )
    ).scalar_one()

    # DAU: distinct users who sent at least one message today
    dau = (
        await session.execute(
            select(func.count(distinct(ConversationModel.user_id)))
            .join(MessageModel, MessageModel.conversation_id == ConversationModel.id)
            .where(
                MessageModel.created_at >= today_start,
                MessageModel.role == "user",
            )
        )
    ).scalar_one()

    # --- Plan distribution ---
    plan_rows = await session.execute(
        select(UserQuotaModel.plan, func.count().label("cnt"))
        .group_by(UserQuotaModel.plan)
    )
    plan_dist = {r.plan: r.cnt for r in plan_rows}

    # --- Conversations & messages today ---
    convs_today = (
        await session.execute(
            select(func.count()).where(ConversationModel.created_at >= today_start)
        )
    ).scalar_one()

    msgs_today = (
        await session.execute(
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.created_at >= today_start, MessageModel.role == "user")
        )
    ).scalar_one()

    # --- Skills ---
    total_skills = (
        await session.execute(select(func.count()).select_from(IndustrySkillModel))
    ).scalar_one()

    # --- Skill usage top 10 (by total signals, 30 days) — joined with skill name ---
    top_skills_rows = await session.execute(
        select(
            SkillSignalModel.skill_id,
            IndustrySkillModel.scenario_name,
            IndustrySkillModel.skill_key,
            func.count().label("total"),
            func.sum(
                case((SkillSignalModel.signal_type == "completed", 1), else_=0)
            ).label("completed"),
            func.sum(
                case((SkillSignalModel.signal_type == "clicked", 1), else_=0)
            ).label("clicked"),
            func.sum(
                case((SkillSignalModel.signal_type == "abandoned", 1), else_=0)
            ).label("abandoned"),
        )
        .join(IndustrySkillModel, IndustrySkillModel.id == SkillSignalModel.skill_id)
        .where(SkillSignalModel.created_at >= thirty_days_ago)
        .group_by(SkillSignalModel.skill_id, IndustrySkillModel.scenario_name, IndustrySkillModel.skill_key)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_skills = [
        {
            "skill_key": r.skill_key,
            "name": r.scenario_name,
            "clicked": int(r.clicked or 0),
            "completed": int(r.completed or 0),
            "abandoned": int(r.abandoned or 0),
        }
        for r in top_skills_rows
    ]

    # --- Top agents (by click signals, 30 days) ---
    top_agents_rows = await session.execute(
        select(
            SkillSignalModel.agent_key,
            func.count().label("total"),
            func.sum(
                case((SkillSignalModel.signal_type == "clicked", 1), else_=0)
            ).label("clicked"),
            func.sum(
                case((SkillSignalModel.signal_type == "used", 1), else_=0)
            ).label("used"),
        )
        .where(
            SkillSignalModel.created_at >= thirty_days_ago,
            SkillSignalModel.agent_key.is_not(None),
        )
        .group_by(SkillSignalModel.agent_key)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_agents = [
        {
            "agent_key": r.agent_key,
            "clicked": int(r.clicked or 0),
            "used": int(r.used or 0),
        }
        for r in top_agents_rows
    ]

    # --- Overall skill funnel (30 days, skills only) ---
    funnel_rows = await session.execute(
        select(SkillSignalModel.signal_type, func.count().label("cnt"))
        .where(
            SkillSignalModel.created_at >= thirty_days_ago,
            SkillSignalModel.skill_id.is_not(None),
        )
        .group_by(SkillSignalModel.signal_type)
    )
    funnel = {r.signal_type: r.cnt for r in funnel_rows}

    # --- Skill execution success rate ---
    total_execs = (
        await session.execute(select(func.count()).select_from(SkillExecutionModel))
    ).scalar_one()
    success_execs = (
        await session.execute(
            select(func.count()).where(SkillExecutionModel.status == "success")
        )
    ).scalar_one()
    exec_success_rate = round(success_execs / total_execs * 100, 1) if total_execs else None

    # --- Recent errors ---
    recent_errors: list[str] = []
    if _ERROR_LOG.exists():
        import re as _re
        _log_line = _re.compile(r"^\d{4}-\d{2}-\d{2}")
        lines = _ERROR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        # Only include top-level log entries (start with timestamp), drop stack trace lines
        recent_errors = [l for l in lines if l.strip() and _log_line.match(l)][-20:]

    return {
        "users": {
            "total": total_users,
            "dau": dau,
            "new_today": new_today,
            "new_this_week": new_this_week,
            "plan_distribution": plan_dist,
        },
        "activity": {
            "conversations_today": convs_today,
            "messages_today": msgs_today,
        },
        "skills": {
            "total": total_skills,
            "agents": _AGENT_COUNT,
            "top10_30d": top_skills,
            "top_agents_30d": top_agents,
            "funnel_30d": funnel,
            "exec_success_rate_pct": exec_success_rate,
        },
        "errors": {
            "recent": recent_errors,
        },
    }
