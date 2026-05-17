from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from backend.core.auth import get_current_user
from backend.memory.database import get_session_factory
from backend.memory.models import UserModel, UserQuotaModel
from backend.memory.repo import SQLAlchemyConversationRepo

router = APIRouter()


@router.post("/conversations")
async def create_conversation(current_user: UserModel = Depends(get_current_user)):
    async with get_session_factory()() as session:
        repo = SQLAlchemyConversationRepo(session)
        conv = await repo.create_conversation(user_id=current_user.id)
        await session.commit()
        return {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
        }


_CST = timezone(timedelta(hours=8))


@router.get("/conversations")
async def list_conversations(
    include_archived: bool = False,
    current_user: UserModel = Depends(get_current_user),
):
    async with get_session_factory()() as session:
        quota_row = await session.scalar(
            select(UserQuotaModel).where(UserQuotaModel.user_id == current_user.id)
        )
        plan = quota_row.plan if quota_row else "free"
        since = (
            datetime.now(_CST) - timedelta(days=30) if plan == "free" else None
        )

        repo = SQLAlchemyConversationRepo(session)
        convs = await repo.list_conversations(
            include_archived=include_archived, user_id=current_user.id, since=since
        )
        return {
            "conversations": [
                {"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()}
                for c in convs
            ]
        }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    async with get_session_factory()() as session:
        repo = SQLAlchemyConversationRepo(session)
        conv = await repo.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await repo.archive_conversation(conversation_id)
        await session.commit()
        return {"ok": True}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    async with get_session_factory()() as session:
        repo = SQLAlchemyConversationRepo(session)
        conv = await repo.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = await repo.get_messages(conversation_id)
        return {
            "id": conv.id,
            "title": conv.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }
