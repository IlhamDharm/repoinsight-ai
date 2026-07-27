"""API endpoint untuk dashboard.

Endpoints:
    GET /api/v1/dashboard/stats — Ringkasan dashboard untuk user yang login
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user, get_request_id_dependency
from app.core.response import build_success_payload
from app.db.models import Analysis, AnalysisStatus, Repository, User
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository

router = APIRouter()


@router.get("/stats", status_code=200)
async def get_dashboard_stats(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Ambil ringkasan statistik dashboard untuk user yang sedang login.

    Returns:
        200 — Stats dashboard: repository_count, analysis_count, recent analyses.
    """
    repo_repo = RepositoryRepository(session)
    analysis_repo = AnalysisRepository(session)

    total_repos = await repo_repo.count_by_owner(current_user.id)

    owner_repo_ids_stmt = (
        select(Repository.id).where(Repository.owner_id == current_user.id)
    )
    owner_repo_ids_result = await session.execute(owner_repo_ids_stmt)
    owner_repo_ids = [row[0] for row in owner_repo_ids_result.all()]

    total_analyses = 0
    recent_analyses: list[dict] = []

    if owner_repo_ids:
        count_stmt = select(func.count(Analysis.id)).where(
            Analysis.repository_id.in_(owner_repo_ids)
        )
        count_result = await session.execute(count_stmt)
        total_analyses = count_result.scalar() or 0

        recent_stmt = (
            select(
                Analysis.id,
                Analysis.status,
                Analysis.created_at,
                Analysis.completed_at,
                Analysis.repository_id,
                Repository.full_name,
            )
            .join(Repository, Analysis.repository_id == Repository.id)
            .where(Analysis.repository_id.in_(owner_repo_ids))
            .order_by(Analysis.created_at.desc())
            .limit(5)
        )
        recent_result = await session.execute(recent_stmt)
        for row in recent_result.all():
            score = None
            if row.status == AnalysisStatus.COMPLETED:
                score_stmt = select(Analysis.scores).where(Analysis.id == row.id)
                score_result = await session.execute(score_stmt)
                scores = score_result.scalar()
                if scores and isinstance(scores, dict):
                    values = [v for v in scores.values() if isinstance(v, (int, float))]
                    if values:
                        score = round(sum(values) / len(values))

            recent_analyses.append(
                {
                    "id": row.id,
                    "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "repository_id": row.repository_id,
                    "repository_name": row.full_name,
                    "score": score,
                }
            )

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            {
                "repository_count": total_repos,
                "analysis_count": total_analyses,
                "recent_analyses": recent_analyses,
            },
            request_id=request_id,
        ),
    )
