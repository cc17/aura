"""Retrieve relevant long-term memories for a user given a query string."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import UserMemoryModel
from backend.services.embedder import embed_text

logger = logging.getLogger(__name__)

# Score = importance × IMPORTANCE_WEIGHT + similarity × SIMILARITY_WEIGHT
_IMPORTANCE_WEIGHT = 0.3
_SIMILARITY_WEIGHT = 0.7


async def retrieve_memories(
    user_id: int,
    query: str,
    session: AsyncSession,
    top_k: int = 5,
) -> list[str]:
    """Return up to top_k memory strings most relevant to the query.

    Falls back to most-recent memories when embeddings are unavailable.
    Updates last_accessed_at and access_count for retrieved rows.
    """
    query_vec = await embed_text(query)

    if query_vec is not None:
        rows = await _retrieve_by_vector(user_id, query_vec, session, top_k)
    else:
        rows = await _retrieve_by_recency(user_id, session, top_k)

    if not rows:
        return []

    ids = [r.id for r in rows]
    now = datetime.now(timezone.utc)
    await session.execute(
        update(UserMemoryModel)
        .where(UserMemoryModel.id.in_(ids))
        .values(last_accessed_at=now, access_count=UserMemoryModel.access_count + 1)
    )

    return [r.content for r in rows]


async def _retrieve_by_vector(
    user_id: int,
    query_vec: list[float],
    session: AsyncSession,
    top_k: int,
) -> list[UserMemoryModel]:
    """Cosine-similarity search via pgvector, re-ranked with importance weight."""
    from pgvector.sqlalchemy import Vector
    from sqlalchemy import cast, func, literal_column

    similarity_expr = (
        1 - func.cosine_distance(
            UserMemoryModel.embedding,
            cast(str(query_vec), Vector(len(query_vec))),
        )
    ).label("similarity")

    score_expr = (
        UserMemoryModel.importance * _IMPORTANCE_WEIGHT
        + similarity_expr * _SIMILARITY_WEIGHT * 10  # normalise to 0-10 scale
    ).label("score")

    stmt = (
        select(UserMemoryModel)
        .where(
            UserMemoryModel.user_id == user_id,
            UserMemoryModel.embedding.is_not(None),
        )
        .order_by(score_expr.desc())
        .limit(top_k)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _retrieve_by_recency(
    user_id: int,
    session: AsyncSession,
    top_k: int,
) -> list[UserMemoryModel]:
    """Fallback: return the most important/recent memories."""
    stmt = (
        select(UserMemoryModel)
        .where(UserMemoryModel.user_id == user_id)
        .order_by(
            UserMemoryModel.importance.desc(),
            UserMemoryModel.created_at.desc(),
        )
        .limit(top_k)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
