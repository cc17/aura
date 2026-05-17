"""Database engine creation and session management."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings
from backend.memory.models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=settings.debug)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncSession:
    """Get a new async session (caller must use `async with`)."""
    factory = get_session_factory()
    return factory()


async def init_database() -> None:
    """Create all tables. Safe to call repeatedly (uses CREATE IF NOT EXISTS)."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Enable pgvector extension (required for user_memories.embedding column)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent column additions for tables created before Phase 2.
        # ALTER TABLE … ADD COLUMN IF NOT EXISTS is safe to run repeatedly.
        await conn.execute(text(
            "ALTER TABLE conversations "
            "ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_conversations_user_id "
            "ON conversations(user_id)"
        ))
        # IVFFlat index for approximate nearest-neighbour memory retrieval.
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_memories_embedding "
            "ON user_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        ))


async def close_database() -> None:
    """Dispose the engine connection pool."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
