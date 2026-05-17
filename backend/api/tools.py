from fastapi import APIRouter

from backend.tools.registry import registry

router = APIRouter()


@router.get("/tools")
async def list_tools():
    return {"tools": registry.list_tools()}
