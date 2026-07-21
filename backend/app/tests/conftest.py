from __future__ import annotations

import pytest

from app.core.database import Base, get_engine


@pytest.fixture(scope="session", autouse=True)
async def initialize_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
