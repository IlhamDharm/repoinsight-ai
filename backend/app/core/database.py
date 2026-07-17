import asyncio
import sys
import weakref
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_engine_by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncEngine] = weakref.WeakKeyDictionary()
_session_factory_by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, async_sessionmaker[AsyncSession]] = weakref.WeakKeyDictionary()


def init_database() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    loop = asyncio.get_running_loop()

    if loop in _engine_by_loop and loop in _session_factory_by_loop:
        return _engine_by_loop[loop], _session_factory_by_loop[loop]

    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    _engine_by_loop[loop] = engine
    _session_factory_by_loop[loop] = session_factory
    return engine, session_factory


def get_engine() -> AsyncEngine:
    engine, _ = init_database()
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    _, session_factory = init_database()
    return session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def check_database_health() -> dict[str, Any]:
    engine = get_engine()
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        scalar = result.scalar_one()

    return {
        "status": "ok" if scalar == 1 else "degraded",
        "database": "postgresql",
        "dialect": "asyncpg",
    }
