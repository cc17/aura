"""Adapter: convert Aura BaseTool instances to LangChain StructuredTool."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from backend.tools.base import BaseTool, ToolParameter


def _build_args_model(tool_name: str, params: list[ToolParameter]) -> type[BaseModel]:
    """Dynamically build a Pydantic model from ToolParameter list."""
    fields: dict[str, Any] = {}
    for p in params:
        python_type = {"string": str, "integer": int, "number": float, "boolean": bool}.get(
            p.type, str
        )
        if p.required:
            fields[p.name] = (python_type, Field(description=p.description))
        else:
            fields[p.name] = (python_type | None, Field(default=None, description=p.description))
    model_name = f"{tool_name.title().replace('_', '')}Args"
    return create_model(model_name, **fields)


def aura_tool_to_langchain(tool: BaseTool) -> StructuredTool:
    """Convert a single Aura BaseTool to a LangChain StructuredTool."""
    defn = tool.definition()
    args_model = _build_args_model(defn.name, defn.parameters)

    async def _arun(**kwargs: Any) -> str:
        return await tool.execute(**kwargs)

    def _run(**kwargs: Any) -> str:
        return asyncio.run(tool.execute(**kwargs))

    return StructuredTool(
        name=defn.name,
        description=defn.description,
        args_schema=args_model,
        func=_run,
        coroutine=_arun,
    )


def adapt_all(tools: dict[str, BaseTool]) -> list[StructuredTool]:
    """Convert all registered Aura tools to LangChain tools."""
    return [aura_tool_to_langchain(t) for t in tools.values()]
