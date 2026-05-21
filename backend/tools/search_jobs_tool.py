"""Search jobs tool — uses Serper API to find matching job postings."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/search"


class SearchJobsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_jobs",
            description=(
                "Search for job postings matching the given query. "
                "Use this after modifying a resume to recommend relevant positions."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Job search keywords, e.g. '字节跳动 后端工程师'",
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="Preferred job location, e.g. '北京'",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        query: str = kwargs.get("query", "")
        location: str = kwargs.get("location") or ""

        if not query:
            return "Error: query parameter is required."

        if not settings.serper_api_key:
            return (
                "Error: Serper API key is not configured. "
                "Please set AURA_SERPER_API_KEY in your environment."
            )

        cache_key = cache_store.make_key(query, location)
        cached = cache_store.get(cache_key)
        if cached is not None:
            logger.info("search_jobs cache hit for key=%s", cache_key)
            return cached

        # Detect language: if query is mostly ASCII, search globally; otherwise target China
        is_english = sum(c.isascii() for c in query) / max(len(query), 1) > 0.8
        if is_english:
            search_query = f"{query} {location} jobs hiring".strip()
            gl, hl = "us", "en"
        else:
            search_query = f"{query} {location} 招聘".strip()
            gl, hl = "cn", "zh-cn"

        payload = {
            "q": search_query,
            "gl": gl,
            "hl": hl,
            "num": 10,
        }
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
            logger.error("Serper API request failed: %s", exc)
            return f"Error: Failed to search for jobs — {exc}"

        results = data.get("organic", [])
        if not results:
            return "No matching job postings found. Try different keywords."

        formatted = _format_results(results)
        cache_store.set(cache_key, formatted)
        logger.info("search_jobs cached result for key=%s", cache_key)
        return formatted


def _format_results(results: list[dict[str, Any]]) -> str:
    lines = ["Matching positions found:\n"]
    for i, item in enumerate(results, 1):
        title = item.get("title", "Unknown Position")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        lines.append(f"{i}. **{title}**")
        if snippet:
            lines.append(f"   {snippet}")
        if link:
            lines.append(f"   [View posting]({link})")
        lines.append("")
    return "\n".join(lines)
