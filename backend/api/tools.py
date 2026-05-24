from fastapi import APIRouter, Depends

from backend.core.auth import get_current_user
from backend.memory.models import UserModel
from backend.tools.registry import registry

router = APIRouter()


@router.get("/tools")
async def list_tools(current_user: UserModel = Depends(get_current_user)):
    return {"tools": registry.list_tools()}
