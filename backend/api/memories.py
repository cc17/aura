"""User memories API — list and delete long-term memories."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_db
from backend.memory.models import UserMemoryModel, UserModel

router = APIRouter()


@router.get("/memories")
async def list_memories(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserMemoryModel)
        .where(UserMemoryModel.user_id == current_user.id)
        .order_by(UserMemoryModel.importance.desc(), UserMemoryModel.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {
        "memories": [
            {
                "id": r.id,
                "content": r.content,
                "category": r.category,
                "importance": r.importance,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await session.execute(
        delete(UserMemoryModel).where(
            UserMemoryModel.id == memory_id,
            UserMemoryModel.user_id == current_user.id,
        )
    )
    await session.commit()
    return {"ok": True}
