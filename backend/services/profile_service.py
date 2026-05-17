"""User profile CRUD — reading and updating the JSONB profile field."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import UserModel


async def get_profile(session: AsyncSession, user_id: int) -> dict | None:
    user = await session.get(UserModel, user_id)
    return user.profile if user else None


async def update_profile(
    session: AsyncSession,
    user_id: int,
    updates: dict,
    *,
    confidence: float = 1.0,
) -> dict:
    """Merge updates into the user's profile with confidence scores.

    Each top-level scalar field is stored as:
      {"value": ..., "confidence": ..., "updated_at": "..."}

    List fields (pain_points, etc.) and dict fields (style_preference, context_facts)
    are replaced directly.

    confidence=1.0 is used for explicit user input (onboarding, manual edit).
    """
    user = await session.get(UserModel, user_id)
    if user is None:
        return {}

    profile: dict = dict(user.profile or {})
    now_iso = datetime.now(timezone.utc).isoformat()

    for key, value in updates.items():
        if isinstance(value, (list, dict)):
            profile[key] = value
        else:
            existing = profile.get(key, {})
            if isinstance(existing, dict):
                new_confidence = min(1.0, existing.get("confidence", 0) + 0.2) if confidence < 1.0 else 1.0
            else:
                new_confidence = confidence
            profile[key] = {"value": value, "confidence": new_confidence, "updated_at": now_iso}

    user.profile = profile
    user.profile_updated_at = datetime.now(timezone.utc)
    await session.flush()
    return profile


async def mark_onboarded(session: AsyncSession, user_id: int) -> None:
    user = await session.get(UserModel, user_id)
    if user:
        user.onboarded = True
        await session.flush()
