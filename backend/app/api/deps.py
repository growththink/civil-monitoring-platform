"""FastAPI dependencies — auth, RBAC, DB session."""
import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import http_401, http_403
from app.core.security import decode_token, hash_api_key
from app.models.device import Device
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise http_401("Missing token")
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise http_401(str(e))

    if payload.get("type") != "access":
        raise http_401("Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise http_401("Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise http_401("Invalid subject in token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise http_401("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Returns a dependency that enforces role membership."""
    async def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise http_403("Insufficient permissions")
        return user
    return _checker


require_admin = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)
require_operator = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.OPERATOR)


async def get_device_by_api_key(
    db: DBSession,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Device:
    """Authenticate a device by API key (used for HTTP ingestion)."""
    if not x_api_key:
        raise http_401("Missing X-API-Key header")
    digest = hash_api_key(x_api_key)
    result = await db.execute(select(Device).where(Device.api_key_hash == digest))
    device = result.scalar_one_or_none()
    if not device:
        raise http_401("Invalid API key")
    return device


AuthedDevice = Annotated[Device, Depends(get_device_by_api_key)]
