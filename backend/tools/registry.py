from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any

from backend.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        defn = tool.definition()
        self._tools[defn.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": defn.name, "description": defn.description}
            for tool in self._tools.values()
            if (defn := tool.definition())
        ]

    def get_llm_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_llm_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        return await tool.execute(**arguments)

    def auto_discover(self) -> None:
        """Scan backend.tools package and register all BaseTool subclasses."""
        import backend.tools as tools_pkg

        for importer, module_name, is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
            if module_name in ("base", "registry"):
                continue
            module = importlib.import_module(f"backend.tools.{module_name}")
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    self.register(obj())


# Singleton
registry = ToolRegistry()
