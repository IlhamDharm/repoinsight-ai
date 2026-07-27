from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_by_github_username(self, github_username: str) -> User | None:
        statement = select(User).where(User.github_username == github_username)
        result = await self._session.execute(statement)
        return result.scalars().first()
