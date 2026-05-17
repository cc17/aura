"""Tests for the LLM KV cache layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.llm.kv_cache import LLMKVCache
from backend.storage.cache_store import CacheStore


def _make_llm(response_text: str) -> MagicMock:
    llm = MagicMock()
    llm.model = "test-model"
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=response_text))
    return llm


@pytest.mark.asyncio
async def test_cache_miss_calls_llm():
    store = CacheStore()
    cache = LLMKVCache(prefix="test", ttl=60, store=store)
    llm = _make_llm("hello")

    messages = [HumanMessage(content="hi")]
    result = await cache.ainvoke(llm, messages)

    assert result.content == "hello"
    llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_skips_llm():
    store = CacheStore()
    cache = LLMKVCache(prefix="test", ttl=60, store=store)
    llm = _make_llm("hello")

    messages = [HumanMessage(content="hi")]
    await cache.ainvoke(llm, messages)  # first call — populates cache
    result = await cache.ainvoke(llm, messages)  # second call — should hit cache

    assert result.content == "hello"
    llm.ainvoke.assert_called_once()  # only ONE real LLM call


@pytest.mark.asyncio
async def test_different_messages_different_keys():
    store = CacheStore()
    cache = LLMKVCache(prefix="test", ttl=60, store=store)
    llm1 = _make_llm("response1")
    llm2 = _make_llm("response2")

    r1 = await cache.ainvoke(llm1, [HumanMessage(content="question A")])
    r2 = await cache.ainvoke(llm2, [HumanMessage(content="question B")])

    assert r1.content == "response1"
    assert r2.content == "response2"


@pytest.mark.asyncio
async def test_empty_response_not_cached():
    store = CacheStore()
    cache = LLMKVCache(prefix="test", ttl=60, store=store)
    llm = _make_llm("")  # empty response

    messages = [HumanMessage(content="hi")]
    await cache.ainvoke(llm, messages)
    await cache.ainvoke(llm, messages)

    # Should call LLM twice since empty response isn't cached
    assert llm.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_system_message_included_in_key():
    store = CacheStore()
    cache = LLMKVCache(prefix="test", ttl=60, store=store)
    llm = _make_llm("answer")

    msgs_with_system = [SystemMessage(content="You are helpful"), HumanMessage(content="hi")]
    msgs_without = [HumanMessage(content="hi")]

    await cache.ainvoke(llm, msgs_with_system)
    await cache.ainvoke(llm, msgs_without)

    # Different inputs → 2 LLM calls
    assert llm.ainvoke.call_count == 2
