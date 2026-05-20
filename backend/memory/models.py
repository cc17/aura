"""SQLAlchemy ORM models for conversations, messages, users, memories, and skills."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    # user_id nullable for backward-compat; new conversations always have a user
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_through_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[MessageModel]] = relationship(
        back_populates="conversation", order_by="MessageModel.idx", lazy="selectin"
    )
    summaries: Mapped[list[ConversationSummaryModel]] = relationship(
        back_populates="conversation", order_by="ConversationSummaryModel.created_at"
    )


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conv_idx", "conversation_id", "idx"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("conversations.id"), nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[ConversationModel] = relationship(back_populates="messages")


class ConversationSummaryModel(Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("conversations.id"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    covers_through_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[ConversationModel] = relationship(back_populates="summaries")


class UserFactModel(Base):
    """Cross-conversation user facts extracted from chat history."""

    __tablename__ = "user_facts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_conversation_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# User / Auth
# ---------------------------------------------------------------------------


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # profile stores dynamic user attributes with confidence scores (see ARCHITECTURE.md §2.1)
    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    profile_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    memories: Mapped[list[UserMemoryModel]] = relationship(
        back_populates="user", lazy="noload"
    )
    suggestions: Mapped[list[UserSuggestionModel]] = relationship(
        back_populates="user", lazy="noload"
    )
    skill_executions: Mapped[list[SkillExecutionModel]] = relationship(
        back_populates="user", lazy="noload"
    )
    quota: Mapped[UserQuotaModel | None] = relationship(
        back_populates="user", lazy="noload", uselist=False
    )


# ---------------------------------------------------------------------------
# Long-term memory (per-user, vector-indexed)
# ---------------------------------------------------------------------------

# Embedding dimension: 1536 for text-embedding-3; change to 1024 for bge-large-zh.
_EMBEDDING_DIM = 1536


class UserMemoryModel(Base):
    __tablename__ = "user_memories"
    __table_args__ = (
        Index("idx_memories_user", "user_id"),
        Index("idx_memories_category", "user_id", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # category: fact | preference | goal | context
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # importance 1–10; 9-10=identity info, 7-8=key relations, 4-6=preferences, 1-3=transient
    importance: Mapped[int] = mapped_column(SmallInteger, default=5)
    source_message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(_EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    # expires_at: NULL = permanent; set for goal-type memories with a known deadline
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserModel] = relationship(back_populates="memories")


# ---------------------------------------------------------------------------
# Industry Skills (database-driven, not hardcoded)
# ---------------------------------------------------------------------------


class IndustrySkillModel(Base):
    __tablename__ = "industry_skills"
    __table_args__ = (
        Index("idx_skills_industry_role", "industry", "role", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_keywords: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    example_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    tagline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    is_universal: Mapped[bool] = mapped_column(Boolean, default=False)
    layer: Mapped[int] = mapped_column(SmallInteger, default=1)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    experiment_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    executions: Mapped[list[SkillExecutionModel]] = relationship(
        back_populates="skill", lazy="noload"
    )
    role_mappings: Mapped[list[SkillRoleMappingModel]] = relationship(
        back_populates="skill", lazy="noload"
    )



# ---------------------------------------------------------------------------
# Skill ↔ Industry/Role many-to-many mapping
# ---------------------------------------------------------------------------


class SkillRoleMappingModel(Base):
    __tablename__ = "skill_role_mapping"
    __table_args__ = (
        UniqueConstraint("skill_id", "industry", "role", name="uq_skill_role_mapping"),
        Index("idx_skill_role_mapping_lookup", "industry", "role", "priority", "display_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry_skills.id", ondelete="CASCADE"), nullable=False)
    industry: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    skill: Mapped[IndustrySkillModel] = relationship(back_populates="role_mappings")


# ---------------------------------------------------------------------------
# User billing quota
# ---------------------------------------------------------------------------


class UserQuotaModel(Base):
    __tablename__ = "user_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped[UserModel] = relationship(back_populates="quota")


# ---------------------------------------------------------------------------
# User skill library
# ---------------------------------------------------------------------------


class UserSkillModel(Base):
    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
        Index("idx_user_skills_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("industry_skills.id", ondelete="CASCADE"), nullable=False
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Per-message suggestions ("你可能还想…")
# ---------------------------------------------------------------------------


class UserSuggestionModel(Base):
    __tablename__ = "user_suggestions"
    __table_args__ = (
        Index("idx_suggestions_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    # message_id references the assistant message that triggered suggestion generation
    message_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # suggestions: [{"type": "question"|"skill", "text": "...", "skill_key": null|"..."}]
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    clicked_index: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[UserModel] = relationship(back_populates="suggestions")


# ---------------------------------------------------------------------------
# Skill execution log
# ---------------------------------------------------------------------------


class SkillExecutionModel(Base):
    __tablename__ = "skill_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry_skills.id"), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # status: pending | success | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[UserModel] = relationship(back_populates="skill_executions")
    skill: Mapped[IndustrySkillModel] = relationship(back_populates="executions")


# ---------------------------------------------------------------------------
# Recommendation pipeline: behavior signals + per-user affinity
# ---------------------------------------------------------------------------


class SkillSignalModel(Base):
    """Raw behavior events: impression, click, execution outcomes, etc."""

    __tablename__ = "skill_signals"
    __table_args__ = (
        Index("idx_skill_signals_user_time", "user_id", "created_at"),
        Index("idx_skill_signals_skill_type", "skill_id", "signal_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry_skills.id"), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UserSkillAffinityModel(Base):
    """Per-user skill affinity scores, updated by the trigger on skill_executions."""

    __tablename__ = "user_skill_affinity"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill_affinity"),
        Index("idx_user_skill_affinity_user_score", "user_id", "affinity_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry_skills.id"), nullable=False)
    affinity_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0.5)
    total_uses: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_recommended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation_cool_down_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
