from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter]


class BaseTool(ABC):
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's metadata and parameter schema."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments. Returns result as string."""

    def to_llm_schema(self) -> dict[str, Any]:
        """Convert tool definition to LLM function calling JSON Schema format."""
        defn = self.definition()
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in defn.parameters:
            prop: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": defn.name,
                "description": defn.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
