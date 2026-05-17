"""Feedback API — collect user feedback."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserModel
from backend.observability import trace

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackPayload(BaseModel):
    rating: int  # 1-5
    comment: str = ""
    context: str = ""  # e.g. "chat", "skill:weekly_report"


@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackPayload,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    trace(
        "feedback",
        user_id=current_user.id,
        rating=payload.rating,
        context=payload.context,
        comment_len=len(payload.comment),
    )
    logger.info(
        "Feedback from user %d: rating=%d context=%s comment=%s",
        current_user.id,
        payload.rating,
        payload.context,
        payload.comment[:100],
    )
    return {"ok": True}
