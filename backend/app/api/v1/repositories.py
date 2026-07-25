"""API endpoint untuk manajemen repository.

Endpoints:
    POST /api/v1/repositories              — Daftarkan atau perbarui GitHub repository
    POST /api/v1/repositories/{id}/scan   — Scan repository content
    POST /api/v1/repositories/{id}/analyze — Jadwalkan analysis (async, returns 202)
    GET /api/v1/repositories/{id}/analyses — Ambil history analysis repository
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_github_client, get_request_id_dependency
from app.core.response import build_success_payload
from app.integrations.github.client import GitHubClient
from app.schemas.analysis import AnalysisJobResponse
from app.schemas.repository import (
    RegisterRepositoryRequest,
    RepositoryResponse,
    RepositoryScanResponse,
)
from app.services.analysis import run_background_analysis
from app.services.analysis.job_service import AnalysisJobService
from app.services.analysis.history_service import AnalysisHistoryService
from app.services.github_sync import RepositorySyncService
from app.services.repository_scanner import RepositoryScanService

router = APIRouter()


@router.post("", status_code=201)
async def register_repository(
    body: RegisterRepositoryRequest,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    github_client: GitHubClient = Depends(get_github_client),
) -> JSONResponse:
    """Daftarkan GitHub repository atau perbarui metadata-nya jika sudah ada."""
    service = RepositorySyncService(session=session, github_client=github_client)
    repository = await service.sync_repository(body.url)

    response_data = RepositoryResponse(
        id=repository.id,
        github_repo_id=repository.github_repo_id,
        name=repository.name,
        full_name=repository.full_name,
        url=repository.url,
        default_branch=repository.default_branch,
        visibility=repository.visibility,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )

    return JSONResponse(
        status_code=201,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )


@router.post("/{repository_id}/scan", status_code=200)
async def scan_repository(
    repository_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    github_client: GitHubClient = Depends(get_github_client),
) -> JSONResponse:
    """Memulai basic repository content & code scan.

    Args:
        repository_id: ID repository di database lokal.

    Returns:
        200 OK — Hasil scan berisi normalized repository structure.

    Raises:
        404 — Repository tidak ditemukan di database atau di GitHub.
        429 — GitHub API rate limit terlampaui.
        401 — Token GitHub tidak valid.
        504 — GitHub API timeout.
        502 — External service error.
    """
    scanner_service = RepositoryScanService(session=session, github_client=github_client)
    scan_result = await scanner_service.scan_repository(repository_id)

    response_data = RepositoryScanResponse(
        repository=scan_result.repository,
        branch=scan_result.branch,
        total_files=scan_result.total_files,
        total_source_files=scan_result.total_source_files,
        total_lines=scan_result.total_lines,
        languages=scan_result.languages,
        files=[f.to_dict() for f in scan_result.files],
    )

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )


@router.post("/{repository_id}/analyze", status_code=202)
async def analyze_repository(
    repository_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    github_client: GitHubClient = Depends(get_github_client),
) -> JSONResponse:
    """Jadwalkan asynchronous AI Static Analysis Engine pada repository.

    Endpoint ini langsung mengembalikan HTTP 202 Accepted tanpa menunggu
    proses analisis selesai. Proses analisis berjalan di background.

    Gunakan GET /api/v1/analyses/{analysis_id} untuk memantau status.

    Args:
        repository_id: ID repository di database lokal.

    Returns:
        202 Accepted — analysis_id, repository_id, dan status "PENDING".

    Raises:
        404 — Repository tidak ditemukan di database.
        409 — Sudah ada analysis aktif (PENDING/RUNNING) untuk repository ini.
    """
    # Buat analysis job dengan status PENDING
    job_service = AnalysisJobService(session)
    analysis = await job_service.create_analysis_job(repository_id)

    # Jadwalkan background task — HTTP response tidak menunggu ini selesai
    background_tasks.add_task(
        run_background_analysis,
        analysis_id=analysis.id,
        repository_id=repository_id,
        github_client=github_client,
    )

    response_data = AnalysisJobResponse(
        analysis_id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status),
    )

    return JSONResponse(
        status_code=202,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )


@router.get("/{repository_id}/analyses", status_code=200)
async def get_analysis_history(
    repository_id: int,
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Ambil history analysis untuk sebuah repository.
    
    Args:
        repository_id: ID repository di database lokal.
        page: Nomor halaman (default: 1)
        page_size: Jumlah item per halaman (default: 20, max: 100)
        
    Returns:
        200 OK — Daftar riwayat analysis.
        
    Raises:
        404 — Repository tidak ditemukan.
    """
    history_service = AnalysisHistoryService(session)
    history_response = await history_service.get_analysis_history(
        repository_id=repository_id, 
        page=page, 
        page_size=page_size
    )

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            history_response.model_dump(mode="json")["data"],
            request_id=request_id,
            meta_extra=history_response.model_dump(mode="json")["meta"],
        ),
    )
