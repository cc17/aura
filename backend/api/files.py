"""File download endpoint for generated exports."""

import hmac

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.storage.file_store import file_store

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}/{filename}")
@router.get("/{file_id}")
async def download_file(
    file_id: str,
    filename: str = "",
    t: str = Query(default="", description="Download token"),
):
    entry = file_store.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    if not t or not hmac.compare_digest(t, entry.download_token):
        raise HTTPException(status_code=403, detail="Invalid or missing download token")

    dl_name = filename or entry.filename
    # HTML files are opened inline in the browser (presentations, previews).
    # All other files (docx, pdf…) are forced to download.
    is_html = entry.content_type.startswith("text/html") or dl_name.lower().endswith(".html")
    disposition = "inline" if is_html else f'attachment; filename="{dl_name}"'
    return Response(
        content=entry.data,
        media_type=entry.content_type,
        headers={"Content-Disposition": disposition},
    )
