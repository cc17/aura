from fastapi import APIRouter, Depends

from backend.core.auth import get_current_user
from backend.llm.models import AVAILABLE_MODELS
from backend.memory.models import UserModel

router = APIRouter()


@router.get("/models")
async def list_models(current_user: UserModel = Depends(get_current_user)):
    return {"models": [m.model_dump() for m in AVAILABLE_MODELS]}
