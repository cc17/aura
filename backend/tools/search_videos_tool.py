"""Search videos tool — find educational videos on Bilibili/Douyin via Serper."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/search"


class SearchVideosTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_videos",
            description="搜索 B站和抖音上的科普/教育视频，帮助学生了解专业和大学。",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜索关键词，如 '计算机专业介绍' 或 '清华大学校园生活'",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").strip()
        if not query:
            return "Error: query parameter is required."

        if not settings.serper_api_key:
            return (
                "Error: Serper API key is not configured. "
                "Please set AURA_SERPER_API_KEY in your environment."
            )

        cache_key = cache_store.make_key("videos", query)
        cached = cache_store.get(cache_key)
        if cached is not None:
            logger.info("search_videos cache hit for key=%s", cache_key)
            return cached

        search_query = f"{query} (site:bilibili.com OR site:douyin.com)"
        payload = {"q": search_query, "gl": "cn", "hl": "zh-cn", "num": 10}
        headers = {
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(_SERPER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Video search failed: %s", exc)
            return f"Error: 搜索视频失败 — {exc}"

        results = data.get("organic", [])
        if not results:
            return f"未找到关于「{query}」的相关视频，请尝试其他关键词。"

        formatted = _format_results(results, query)
        cache_store.set(cache_key, formatted)
        return formatted


def _format_results(results: list[dict[str, Any]], query: str) -> str:
    lines = [f"为「{query}」找到以下科普视频：\n"]
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        # Detect platform
        if "bilibili.com" in link:
            platform = "B站"
        elif "douyin.com" in link:
            platform = "抖音"
        else:
            platform = "其他"

        lines.append(f"{i}. 【{platform}】**{title}**")
        if snippet:
            lines.append(f"   {snippet}")
        if link:
            lines.append(f"   [观看视频]({link})")
        lines.append("")
    return "\n".join(lines)
