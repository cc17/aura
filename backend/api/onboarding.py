"""Onboarding endpoint — collects the 3-question profile and marks user as onboarded."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserModel
from backend.services.profile_service import mark_onboarded, update_profile

router = APIRouter()


class OnboardingRequest(BaseModel):
    industry: str        # e.g. "互联网"
    role: str            # e.g. "研发助理"
    pain_points: list[str]   # e.g. ["写周报", "会议纪要"]
    ai_proficiency: str  # e.g. "新手" | "入门" | "熟练"


@router.post("/onboarding")
async def complete_onboarding(
    body: OnboardingRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    profile = await update_profile(
        session,
        current_user.id,
        {
            "industry": body.industry,
            "role": body.role,
            "pain_points": body.pain_points,
            "ai_proficiency": body.ai_proficiency,
        },
        confidence=1.0,
    )
    await mark_onboarded(session, current_user.id)
    await session.commit()
    return {"ok": True, "profile": profile}
