import asyncio
import sys
import weakref
from collections.abc import AsyncIterator
from urllib.parse import urlsplit, urlunsplit
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Base(DeclarativeBase):
    pass


# Import domain models explicitly so SQLAlchemy metadata includes them for migration generation
# and runtime ORM usage.
try:
    import app.db.models  # noqa: F401
except Exception:
    pass

_engine_by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncEngine] = weakref.WeakKeyDictionary()
_session_factory_by_loop: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, async_sessionmaker[AsyncSession]] = weakref.WeakKeyDictionary()


def normalize_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the asyncpg SQLAlchemy dialect.

    Neon provides URLs beginning with ``postgresql://``. SQLAlchemy otherwise
    selects psycopg2, while this service intentionally ships asyncpg only.
    """
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def init_database() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    loop = asyncio.get_running_loop()

    if loop in _engine_by_loop and loop in _session_factory_by_loop:
        return _engine_by_loop[loop], _session_factory_by_loop[loop]

    settings = get_settings()
    engine = create_async_engine(
        normalize_database_url(settings.database_url),
        echo=settings.database_echo,
        poolclass=NullPool,
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


async def initialize_database_schema() -> None:
    """Create missing ORM tables for a new deployment/database."""
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


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
