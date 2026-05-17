"""Embedding service — wraps LiteLLM embedding call.

Graceful degradation: returns None if embedding_model is not configured or call fails.
Memories are still stored as text; retrieval falls back to recency ordering.
"""

from __future__ import annotations

import logging

from backend.config import settings

logger = logging.getLogger(__name__)


async def embed_text(text: str) -> list[float] | None:
    """Return an embedding vector, or None if unavailable."""
    if not settings.embedding_model:
        return None
    try:
        import litellm

        resp = await litellm.aembedding(
            model=settings.embedding_model,
            input=[text],
            api_key=settings.ark_api_key,
            api_base=settings.ark_api_base,
        )
        return resp.data[0]["embedding"]
    except Exception:
        logger.warning("embed_text failed (non-fatal)", exc_info=True)
        return None
