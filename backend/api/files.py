"""File download endpoint for generated exports."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.storage.file_store import file_store

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}/{filename}")
@router.get("/{file_id}")
async def download_file(file_id: str, filename: str = ""):
    entry = file_store.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")

    dl_name = filename or entry.filename
    return Response(
        content=entry.data,
        media_type=entry.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{dl_name}"',
        },
    )
