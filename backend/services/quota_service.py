"""Quota service — per-user billing quota check, auto-reset, and increment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import UserQuotaModel

# CST = UTC+8
CST = timezone(timedelta(hours=8))

QUOTA_LIMITS: dict[str, int] = {
    "free": 20,    # per day
    "pro": 1000,   # per month
    "max": -1,     # unlimited
}


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def _cst_now() -> datetime:
    return datetime.now(CST)


def _free_period(now: datetime) -> tuple[datetime, datetime]:
    """Today 00:00 CST → tomorrow 00:00 CST."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _monthly_period(now: datetime) -> tuple[datetime, datetime]:
    """First of this month 00:00 CST → first of next month 00:00 CST."""
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start, end


def _period_for_plan(plan: str, now: datetime) -> tuple[datetime, datetime]:
    if plan == "free":
        return _free_period(now)
    return _monthly_period(now)


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

async def get_or_create(user_id: int, session: AsyncSession) -> UserQuotaModel:
    """Return the quota row for user_id, creating a Free one if absent."""
    result = await session.execute(
        select(UserQuotaModel).where(UserQuotaModel.user_id == user_id)
    )
    quota = result.scalar_one_or_none()
    if quota is None:
        now = _cst_now()
        start, end = _free_period(now)
        quota = UserQuotaModel(
            user_id=user_id,
            plan="free",
            usage_count=0,
            period_start=start,
            period_end=end,
        )
        session.add(quota)
        await session.flush()
    return quota


def _maybe_reset(quota: UserQuotaModel, now: datetime) -> None:
    """If the current period has expired, reset usage_count and advance the period."""
    if now >= quota.period_end:
        start, end = _period_for_plan(quota.plan, now)
        quota.period_start = start
        quota.period_end = end
        quota.usage_count = 0


async def check_and_increment(user_id: int, session: AsyncSession) -> None:
    """Check quota and increment usage by 1.

    Raises HTTP 402 with a JSON body if the user is over their limit.
    No-ops for 'max' plan users.
    """
    quota = await get_or_create(user_id, session)
    now = _cst_now()
    _maybe_reset(quota, now)

    limit = QUOTA_LIMITS[quota.plan]
    if limit == -1:
        # Unlimited plan — still increment for analytics
        quota.usage_count += 1
        return

    if quota.usage_count >= limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "quota_exceeded",
                "plan": quota.plan,
                "usage_count": quota.usage_count,
                "quota_limit": limit,
                "reset_at": quota.period_end.isoformat(),
            },
        )

    quota.usage_count += 1


async def get_quota_info(user_id: int, session: AsyncSession) -> dict:
    """Return serialisable quota info for the current user."""
    quota = await get_or_create(user_id, session)
    now = _cst_now()
    _maybe_reset(quota, now)

    limit = QUOTA_LIMITS[quota.plan]
    remaining = -1 if limit == -1 else max(0, limit - quota.usage_count)

    return {
        "plan": quota.plan,
        "usage_count": quota.usage_count,
        "quota_limit": limit,
        "remaining": remaining,
        "period_start": quota.period_start.isoformat(),
        "reset_at": quota.period_end.isoformat(),
        "plan_expires_at": quota.plan_expires_at.isoformat() if quota.plan_expires_at else None,
    }
