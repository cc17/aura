"""Stats API — in-process counters + DB aggregates (admin/internal view)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db, require_admin
from backend.memory.models import (
    ConversationModel,
    SkillExecutionModel,
    UserModel,
    UserSuggestionModel,
)
from backend.observability import get_stats

router = APIRouter()


@router.get("/stats")
async def stats(current_user: UserModel = Depends(get_current_user)):
    """Real-time in-process counters for key paths."""
    return get_stats()


@router.get("/stats/dashboard", dependencies=[Depends(require_admin)])
async def dashboard(session: AsyncSession = Depends(get_db)):
    """Internal data dashboard — aggregates from the DB."""
    # Total users
    total_users = (await session.execute(select(func.count()).select_from(UserModel))).scalar_one()

    # Total conversations
    total_convs = (
        await session.execute(select(func.count()).select_from(ConversationModel))
    ).scalar_one()

    # Skill usage counts
    skill_rows = await session.execute(
        select(
            SkillExecutionModel.skill_id,
            func.count().label("cnt"),
            func.avg(SkillExecutionModel.duration_ms).label("avg_ms"),
        )
        .group_by(SkillExecutionModel.skill_id)
        .order_by(func.count().desc())
    )
    skill_stats = [
        {"skill_id": r.skill_id, "count": r.cnt, "avg_duration_ms": round(r.avg_ms or 0)}
        for r in skill_rows
    ]

    # Skill success rate
    total_execs = (
        await session.execute(select(func.count()).select_from(SkillExecutionModel))
    ).scalar_one()
    success_execs = (
        await session.execute(
            select(func.count()).where(SkillExecutionModel.status == "success")
        )
    ).scalar_one()
    skill_success_rate = round(success_execs / total_execs * 100, 1) if total_execs else 0.0

    # Suggestion click rate
    total_suggestions_rows = (
        await session.execute(select(func.count()).select_from(UserSuggestionModel))
    ).scalar_one()
    clicked_suggestions = (
        await session.execute(
            select(func.count()).where(UserSuggestionModel.clicked_index.is_not(None))
        )
    ).scalar_one()
    suggestion_ctr = (
        round(clicked_suggestions / total_suggestions_rows * 100, 1)
        if total_suggestions_rows
        else 0.0
    )

    return {
        "total_users": total_users,
        "total_conversations": total_convs,
        "skill_stats": skill_stats,
        "skill_success_rate_pct": skill_success_rate,
        "suggestion_ctr_pct": suggestion_ctr,
        "in_process": get_stats(),
    }
