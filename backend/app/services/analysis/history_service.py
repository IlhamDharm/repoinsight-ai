from __future__ import annotations

import logging
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundError
from app.db.models import AnalysisStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository
from app.schemas.analysis import (
    AnalysisComparisonData,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
)
from app.schemas.common import PaginationMeta

logger = logging.getLogger("repoinsight.services.analysis_history_service")


class AnalysisHistoryService:
    """Service to handle analysis history and comparisons."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._analysis_repo = AnalysisRepository(session)
        self._repo_repo = RepositoryRepository(session)

    async def get_analysis_history(self, repository_id: int, page: int = 1, page_size: int = 20) -> AnalysisHistoryResponse:
        """Fetch paginated analysis history for a given repository."""
        # Validate repository
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise NotFoundError(f"Repository with ID {repository_id} not found")

        # Calculate pagination
        total_items = await self._analysis_repo.count_by_repository(repository_id)
        total_pages = ceil(total_items / page_size) if total_items > 0 else 0
        
        offset = (page - 1) * page_size
        
        analyses = await self._analysis_repo.list_by_repository(
            repository_id=repository_id, 
            offset=offset, 
            limit=page_size
        )

        history_items = []
        for analysis in analyses:
            score = self._calculate_overall_score(analysis.scores)
            history_items.append(
                AnalysisHistoryItem(
                    id=analysis.id,
                    status=analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status),
                    created_at=analysis.created_at,
                    completed_at=analysis.completed_at,
                    score=score,
                )
            )

        meta = PaginationMeta(
            page=page,
            page_size=page_size,
            total=total_items,
            total_pages=total_pages
        )

        return AnalysisHistoryResponse(data=history_items, meta=meta)

    async def compare_analyses(self, current_analysis_id: int, previous_analysis_id: int) -> AnalysisComparisonData:
        """Compare two analysis results."""
        current_analysis = await self._analysis_repo.get_by_id(current_analysis_id)
        if current_analysis is None:
            raise NotFoundError(f"Analysis with ID {current_analysis_id} not found")

        previous_analysis = await self._analysis_repo.get_by_id(previous_analysis_id)
        if previous_analysis is None:
            raise NotFoundError(f"Analysis with ID {previous_analysis_id} not found")

        if current_analysis.repository_id != previous_analysis.repository_id:
            raise AppException(
                "Analyses belong to different repositories",
                status_code=400,
                code="different_repository"
            )

        if current_analysis.status != AnalysisStatus.COMPLETED or previous_analysis.status != AnalysisStatus.COMPLETED:
            raise AppException(
                "Both analyses must be COMPLETED to be compared",
                status_code=400,
                code="incomplete_analysis"
            )

        current_scores = current_analysis.scores or {}
        previous_scores = previous_analysis.scores or {}

        current_overall = self._calculate_overall_score(current_scores) or 0
        previous_overall = self._calculate_overall_score(previous_scores) or 0

        score_change = current_overall - previous_overall

        current_findings_count = len(current_analysis.findings or [])
        previous_findings_count = len(previous_analysis.findings or [])
        findings_change = current_findings_count - previous_findings_count

        category_changes = {}
        all_categories = set(current_scores.keys()).union(set(previous_scores.keys()))
        for cat in all_categories:
            c_val = current_scores.get(cat, 0)
            p_val = previous_scores.get(cat, 0)
            category_changes[cat] = c_val - p_val

        return AnalysisComparisonData(
            current_analysis_id=current_analysis_id,
            previous_analysis_id=previous_analysis_id,
            score_change=score_change,
            current_score=current_overall,
            previous_score=previous_overall,
            category_changes=category_changes,
            findings_change=findings_change,
        )

    def _calculate_overall_score(self, scores: dict | None) -> int | None:
        """Helper to calculate overall score from category scores.
        
        Uses the average of the available category scores.
        """
        if not scores:
            return None
        values = [v for v in scores.values() if isinstance(v, (int, float))]
        if not values:
            return None
        return int(round(sum(values) / len(values)))
