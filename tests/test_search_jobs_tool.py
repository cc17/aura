"""Tests for the search_jobs tool."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.storage.cache_store import CacheStore, cache_store
from backend.tools.search_jobs_tool import SearchJobsTool


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the global cache before each test."""
    cache_store._data.clear()


@pytest.fixture
def tool():
    return SearchJobsTool()


def test_definition(tool):
    defn = tool.definition()
    assert defn.name == "search_jobs"
    param_names = [p.name for p in defn.parameters]
    assert "query" in param_names
    assert "location" in param_names


@pytest.mark.asyncio
async def test_missing_query(tool):
    result = await tool.execute()
    assert "Error" in result


@pytest.mark.asyncio
async def test_missing_api_key(tool):
    with patch("backend.tools.search_jobs_tool.settings") as mock_settings:
        mock_settings.serper_api_key = ""
        result = await tool.execute(query="test")
        assert "API key" in result


@pytest.mark.asyncio
async def test_search_returns_formatted_results(tool):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "高级后端工程师 - 字节跳动",
                "link": "https://example.com/job1",
                "snippet": "负责后端架构设计",
            },
            {
                "title": "Java 开发工程师 - 阿里巴巴",
                "link": "https://example.com/job2",
                "snippet": "Java 后端开发",
            },
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with (
        patch("backend.tools.search_jobs_tool.settings") as mock_settings,
        patch("backend.tools.search_jobs_tool.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.serper_api_key = "test-key"
        result = await tool.execute(query="后端工程师", location="北京")

    assert "匹配职位" in result
    assert "字节跳动" in result
    assert "阿里巴巴" in result
    assert "https://example.com/job1" in result


@pytest.mark.asyncio
async def test_cache_hit_skips_api(tool):
    """Second call with same params should use cache, not call API."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "organic": [{"title": "Test Job", "link": "https://example.com", "snippet": "desc"}]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with (
        patch("backend.tools.search_jobs_tool.settings") as mock_settings,
        patch("backend.tools.search_jobs_tool.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.serper_api_key = "test-key"

        # First call — hits API
        result1 = await tool.execute(query="test query")
        assert mock_client.post.call_count == 1

        # Second call — should use cache
        result2 = await tool.execute(query="test query")
        assert mock_client.post.call_count == 1  # No additional API call

    assert result1 == result2


@pytest.mark.asyncio
async def test_no_results(tool):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"organic": []}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with (
        patch("backend.tools.search_jobs_tool.settings") as mock_settings,
        patch("backend.tools.search_jobs_tool.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.serper_api_key = "test-key"
        result = await tool.execute(query="nonexistent job xyz")

    assert "No matching" in result
