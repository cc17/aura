import pytest

from backend.tools.base import BaseTool, ToolDefinition, ToolParameter
from backend.tools.registry import ToolRegistry


class DummyTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dummy",
            description="A dummy tool for testing",
            parameters=[
                ToolParameter(name="input", type="string", description="Input text"),
            ],
        )

    async def execute(self, **kwargs) -> str:
        return f"dummy result: {kwargs.get('input', '')}"


class AnotherTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="another",
            description="Another test tool",
            parameters=[
                ToolParameter(name="x", type="number", description="A number"),
                ToolParameter(name="y", type="number", description="Another number", required=False),
            ],
        )

    async def execute(self, **kwargs) -> str:
        return "another result"


def test_register_and_list():
    reg = ToolRegistry()
    reg.register(DummyTool())
    tools = reg.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "dummy"


def test_register_multiple():
    reg = ToolRegistry()
    reg.register(DummyTool())
    reg.register(AnotherTool())
    assert len(reg.list_tools()) == 2


def test_get_tool():
    reg = ToolRegistry()
    reg.register(DummyTool())
    assert reg.get("dummy") is not None
    assert reg.get("nonexistent") is None


@pytest.mark.asyncio
async def test_execute_tool():
    reg = ToolRegistry()
    reg.register(DummyTool())
    result = await reg.execute("dummy", {"input": "hello"})
    assert result == "dummy result: hello"


@pytest.mark.asyncio
async def test_execute_missing_tool():
    reg = ToolRegistry()
    result = await reg.execute("nonexistent", {})
    assert "not found" in result.lower()


def test_llm_schema():
    tool = DummyTool()
    schema = tool.to_llm_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "dummy"
    props = schema["function"]["parameters"]["properties"]
    assert "input" in props
    assert schema["function"]["parameters"]["required"] == ["input"]


def test_llm_schema_optional_params():
    tool = AnotherTool()
    schema = tool.to_llm_schema()
    assert schema["function"]["parameters"]["required"] == ["x"]


def test_get_llm_schemas():
    reg = ToolRegistry()
    reg.register(DummyTool())
    reg.register(AnotherTool())
    schemas = reg.get_llm_schemas()
    assert len(schemas) == 2


def test_auto_discover():
    reg = ToolRegistry()
    reg.auto_discover()
    tools = reg.list_tools()
    names = [t["name"] for t in tools]
    assert "resume_modify" in names
