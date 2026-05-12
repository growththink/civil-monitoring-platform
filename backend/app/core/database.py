"""Database engine and session management (async SQLAlchemy)."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Common base for all ORM models."""
    pass


def pg_enum(enum_cls, *, name: str):
    # values_callable: store python-enum .value (lowercase) in DB, not .name
    # create_type=False: enums are managed by alembic, not SQLAlchemy metadata
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda obj: [e.value for e in obj],
        create_type=False,
    )


engine = create_async_engine(
    settings.database_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Use inside background workers / scripts."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
