"""Recommendations API — home screen cards + behavior event recording."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import SkillSignalModel, UserModel
from backend.services.skill_recommender import get_recommendations
from backend.services.skill_registry import get_skill

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations")

_VALID_SIGNAL_TYPES = {
    "impressioned", "clicked", "opened", "started", "submitted",
    "completed", "abandoned", "output_copied", "output_liked",
    "output_disliked", "output_edited", "shared",
}


# ---------------------------------------------------------------------------
# GET /api/recommendations — home screen cards
# ---------------------------------------------------------------------------


@router.get("")
async def recommendations(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await get_recommendations(
        user_id=current_user.id,
        profile=current_user.profile or {},
        session=session,
    )


# ---------------------------------------------------------------------------
# POST /api/recommendations/events — record impression / click / etc.
# ---------------------------------------------------------------------------


class EventItem(BaseModel):
    item_type: str        # "skill" | "agent"
    item_key: str         # skill_key or agent key
    signal_type: str      # must be in _VALID_SIGNAL_TYPES
    context: dict | None = None
    session_id: str | None = None


class EventsRequest(BaseModel):
    events: list[EventItem]


@router.post("/events", status_code=204)
async def record_events(
    body: EventsRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    for ev in body.events:
        if ev.signal_type not in _VALID_SIGNAL_TYPES:
            continue
        if ev.item_type == "skill":
            skill = get_skill(ev.item_key)
            if skill:
                session.add(
                    SkillSignalModel(
                        user_id=current_user.id,
                        skill_id=skill["id"],
                        signal_type=ev.signal_type,
                        context=ev.context or {},
                        session_id=ev.session_id,
                    )
                )
        # agent events are accepted silently — agents have no DB skill_id yet
    await session.commit()
