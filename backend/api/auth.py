"""Authentication endpoints: register, login, me."""

from __future__ import annotations

from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import (
    create_access_token,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from backend.memory.models import UserModel
from backend.services.quota_service import get_or_create

router = APIRouter(prefix="/auth")

# Simple in-memory sliding-window rate limiter (per IP)
_auth_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW = 60  # seconds
_MAX_LOGIN = 10    # attempts per minute per IP
_MAX_REGISTER = 5  # registrations per minute per IP


def _check_rate(ip: str, max_attempts: int) -> None:
    now = time()
    window = _auth_attempts[ip]
    _auth_attempts[ip] = [t for t in window if now - t < _RATE_WINDOW]
    if len(_auth_attempts[ip]) >= max_attempts:
        raise HTTPException(status_code=429, detail="Too many requests, please try again later")
    _auth_attempts[ip].append(now)


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("用户名长度须在 2-50 字符之间")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v


@router.post("/register", status_code=201)
async def register(request: Request, body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    _check_rate(request.client.host, _MAX_REGISTER)
    existing = await session.execute(
        select(UserModel).where(UserModel.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = UserModel(
        username=body.username,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    await session.flush()          # get user.id before quota creation
    await get_or_create(user.id, session)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "onboarded": user.onboarded,
        },
    }


@router.post("/login")
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    _check_rate(request.client.host, _MAX_LOGIN)
    result = await session.execute(
        select(UserModel).where(UserModel.username == form.username)
    )
    user = result.scalar_one_or_none()
    # Always run bcrypt to prevent username enumeration via timing difference
    _DUMMY_HASH = "$2b$12$dummy.hash.that.never.matches.any.real.password.padding"
    password_ok = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "onboarded": user.onboarded,
        },
    }


@router.get("/me")
async def me(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "onboarded": current_user.onboarded,
        "profile": current_user.profile,
    }
