"""URL scraper tool — fetches a URL and returns cleaned plain text.

Uses httpx for the HTTP request and BeautifulSoup for HTML parsing.
Strips nav/footer/ads boilerplate, limits output to 4 000 chars.
Results are cached by URL for 30 minutes.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

_CACHE_TTL = 1800  # 30 min
_MAX_CHARS = 4_000

_BOILERPLATE_TAGS = {"nav", "footer", "header", "aside", "script", "style", "noscript", "iframe"}


def _extract_text(html: str, url: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # Remove boilerplate elements
    for tag in soup.find_all(_BOILERPLATE_TAGS):
        tag.decompose()

    # Try main content containers first
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|article|post|entry|body", re.I))
        or soup.body
    )

    if main is None:
        return f"Could not extract content from {url}"

    text = main.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:_MAX_CHARS]


class UrlScraperTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="url_scraper",
            description=(
                "Fetch a web page and return its plain-text content (up to 4000 characters). "
                "Use this to read the full content of URLs found via web_search."
            ),
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Full URL to fetch (must start with http:// or https://)",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        url: str = kwargs.get("url", "").strip()

        if not url:
            return "Error: url is required."
        if not url.startswith(("http://", "https://")):
            return "Error: url must start with http:// or https://"

        cache_key = cache_store.make_key("url_scraper", url)
        cached = cache_store.get(cache_key)
        if cached:
            logger.debug("url_scraper cache HIT  url=%s", url[:80])
            return cached

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AuraBot/1.0; +https://aura.ai)"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type and "text" not in content_type:
                    return f"Skipped non-text content ({content_type}) at {url}"
                html = resp.text
        except httpx.HTTPError as exc:
            logger.warning("url_scraper fetch failed: %s", exc)
            return f"Error: could not fetch {url} — {exc}"

        text = _extract_text(html, url)
        result = f"[Content from {url}]\n\n{text}"
        cache_store.set(cache_key, result, ttl=_CACHE_TTL)
        return result
