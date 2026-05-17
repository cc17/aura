"""Career outlook tool — search for employment prospects of a given major."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/search"


class CareerOutlookTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="career_outlook",
            description="搜索某个专业的就业前景、薪资水平和就业率等信息。",
            parameters=[
                ToolParameter(
                    name="major",
                    type="string",
                    description="专业名称，如 '计算机科学与技术'",
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="就业地点，如 '北京'。不填则搜索全国数据。",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        major = kwargs.get("major", "").strip()
        if not major:
            return "Error: major parameter is required."

        if not settings.serper_api_key:
            return (
                "Error: Serper API key is not configured. "
                "Please set AURA_SERPER_API_KEY in your environment."
            )

        location = kwargs.get("location") or ""
        cache_key = cache_store.make_key("career", major, location)
        cached = cache_store.get(cache_key)
        if cached is not None:
            logger.info("career_outlook cache hit for key=%s", cache_key)
            return cached

        search_query = f"{major} 专业就业前景 薪资 就业率 {location}".strip()
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
            logger.error("Career outlook search failed: %s", exc)
            return f"Error: 查询失败 — {exc}"

        results = data.get("organic", [])
        if not results:
            return f"未找到关于 **{major}** 专业的就业前景数据，请尝试其他关键词。"

        formatted = _format_results(results, major, location)
        cache_store.set(cache_key, formatted)
        return formatted


def _format_results(
    results: list[dict[str, Any]], major: str, location: str
) -> str:
    header = f"**{major}** 专业"
    if location:
        header += f"（{location}）"
    header += "就业前景参考信息：\n"

    lines = [header]
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        lines.append(f"{i}. **{title}**")
        if snippet:
            lines.append(f"   {snippet}")
        if link:
            lines.append(f"   [查看详情]({link})")
        lines.append("")
    return "\n".join(lines)
