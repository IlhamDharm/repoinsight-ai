from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, get_engine, get_session_factory
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password
from app.db.models import User
from app.main import app


@pytest.fixture(scope="session", autouse=True)
async def initialize_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture()
def authenticated_user_factory():
    """Factory untuk membuat user terautentikasi di database dan return token."""
    created_users: list[User] = []

    async def _factory(email: str | None = None, password: str = "TestPassword123!") -> tuple[User, str]:
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            created_users.append(user)
            token = create_access_token(subject=user.id)
            return user, token

    yield _factory


@pytest.fixture()
def auth_headers_factory(authenticated_user_factory):
    """Factory untuk membuat authorization headers."""
    async def _factory(email: str | None = None, password: str = "TestPassword123!") -> dict[str, str]:
        _, token = await authenticated_user_factory(email=email, password=password)
        return {"Authorization": f"Bearer {token}"}

    return _factory


@pytest.fixture()
def mock_auth_dependency():
    """Override get_current_user dependency dengan user mock."""
    created_users: list[User] = []

    async def _setup(email: str | None = None, password: str = "TestPassword123!") -> tuple[User, dict[str, str]]:
        if email is None:
            email = f"mock_{uuid.uuid4().hex[:8]}@example.com"
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            created_users.append(user)

            async def _get_user() -> User:
                return user

            app.dependency_overrides[get_current_user] = _get_user
            token = create_access_token(subject=user.id)
            return user, {"Authorization": f"Bearer {token}"}

    yield _setup

    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependency_overrides():
    """Pastikan dependency overrides dibersihkan setelah setiap test."""
    yield
    app.dependency_overrides.clear()
