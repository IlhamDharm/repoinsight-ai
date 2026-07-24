from datetime import datetime
from typing import Any

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
        return list(result.scalars().all())

    async def list_by_status(self, status: AnalysisStatus, offset: int = 0, limit: int = 100) -> list[Analysis]:
        statement = select(Analysis).where(Analysis.status == status).offset(offset).limit(limit)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_active_analysis_by_repo(self, repository_id: int) -> Analysis | None:
        statement = (
            select(Analysis)
            .where(
                Analysis.repository_id == repository_id,
                Analysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.RUNNING]),
            )
            .order_by(Analysis.created_at.desc())
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def create_analysis(self, repository_id: int) -> Analysis:
        analysis = Analysis(
            repository_id=repository_id,
            status=AnalysisStatus.PENDING,
        )
        return await self.create(analysis)

    async def update_status(
        self,
        analysis_id: int,
        status: AnalysisStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        summary: dict[str, Any] | None = None,
        scores: dict[str, int] | None = None,
        findings: list[dict[str, Any]] | None = None,
        recommendations: list[str] | None = None,
    ) -> Analysis | None:
        analysis = await self.get_by_id(analysis_id)
        if not analysis:
            return None

        analysis.status = status
        if started_at is not None:
            analysis.started_at = started_at
        if completed_at is not None:
            analysis.completed_at = completed_at
        if error_message is not None:
            analysis.error_message = error_message
        if summary is not None:
            analysis.summary = summary
        if scores is not None:
            analysis.scores = scores
        if findings is not None:
            analysis.findings = findings
        if recommendations is not None:
            analysis.recommendations = recommendations

        await self._session.commit()
        await self._session.refresh(analysis)
        return analysis
