"""Application-level KV cache for LLM calls.

Wraps LangChain ainvoke with deterministic hash-based caching so that
identical (model, messages, tools) triples skip the network round-trip.

Why application-level rather than provider-level:
  The doubao/Ark endpoint does not expose Anthropic-style cache_control.
  We compensate by caching the serialised response in CacheStore.
  Cache hit rate is highest for the supervisor routing call (same system
  prompt + short last message) and the reflection scoring call.

The cache is intentionally disabled for streaming calls — chunked
responses are cached only at the non-streaming layer used by the
supervisor and reflection nodes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from backend.observability import trace
from backend.storage.cache_store import CacheStore, cache_store as _default_store

logger = logging.getLogger(__name__)


def _serialize_messages(messages: list[BaseMessage]) -> str:
    """Stable JSON representation of a message list."""
    parts = []
    for m in messages:
        role = getattr(m, "type", "unknown")
        content = m.content if isinstance(m.content, str) else json.dumps(m.content)
        parts.append(f"{role}:{content}")
    return "\n---\n".join(parts)


def _make_llm_key(prefix: str, model: str, messages: list[BaseMessage]) -> str:
    payload = f"{model}\n{_serialize_messages(messages)}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"llm:{prefix}:{digest}"


class LLMKVCache:
    """Wraps a LangChain ChatModel with content-addressed response caching.

    Usage::

        cache = LLMKVCache(prefix="supervisor", ttl=3600)
        response = await cache.ainvoke(llm, messages)
    """

    def __init__(
        self,
        prefix: str = "default",
        ttl: int = 3600,
        store: CacheStore | None = None,
    ) -> None:
        self._prefix = prefix
        self._ttl = ttl
        self._store = store or _default_store

    async def ainvoke(self, llm: Any, messages: list[BaseMessage]) -> AIMessage:
        model_name: str = getattr(llm, "model", "") or getattr(llm, "model_name", "") or "?"
        key = _make_llm_key(self._prefix, model_name, messages)

        cached = self._store.get(key)
        if cached is not None:
            logger.debug("LLM cache HIT  prefix=%s key=%s…", self._prefix, key[:8])
            trace("kv_cache_hit", prefix=self._prefix, key=key[:8])
            return AIMessage(content=cached)

        logger.debug("LLM cache MISS prefix=%s key=%s…", self._prefix, key[:8])
        t0 = __import__("time").perf_counter()
        response: AIMessage = await llm.ainvoke(messages)
        elapsed = round((__import__("time").perf_counter() - t0) * 1000, 1)
        trace("kv_cache_miss", prefix=self._prefix, key=key[:8], llm_ms=elapsed)
        if isinstance(response.content, str) and response.content:
            self._store.set(key, response.content, ttl=self._ttl)

        return response


# Shared cache instances — one per hot path
supervisor_cache = LLMKVCache(prefix="supervisor", ttl=300)   # 5 min (routing is cheap)
reflection_cache = LLMKVCache(prefix="reflection", ttl=600)   # 10 min
