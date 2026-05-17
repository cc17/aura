"""Profile endpoints — read and manually update user profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserModel
from backend.services.profile_service import update_profile

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    updates: dict  # arbitrary profile field updates


@router.get("/profile")
async def get_profile(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "onboarded": current_user.onboarded,
        "profile": current_user.profile or {},
        "profile_updated_at": (
            current_user.profile_updated_at.isoformat()
            if current_user.profile_updated_at
            else None
        ),
    }


@router.patch("/profile")
async def patch_profile(
    body: ProfileUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # Manual edits always set confidence=1.0
    profile = await update_profile(
        session, current_user.id, body.updates, confidence=1.0
    )
    await session.commit()
    return {"ok": True, "profile": profile}
