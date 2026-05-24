"""JWT authentication utilities and FastAPI dependencies."""

from __future__ import annotations

import bcrypt
import hmac
from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncGenerator

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.memory.database import get_session_factory
from backend.memory.models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=_ALGORITHM,
    )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> UserModel:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise credentials_exc

    user = await session.get(UserModel, user_id)
    if user is None:
        raise credentials_exc
    return user


async def require_admin(authorization: Annotated[str, Header(alias="authorization")] = "") -> None:
    """FastAPI dependency: requires a valid AURA_ADMIN_TOKEN in the Authorization header."""
    token = settings.admin_token
    if not token:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=403, detail="Invalid admin token")
