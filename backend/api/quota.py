"""Quota API — return current user's billing quota status."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserModel
from backend.services.quota_service import get_quota_info

router = APIRouter(prefix="/quota")


@router.get("")
async def get_quota(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    info = await get_quota_info(current_user.id, session)
    await session.commit()
    return info
