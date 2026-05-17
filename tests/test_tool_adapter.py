from typing import Any

import pytest

from backend.tools.adapter import aura_tool_to_langchain
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter


class DummyTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dummy",
            description="A dummy tool for testing",
            parameters=[
                ToolParameter(name="text", type="string", description="Input text"),
                ToolParameter(
                    name="count", type="integer", description="Repeat count", required=False
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        text = kwargs.get("text", "")
        count = kwargs.get("count", 1) or 1
        return f"{text} x{count}"


def test_adapter_preserves_metadata():
    lc_tool = aura_tool_to_langchain(DummyTool())
    assert lc_tool.name == "dummy"
    assert "dummy tool" in lc_tool.description.lower()


def test_adapter_args_schema():
    lc_tool = aura_tool_to_langchain(DummyTool())
    schema = lc_tool.args_schema.model_json_schema()
    assert "text" in schema["properties"]
    assert "count" in schema["properties"]
    assert "text" in schema["required"]
    assert "count" not in schema["required"]


@pytest.mark.asyncio
async def test_adapter_async_invoke():
    lc_tool = aura_tool_to_langchain(DummyTool())
    result = await lc_tool.ainvoke({"text": "hello", "count": 3})
    assert result == "hello x3"


@pytest.mark.asyncio
async def test_adapter_optional_param():
    lc_tool = aura_tool_to_langchain(DummyTool())
    result = await lc_tool.ainvoke({"text": "hi"})
    assert result == "hi x1"
