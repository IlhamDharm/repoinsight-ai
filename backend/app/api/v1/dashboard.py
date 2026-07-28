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


@router.get(
    "/stats",
    status_code=200,
    summary="Get dashboard statistics",
    description=(
        "Retrieve summary statistics for the authenticated user's dashboard.\n\n"
        "Returns `repository_count`, `analysis_count`, and the 5 most recent analyses with scores."
    ),
    responses={
        200: {"description": "Dashboard statistics"},
        401: {"description": "Authentication required"},
    },
)
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
        recent_rows = recent_result.all()

        completed_ids = [row.id for row in recent_rows if row.status == AnalysisStatus.COMPLETED]
        scores_map: dict[int, dict] = {}
        if completed_ids:
            scores_stmt = select(Analysis.id, Analysis.scores).where(
                Analysis.id.in_(completed_ids)
            )
            scores_result = await session.execute(scores_stmt)
            for scores_row in scores_result.all():
                scores_map[scores_row.id] = scores_row.scores or {}

        for row in recent_rows:
            score = None
            scores = scores_map.get(row.id)
            if scores and isinstance(scores, dict):
                values = [v for v in scores.values() if isinstance(v, (int, float))]
                if values:
                    score = round(sum(values) / len(values))

            recent_analyses.append(
                {
                    "id": row.id,
                    "status": row.status.value,
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
