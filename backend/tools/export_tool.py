"""Export resume content as a downloadable .docx file."""

from typing import Any

from backend.storage.file_store import file_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter
from backend.utils.docx_builder import build_docx


class ExportDocxTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="export_docx",
            description=(
                "Export resume content as a downloadable Word (.docx) file. "
                "Call this after finalizing the resume to give the user a download link."
            ),
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="The full resume content (markdown-formatted) to export",
                ),
                ToolParameter(
                    name="filename",
                    type="string",
                    description="Desired filename without extension (default: resume)",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        content: str = kwargs.get("content", "")
        filename: str = kwargs.get("filename", "resume")

        if not content.strip():
            return "Error: No content provided to export."

        if not filename.endswith(".docx"):
            filename = f"{filename}.docx"

        docx_bytes = build_docx(content)
        file_id, token = file_store.save(
            filename=filename,
            data=docx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        return f"[📎 下载 {filename}](/api/files/{file_id}/{filename}?t={token})"
