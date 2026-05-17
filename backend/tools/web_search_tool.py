"""Web search tool — wraps Serper API for research queries.

Returns a structured result set with title, snippet and URL for each hit.
Results are cached by query string to avoid redundant API calls.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/search"
_CACHE_TTL = 1800  # 30 minutes for search results


class WebSearchTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description=(
                "Search the web for information on any topic. "
                "Returns top results with title, snippet and URL. "
                "Use this to gather current information, news, or research data."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query string",
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results to return (1–10, default 8)",
                    required=False,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Language/region hint: 'zh-cn' (default), 'en', etc.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        query: str = kwargs.get("query", "").strip()
        num: int = min(10, max(1, int(kwargs.get("num_results") or 8)))
        lang: str = kwargs.get("language") or "zh-cn"

        if not query:
            return "Error: query is required."

        if not settings.serper_api_key:
            return (
                "Error: Serper API key not configured. "
                "Set AURA_SERPER_API_KEY in your environment."
            )

        cache_key = cache_store.make_key("web_search", query, str(num), lang)
        cached = cache_store.get(cache_key)
        if cached:
            logger.debug("web_search cache HIT  query=%r", query[:60])
            return cached

        payload: dict[str, Any] = {"q": query, "num": num}
        if lang.startswith("zh"):
            payload.update({"gl": "cn", "hl": "zh-cn"})
        else:
            payload.update({"gl": "us", "hl": "en"})

        headers = {"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(_SERPER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Serper request failed: %s", exc)
            return f"Error: Web search failed — {exc}"

        results = data.get("organic", [])
        if not results:
            return f"No results found for: {query}"

        lines = [f"Search results for: **{query}**\n"]
        for i, item in enumerate(results[:num], 1):
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            lines.append(f"{i}. **{title}**")
            if snippet:
                lines.append(f"   {snippet}")
            if link:
                lines.append(f"   URL: {link}")
            lines.append("")

        formatted = "\n".join(lines)
        cache_store.set(cache_key, formatted, ttl=_CACHE_TTL)
        return formatted
