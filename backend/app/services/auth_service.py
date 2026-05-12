"""Authentication-related service functions."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import http_401, http_409
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenPair


async def authenticate(db: AsyncSession, email: str, password: str) -> TokenPair:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise http_401("Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise http_401("Invalid credentials")

    return TokenPair(
        access_token=create_access_token(str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise http_409("Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise http_401(str(e))
    if payload.get("type") != "refresh":
        raise http_401("Not a refresh token")

    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise http_401("User not found")

    return TokenPair(
        access_token=create_access_token(str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
