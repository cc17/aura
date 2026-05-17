"""Suggestions API — retrieve latest suggestions for the current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserModel, UserSuggestionModel

router = APIRouter()


@router.get("/suggestions/latest")
async def get_latest_suggestions(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return the most recently generated suggestions for the user."""
    stmt = (
        select(UserSuggestionModel)
        .where(UserSuggestionModel.user_id == current_user.id)
        .order_by(UserSuggestionModel.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return {"suggestions": [], "message_id": None}
    return {"suggestions": row.suggestions, "message_id": row.message_id}
