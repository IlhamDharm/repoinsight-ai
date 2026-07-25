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
from app.core.dependencies import get_request_id_dependency
from app.core.response import build_success_payload
from app.db.models import AnalysisStatus
from app.schemas.analysis import AnalysisErrorPayload, AnalysisStatusResponse, AnalysisComparisonResponse
from app.services.analysis.job_service import AnalysisJobService
from app.services.analysis.history_service import AnalysisHistoryService

router = APIRouter()


@router.get("/{analysis_id}", status_code=200)
async def get_analysis_status(
    analysis_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Ambil status dan hasil analysis berdasarkan analysis ID.

    Args:
        analysis_id: ID analysis job.

    Returns:
        200 OK — Status dan detail analisis.

    Response structure:
        - status "pending"/"running": hanya status + timestamps
        - status "completed": lengkap dengan summary, scores, findings, recommendations
        - status "failed": dengan error payload (tanpa detail internal)

    Raises:
        404 — Analysis tidak ditemukan.
    """
    job_service = AnalysisJobService(session)
    analysis = await job_service.get_analysis_by_id(analysis_id)

    # Build error payload jika FAILED
    error_payload: AnalysisErrorPayload | None = None
    if analysis.status == AnalysisStatus.FAILED:
        error_payload = AnalysisErrorPayload(
            code="ANALYSIS_FAILED",
            message="Analysis failed. Please check the error details or retry.",
        )

    response_data = AnalysisStatusResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status),
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


@router.get("/{analysis_id}/compare/{previous_analysis_id}", status_code=200)
async def compare_analyses(
    analysis_id: int,
    previous_analysis_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Bandingkan dua analysis result.
    
    Args:
        analysis_id: ID analysis job saat ini.
        previous_analysis_id: ID analysis job sebelumnya.
        
    Returns:
        200 OK — Data komparasi.
        
    Raises:
        400 — Analysis berbeda repository atau belum COMPLETED.
        404 — Analysis tidak ditemukan.
    """
    history_service = AnalysisHistoryService(session)
    comparison_data = await history_service.compare_analyses(
        current_analysis_id=analysis_id,
        previous_analysis_id=previous_analysis_id,
    )

    response_data = AnalysisComparisonResponse(data=comparison_data)

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            response_data.model_dump(mode="json")["data"],
            request_id=request_id,
            meta_extra=response_data.model_dump(mode="json")["meta"],
        ),
    )
