"""Tests for the PPT builder tool."""

import json

import pytest

from backend.tools.ppt_tool import PptBuilderTool

_VALID_OUTLINE = {
    "title": "Test Presentation",
    "subtitle": "A test deck",
    "theme": "modern",
    "slides": [
        {
            "title": "Introduction",
            "bullets": ["Point one", "Point two", "Point three"],
            "notes": "Opening remarks",
        },
        {
            "title": "Key Findings",
            "bullets": ["Finding A", "Finding B"],
        },
    ],
}


@pytest.mark.asyncio
async def test_generates_file_id():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps(_VALID_OUTLINE))
    assert "File ID" in result
    assert "/api/files/" in result


@pytest.mark.asyncio
async def test_result_contains_title():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps(_VALID_OUTLINE))
    assert "Test Presentation" in result


@pytest.mark.asyncio
async def test_slide_count_in_result():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps(_VALID_OUTLINE))
    assert "2" in result  # 2 content slides


@pytest.mark.asyncio
async def test_invalid_json_returns_error():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json="{not valid json")
    assert "Error" in result


@pytest.mark.asyncio
async def test_missing_title_returns_error():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps({"slides": []}))
    assert "Error" in result


@pytest.mark.asyncio
async def test_missing_slides_returns_error():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps({"title": "No slides"}))
    assert "Error" in result


@pytest.mark.asyncio
async def test_empty_outline_json_returns_error():
    tool = PptBuilderTool()
    result = await tool.execute(outline_json="")
    assert "Error" in result


@pytest.mark.asyncio
async def test_all_themes():
    tool = PptBuilderTool()
    for theme in ("modern", "minimal", "corporate"):
        outline = {**_VALID_OUTLINE, "theme": theme}
        result = await tool.execute(outline_json=json.dumps(outline))
        assert "File ID" in result, f"Failed for theme={theme}"


@pytest.mark.asyncio
async def test_definition_name():
    tool = PptBuilderTool()
    assert tool.definition().name == "ppt_builder"


@pytest.mark.asyncio
async def test_file_stored_and_retrievable():
    from backend.storage.file_store import file_store

    tool = PptBuilderTool()
    result = await tool.execute(outline_json=json.dumps(_VALID_OUTLINE))

    # Extract file_id from result
    file_id = None
    for line in result.splitlines():
        if "File ID" in line:
            file_id = line.split(":", 1)[1].strip()
            break

    assert file_id is not None
    entry = file_store.get(file_id)
    assert entry is not None
    assert entry.filename.endswith(".pptx")
    assert len(entry.data) > 1000  # non-trivial file size
