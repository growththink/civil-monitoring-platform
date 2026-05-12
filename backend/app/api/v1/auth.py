"""Auth endpoints: login, refresh, register (admin), me."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DBSession, require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: DBSession):
    return await auth_service.authenticate(db, body.email, body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DBSession):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    return await auth_service.register_user(db, body)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
