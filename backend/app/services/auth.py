"""Authentication service — register dan login."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateResourceError, NotFoundError, ValidationError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.user import UserRepository

logger = logging.getLogger("repoinsight.services.auth")


class AuthService:
    """Service untuk operasi authentication: register dan login.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)

    async def register(self, email: str, password: str) -> User:
        """Registrasi user baru.

        Args:
            email: Email unik user.
            password: Password plain text (akan di-hash).

        Returns:
            User yang baru dibuat.

        Raises:
            DuplicateResourceError: Email sudah terdaftar.
            ValidationError: Input tidak valid.
        """
        existing = await self._user_repo.get_by_email(email)
        if existing is not None:
            raise DuplicateResourceError("Email sudah terdaftar")

        password_hashed = hash_password(password)
        user = User(
            email=email,
            password_hash=password_hashed,
            is_active=True,
        )
        user = await self._user_repo.create(user)
        await self._session.commit()
        await self._session.refresh(user)

        logger.info("User baru didaftarkan: id=%d email=%s", user.id, user.email)
        return user

    async def authenticate(self, email: str, password: str) -> str:
        """Autentikasi user dan return access token.

        Args:
            email: Email user.
            password: Password plain text.

        Returns:
            JWT access token string.

        Raises:
            NotFoundError: Email tidak ditemukan.
            ValidationError: Password salah atau user inactive.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None:
            raise NotFoundError("Email atau password salah")

        if not verify_password(password, user.password_hash):
            raise NotFoundError("Email atau password salah")

        if not user.is_active:
            raise ValidationError("Akun tidak aktif")

        token = create_access_token(subject=user.id)
        logger.info("User berhasil login: id=%d email=%s", user.id, user.email)
        return token
