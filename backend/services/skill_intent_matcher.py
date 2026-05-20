"""System 2: In-conversation intent trigger.

Pipeline per message:
  Hard rules (keyword fast path)
  → Embedding recall (cosine similarity, top-N)
  → Fine rank (semantic_sim×0.40 + profile_match×0.20 + quality×0.25 + affinity×0.15)
  → Confidence threshold (score < 0.55 → no trigger)
  → top-1 skill returned, or None

Graceful degradation: if AURA_EMBEDDING_MODEL is unset or embedding call fails,
falls back to keyword-only matching (existing behavior).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import SkillSignalModel, UserSkillAffinityModel
from backend.services.embedder import embed_text
from backend.services.skill_recommender import _parse_profile, _profile_score_norm
from backend.services.skill_registry import all_skills, find_by_keywords, get_skill

logger = logging.getLogger(__name__)

# Skill text embeddings computed at startup: skill_key → vector
_skill_embeddings: dict[str, list[float]] = {}

_RECALL_TOP_N = 5
_CONFIDENCE_THRESHOLD = 0.55

# Fine rank composite weights (must sum to 1.0)
_W_SIM = 0.40
_W_PROFILE = 0.20
_W_QUALITY = 0.25
_W_AFFINITY = 0.15


# ---------------------------------------------------------------------------
# Startup: pre-compute skill embeddings
# ---------------------------------------------------------------------------


async def build_skill_embeddings() -> None:
    """Embed all enabled skills and cache vectors in memory.

    Called at startup as a background task; safe to re-call after skill reload.
    No-op when AURA_EMBEDDING_MODEL is not configured.
    """
    global _skill_embeddings

    skills = all_skills()
    if not skills:
        return

    built: dict[str, list[float]] = {}
    for skill in skills:
        text = " ".join(
            filter(
                None,
                [
                    skill.get("scenario_name", ""),
                    skill.get("tagline") or "",
                    skill.get("description", ""),
                ],
            )
        )
        vec = await embed_text(text)
        if vec:
            built[skill["skill_key"]] = vec

    _skill_embeddings = built
    logger.info("Skill intent embeddings built: %d / %d skills", len(built), len(skills))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


async def _quality_scores(
    skill_ids: list[int], session: AsyncSession
) -> dict[int, float]:
    """Compute quality signal per skill from skill_signals (last 30 days).

    quality = pComplete×0.5 + pAdopt×0.4 - pAbandon×0.3
    Default when no data: 0.3 (neutral-low, avoids over-boosting unknown skills).
    """
    if not skill_ids:
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (
        await session.execute(
            select(
                SkillSignalModel.skill_id,
                func.count()
                .filter(SkillSignalModel.signal_type == "completed")
                .label("completed"),
                func.count()
                .filter(SkillSignalModel.signal_type == "abandoned")
                .label("abandoned"),
                func.count()
                .filter(
                    SkillSignalModel.signal_type.in_(
                        ["output_copied", "output_liked", "shared"]
                    )
                )
                .label("adopted"),
            )
            .where(
                SkillSignalModel.skill_id.in_(skill_ids),
                SkillSignalModel.created_at >= cutoff,
            )
            .group_by(SkillSignalModel.skill_id)
        )
    ).all()

    result: dict[int, float] = {}
    for row in rows:
        completed = row.completed or 0
        abandoned = row.abandoned or 0
        adopted = row.adopted or 0
        sessions = completed + abandoned
        p_complete = completed / sessions if sessions > 0 else 0.5
        p_abandon = abandoned / sessions if sessions > 0 else 0.0
        p_adopt = min(adopted / completed, 1.0) if completed > 0 else 0.0
        result[row.skill_id] = (
            p_complete * 0.5 + p_adopt * 0.4 - p_abandon * 0.3
        )
    return result


async def _affinity_scores(
    user_id: int, skill_ids: list[int], session: AsyncSession
) -> dict[int, float]:
    if not skill_ids:
        return {}
    rows = (
        await session.execute(
            select(
                UserSkillAffinityModel.skill_id,
                UserSkillAffinityModel.affinity_score,
            )
            .where(
                UserSkillAffinityModel.user_id == user_id,
                UserSkillAffinityModel.skill_id.in_(skill_ids),
            )
        )
    ).all()
    return {row.skill_id: float(row.affinity_score) for row in rows}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def match_intent(
    message: str,
    user_id: int,
    profile: dict,
    session: AsyncSession,
) -> dict | None:
    """Run the full System 2 pipeline for one user message.

    Returns the best-matching skill dict, or None if nothing passes the
    confidence threshold.
    """

    # Stage 0: Hard rules fast path — preserve explicit keyword config
    hard = find_by_keywords(message)
    if hard:
        logger.debug("Intent: hard-rule match skill=%s", hard["skill_key"])
        return hard

    # Graceful degradation: no embeddings → keyword-only mode
    if not _skill_embeddings:
        return None

    # Stage 1: Embed the user message
    msg_vec = await embed_text(message)
    if msg_vec is None:
        return None

    # Stage 2: Embedding recall — cosine similarity, top-N
    sims: list[tuple[float, dict]] = []
    for skill_key, skill_vec in _skill_embeddings.items():
        skill = get_skill(skill_key)
        if skill:
            sims.append((_cosine(msg_vec, skill_vec), skill))
    sims.sort(key=lambda x: x[0], reverse=True)
    candidates = sims[:_RECALL_TOP_N]

    if not candidates:
        return None

    # Stage 3: Fine rank
    industry, role, pain_points = _parse_profile(profile)
    skill_ids = [s["id"] for _, s in candidates]

    quality_map = await _quality_scores(skill_ids, session)
    affinity_map = await _affinity_scores(user_id, skill_ids, session)

    scored: list[tuple[float, dict]] = []
    for sim, skill in candidates:
        sid = skill["id"]
        profile_n = _profile_score_norm(skill, industry, role, pain_points)
        quality = quality_map.get(sid, 0.3)
        affinity = affinity_map.get(sid, 0.5)

        composite = (
            sim * _W_SIM
            + profile_n * _W_PROFILE
            + quality * _W_QUALITY
            + affinity * _W_AFFINITY
        )
        scored.append((composite, skill))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_skill = scored[0]

    # Stage 4: Confidence threshold
    if best_score < _CONFIDENCE_THRESHOLD:
        logger.debug(
            "Intent: below threshold skill=%s score=%.3f",
            best_skill["skill_key"],
            best_score,
        )
        return None

    logger.debug(
        "Intent: matched skill=%s score=%.3f",
        best_skill["skill_key"],
        best_score,
    )
    return best_skill
