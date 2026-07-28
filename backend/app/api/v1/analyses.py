"""API endpoint untuk mengambil status, hasil analysis, dan komparasi.

Endpoints:
    GET /api/v1/analyses/{analysis_id} — Status check dan hasil analisis
    GET /api/v1/analyses/{analysis_id}/compare/{previous_analysis_id} — Komparasi dua analisis
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user, get_request_id_dependency, verify_analysis_owner

from app.core.response import build_success_payload
from app.db.models import AnalysisStatus, User
from app.repositories.repository import RepositoryRepository
from app.schemas.analysis import AnalysisErrorPayload, AnalysisStatusResponse, AnalysisComparisonResponse
from app.services.analysis.job_service import AnalysisJobService
from app.services.analysis.history_service import AnalysisHistoryService

router = APIRouter()


async def _assert_analysis_ownership(session: AsyncSession, analysis_id: int, user: User):
    """Pastikan analysis milik user yang sedang login melalui ownership repository."""
    return await verify_analysis_owner(analysis_id, user, session)


@router.get(
    "/{analysis_id}",
    status_code=200,
    summary="Get analysis status and results",
    description=(
        "Retrieve the full status and results of an analysis.\n\n"
        "If status is `COMPLETED`, includes `scores`, `findings`, `recommendations`, and `summary`.\n"
        "If status is `FAILED`, includes an `error` object with failure details."
    ),
    responses={
        200: {"description": "Analysis status and results"},
        403: {"description": "Not the analysis owner"},
        404: {"description": "Analysis not found"},
    },
)
async def get_analysis_status(
    analysis_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Ambil status dan hasil analysis berdasarkan analysis ID."""
    analysis = await _assert_analysis_ownership(session, analysis_id, current_user)

    error_payload: AnalysisErrorPayload | None = None
    if analysis.status == AnalysisStatus.FAILED:
        error_payload = AnalysisErrorPayload(
            code="ANALYSIS_FAILED",
            message=analysis.error_message or "Analysis failed. Please check the error details or retry.",
        )

    response_data = AnalysisStatusResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status.value,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
        summary=analysis.summary,
        scores=analysis.scores,
        findings=analysis.findings,
        recommendations=analysis.recommendations,
        error=error_payload,
    )

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )


@router.get(
    "/{analysis_id}/compare/{previous_analysis_id}",
    status_code=200,
    summary="Compare two analyses",
    description=(
        "Compare two analysis results side by side. Returns score changes, "
        "category differences, and findings count delta."
    ),
    responses={
        200: {"description": "Comparison data"},
        403: {"description": "Not the analysis owner"},
        404: {"description": "One or both analyses not found"},
    },
)
async def compare_analyses(
    analysis_id: int,
    previous_analysis_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Bandingkan dua analysis result."""
    await _assert_analysis_ownership(session, analysis_id, current_user)
    await _assert_analysis_ownership(session, previous_analysis_id, current_user)

    history_service = AnalysisHistoryService(session)
    comparison_data = await history_service.compare_analyses(
        current_analysis_id=analysis_id,
        previous_analysis_id=previous_analysis_id,
    )

    response_data = AnalysisComparisonResponse(data=comparison_data)
    response_dict = response_data.model_dump(mode="json")

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            response_dict["data"],
            request_id=request_id,
            meta_extra=response_dict["meta"],
        ),
    )
