"""Lightweight structured tracer — no external dependencies.

Every trace event is emitted as a JSON line to the `aura.trace` logger.
Route it to a dedicated file handler in your logging config if needed.

Usage:
    trace("kv_cache.hit", prefix="supervisor", latency_ms=12, conv_id=cid)

    async with trace_span("tool.call", conv_id=cid, tool="web_search") as span:
        result = await do_work()
        span["tokens"] = len(result)  # attach extra fields before close
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

_logger = logging.getLogger("aura.trace")

# In-process counters for the /api/stats endpoint
_stats: dict[str, int] = {
    "requests_total": 0,
    "requests_completed": 0,
    "requests_cancelled": 0,
    "kv_hit_supervisor": 0,
    "kv_miss_supervisor": 0,
    "kv_hit_reflection": 0,
    "kv_miss_reflection": 0,
    "intent_fast_path": 0,
    "intent_llm_path": 0,
    "tool_calls_total": 0,
    "tool_calls_error": 0,
    "reflection_loops_total": 0,
    "reflection_retries": 0,
}


def trace(event: str, **fields: Any) -> None:
    """Emit one structured trace event."""
    payload = {"event": event, "ts": time.time(), **fields}
    _logger.info(json.dumps(payload, ensure_ascii=False, default=str))

    # Update in-process counters
    key = event.replace(".", "_")
    if key in _stats:
        _stats[key] += 1
    # Special counter aliases
    _counter_aliases = {
        "kv_cache_hit":  lambda f: f"kv_hit_{f.get('prefix', '')}",
        "kv_cache_miss": lambda f: f"kv_miss_{f.get('prefix', '')}",
        "request_start": lambda _: "requests_total",
        "request_done":  lambda _: "requests_completed",
        "request_cancel": lambda _: "requests_cancelled",
        "tool_call_start": lambda _: "tool_calls_total",
        "tool_call_error": lambda _: "tool_calls_error",
        "reflection_done": lambda f: "reflection_retries" if not f.get("approved") else None,
    }
    if event in _counter_aliases:
        counter_key = _counter_aliases[event](fields)
        if counter_key and counter_key in _stats:
            _stats[counter_key] += 1


@asynccontextmanager
async def trace_span(
    event: str, **fields: Any
) -> AsyncGenerator[dict[str, Any], None]:
    """Async context manager that records start + end with elapsed_ms.

    Extra fields can be written into the yielded dict before the span closes::

        async with trace_span("tool.call", tool="web_search") as span:
            result = await tool_fn()
            span["result_len"] = len(result)
    """
    extra: dict[str, Any] = {}
    t0 = time.perf_counter()
    try:
        yield extra
    finally:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        trace(event, elapsed_ms=elapsed, **fields, **extra)


def get_stats() -> dict[str, int]:
    return dict(_stats)
