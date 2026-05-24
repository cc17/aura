"""Skill registry — loads Industry Skills from DB, caches in memory."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import IndustrySkillModel, SkillRoleMappingModel

logger = logging.getLogger(__name__)

# skill_key → model snapshot dict
_cache: dict[str, dict] = {}

# (industry, role) → ordered list of skill_key strings (essential first, then recommended, optional)
_role_index: dict[tuple[str, str], list[str]] = {}

_PRIORITY_ORDER = {"essential": 0, "recommended": 1, "optional": 2}


def _to_dict(skill: IndustrySkillModel) -> dict:
    return {
        "id": skill.id,
        "skill_key": skill.skill_key,
        "industry": skill.industry,
        "role": skill.role,
        "scenario_name": skill.scenario_name,
        "description": skill.description,
        "tagline": skill.tagline,
        "trigger_keywords": skill.trigger_keywords or [],
        "prompt_template": skill.prompt_template,
        "starter_text": skill.starter_text,
        "input_schema": skill.input_schema,
        "example_output": skill.example_output,
        "is_universal": skill.is_universal,
        "layer": skill.layer,
        "enabled": skill.enabled,
        "display_order": skill.display_order,
    }


async def load_skills(session: AsyncSession) -> None:
    """Load all enabled skills and role mappings from DB into in-memory caches."""
    global _cache, _role_index

    result = await session.execute(
        select(IndustrySkillModel)
        .where(IndustrySkillModel.enabled == True)  # noqa: E712
        .order_by(IndustrySkillModel.display_order, IndustrySkillModel.id)
    )
    skills = result.scalars().all()
    _cache = {s.skill_key: _to_dict(s) for s in skills}

    # Load role mappings and build index
    mapping_result = await session.execute(
        select(SkillRoleMappingModel).order_by(
            SkillRoleMappingModel.industry,
            SkillRoleMappingModel.role,
            SkillRoleMappingModel.priority,
            SkillRoleMappingModel.display_order,
        )
    )
    mappings = mapping_result.scalars().all()

    index: dict[tuple[str, str], list[tuple[int, int, str]]] = {}
    for m in mappings:
        key = (m.industry, m.role)
        if key not in index:
            index[key] = []
        priority_rank = _PRIORITY_ORDER.get(m.priority, 9)
        # look up the skill key via the DB id
        skill_key = next(
            (sk for sk, sd in _cache.items() if sd["id"] == m.skill_id), None
        )
        if skill_key:
            index[key].append((priority_rank, m.display_order, skill_key))

    _role_index = {}
    for key, entries in index.items():
        entries.sort(key=lambda x: (x[0], x[1]))
        _role_index[key] = [e[2] for e in entries]

    logger.info(
        "Skill registry loaded: %d skills, %d role combos",
        len(_cache),
        len(_role_index),
    )


def get_skill(skill_key: str) -> dict | None:
    return _cache.get(skill_key)


def get_skill_by_id(skill_id: int) -> dict | None:
    return next((s for s in _cache.values() if s["id"] == skill_id), None)


def all_skills() -> list[dict]:
    """Return all enabled skills ordered by display_order."""
    return sorted(_cache.values(), key=lambda s: s["display_order"])


def list_skills(industry: str | None = None, role: str | None = None) -> list[dict]:
    """Return skills for the given industry/role using priority ordering from skill_role_mapping.

    Falls back to all enabled skills ordered by display_order when no mapping is found.
    """
    if industry and role:
        keys = _role_index.get((industry, role))
        if keys:
            result = [_cache[k] for k in keys if k in _cache]
            if result:
                return result

    # Fallback: all enabled skills in display_order
    return sorted(_cache.values(), key=lambda s: s["display_order"])


def find_by_keywords(text: str) -> dict | None:
    """Return first skill whose trigger_keywords appear in text."""
    text_lower = text.lower()
    for skill in sorted(_cache.values(), key=lambda s: s["display_order"]):
        for kw in skill["trigger_keywords"]:
            if kw.lower() in text_lower:
                return skill
    return None
