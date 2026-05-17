"""Tests for gaokao tools (interest, career, videos)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.storage.cache_store import cache_store
from backend.tools.career_outlook_tool import CareerOutlookTool
from backend.tools.interest_assessment_tool import InterestAssessmentTool
from backend.tools.search_videos_tool import SearchVideosTool


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the global cache before each test."""
    cache_store._data.clear()


# ── helpers ──────────────────────────────────────────────────────────────

def _mock_serper_client(organic: list[dict]):
    """Return a mock httpx.AsyncClient that returns the given organic results."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"organic": organic}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ═════════════════════════════════════════════════════════════════════════
# InterestAssessmentTool
# ═════════════════════════════════════════════════════════════════════════

class TestInterestAssessmentTool:
    @pytest.fixture
    def tool(self):
        return InterestAssessmentTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "interest_assessment"
        param_names = [p.name for p in defn.parameters]
        assert "interests" in param_names

    @pytest.mark.asyncio
    async def test_missing_interests(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_returns_riasec_content(self, tool):
        result = await tool.execute(interests="我喜欢编程和数学")
        assert "RIASEC" in result
        assert "我喜欢编程和数学" in result
        # Should contain all six types
        assert "实际型" in result
        assert "研究型" in result
        assert "艺术型" in result
        assert "社会型" in result
        assert "企业型" in result
        assert "常规型" in result

    @pytest.mark.asyncio
    async def test_contains_major_recommendations(self, tool):
        result = await tool.execute(interests="我喜欢画画和设计")
        assert "计算机科学与技术" in result  # From Investigative type
        assert "视觉传达设计" in result  # From Artistic type


# ═════════════════════════════════════════════════════════════════════════
# CareerOutlookTool
# ═════════════════════════════════════════════════════════════════════════

class TestCareerOutlookTool:
    @pytest.fixture
    def tool(self):
        return CareerOutlookTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "career_outlook"
        param_names = [p.name for p in defn.parameters]
        assert "major" in param_names
        assert "location" in param_names

    @pytest.mark.asyncio
    async def test_missing_major(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_missing_api_key(self, tool):
        with patch("backend.tools.career_outlook_tool.settings") as mock_settings:
            mock_settings.serper_api_key = ""
            result = await tool.execute(major="计算机科学与技术")
            assert "API key" in result

    @pytest.mark.asyncio
    async def test_search_returns_formatted_results(self, tool):
        organic = [
            {
                "title": "计算机专业就业前景分析",
                "link": "https://example.com/career1",
                "snippet": "平均薪资 15k",
            },
        ]
        mock_client = _mock_serper_client(organic)

        with (
            patch("backend.tools.career_outlook_tool.settings") as mock_settings,
            patch("backend.tools.career_outlook_tool.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.serper_api_key = "test-key"
            result = await tool.execute(major="计算机科学与技术", location="北京")

        assert "计算机科学与技术" in result
        assert "北京" in result
        assert "15k" in result

    @pytest.mark.asyncio
    async def test_no_results(self, tool):
        mock_client = _mock_serper_client([])

        with (
            patch("backend.tools.career_outlook_tool.settings") as mock_settings,
            patch("backend.tools.career_outlook_tool.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.serper_api_key = "test-key"
            result = await tool.execute(major="不存在的专业xyz")

        assert "未找到" in result


# ═════════════════════════════════════════════════════════════════════════
# SearchVideosTool
# ═════════════════════════════════════════════════════════════════════════

class TestSearchVideosTool:
    @pytest.fixture
    def tool(self):
        return SearchVideosTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "search_videos"
        param_names = [p.name for p in defn.parameters]
        assert "query" in param_names

    @pytest.mark.asyncio
    async def test_missing_query(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_missing_api_key(self, tool):
        with patch("backend.tools.search_videos_tool.settings") as mock_settings:
            mock_settings.serper_api_key = ""
            result = await tool.execute(query="计算机专业介绍")
            assert "API key" in result

    @pytest.mark.asyncio
    async def test_search_query_targets_video_sites(self, tool):
        """Verify the search query includes site:bilibili.com."""
        organic = [
            {
                "title": "计算机专业全面介绍",
                "link": "https://www.bilibili.com/video/BV123",
                "snippet": "B站科普视频",
            },
        ]
        mock_client = _mock_serper_client(organic)

        with (
            patch("backend.tools.search_videos_tool.settings") as mock_settings,
            patch("backend.tools.search_videos_tool.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.serper_api_key = "test-key"
            await tool.execute(query="计算机专业介绍")

        # Check the actual search query sent to Serper
        call_args = mock_client.post.call_args
        sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "site:bilibili.com" in sent_payload["q"]

    @pytest.mark.asyncio
    async def test_platform_labels(self, tool):
        organic = [
            {
                "title": "B站视频",
                "link": "https://www.bilibili.com/video/BV123",
                "snippet": "B站",
            },
            {
                "title": "抖音视频",
                "link": "https://www.douyin.com/video/123",
                "snippet": "抖音",
            },
        ]
        mock_client = _mock_serper_client(organic)

        with (
            patch("backend.tools.search_videos_tool.settings") as mock_settings,
            patch("backend.tools.search_videos_tool.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.serper_api_key = "test-key"
            result = await tool.execute(query="计算机专业")

        assert "【B站】" in result
        assert "【抖音】" in result

    @pytest.mark.asyncio
    async def test_no_results(self, tool):
        mock_client = _mock_serper_client([])

        with (
            patch("backend.tools.search_videos_tool.settings") as mock_settings,
            patch("backend.tools.search_videos_tool.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.serper_api_key = "test-key"
            result = await tool.execute(query="不存在的视频xyz")

        assert "未找到" in result
