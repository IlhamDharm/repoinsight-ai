from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis, AnalysisStatus
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Analysis)

    async def list_by_repository(self, repository_id: int, offset: int = 0, limit: int = 100) -> list[Analysis]:
        statement = select(Analysis).where(Analysis.repository_id == repository_id).offset(offset).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def list_by_status(self, status: AnalysisStatus, offset: int = 0, limit: int = 100) -> list[Analysis]:
        statement = select(Analysis).where(Analysis.status == status).offset(offset).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()
