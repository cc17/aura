from typing import Any

from backend.tools.base import BaseTool, ToolDefinition, ToolParameter


class ResumeModifyTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="resume_modify",
            description=(
                "Modify a user's resume. Accepts the current resume text and "
                "modification instructions, returns the improved resume."
            ),
            parameters=[
                ToolParameter(
                    name="resume_text",
                    type="string",
                    description="The current resume content to modify",
                ),
                ToolParameter(
                    name="instructions",
                    type="string",
                    description="Specific instructions for how to modify the resume",
                ),
                ToolParameter(
                    name="target_role",
                    type="string",
                    description="The target job role to tailor the resume for",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        # Stub implementation — will be replaced with actual logic later
        return (
            "[Resume Tool] This is a stub response. "
            "Resume modification logic has not been implemented yet. "
            f"Received parameters: {list(kwargs.keys())}"
        )
