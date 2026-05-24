"""Async SQLAlchemy engine + session factory."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
# Ensure local sqlite dir exists
if settings.database_url.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)

engine = create_async_engine(settings.database_url, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    # Import models so they register with Base.metadata
    from app.models import agent, message, run, workflow  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s
