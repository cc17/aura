from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

import litellm


class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> Any: ...


class LiteLLMProvider:
    def __init__(self) -> None:
        from backend.config import settings

        self._api_base = settings.ark_api_base
        self._api_key = settings.ark_api_key

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "api_base": self._api_base,
            "api_key": self._api_key,
        }
        if tools:
            kwargs["tools"] = tools
        return await litellm.acompletion(**kwargs)

    async def stream_complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[Any]:
        response = await self.complete(messages, model, tools, stream=True)
        async for chunk in response:
            yield chunk
