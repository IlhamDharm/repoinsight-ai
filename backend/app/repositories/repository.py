from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Repository)

    async def get_by_github_repo_id(self, github_repo_id: int) -> Repository | None:
        statement = select(Repository).where(Repository.github_repo_id == github_repo_id)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_by_full_name(self, full_name: str) -> Repository | None:
        statement = select(Repository).where(Repository.full_name == full_name)
        result = await self._session.execute(statement)
        return result.scalars().first()
