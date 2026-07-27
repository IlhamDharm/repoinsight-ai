"""API endpoint untuk manajemen repository.

Endpoints:
    GET  /api/v1/repositories              — Ambil daftar repository milik user
    GET  /api/v1/repositories/{id}         — Ambil detail satu repository
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
from app.core.dependencies import get_current_user, get_github_client, get_request_id_dependency, verify_repository_owner
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.response import build_success_payload
from app.db.models import User
from app.integrations.github.client import GitHubClient
from app.schemas.analysis import AnalysisJobResponse
from app.schemas.repository import (
    RegisterRepositoryRequest,
    RepositoryListItem,
    RepositoryResponse,
    RepositoryScanResponse,
)
from app.services.analysis import run_background_analysis
from app.services.analysis.job_service import AnalysisJobService
from app.services.analysis.history_service import AnalysisHistoryService
from app.services.github_sync import RepositorySyncService
from app.services.repository_scanner import RepositoryScanService
from app.repositories.repository import RepositoryRepository

router = APIRouter()


@router.get("", status_code=200)
async def list_user_repositories(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Ambil daftar repository milik user yang sedang login."""
    from math import ceil

    repo_repo = RepositoryRepository(session)

    total_items = await repo_repo.count_by_owner(current_user.id)
    total_pages = ceil(total_items / page_size) if total_items > 0 else 0

    offset = (page - 1) * page_size
    repositories = await repo_repo.list_by_owner(
        owner_id=current_user.id,
        offset=offset,
        limit=page_size,
    )

    items = [
        RepositoryListItem(
            id=r.id,
            github_repo_id=r.github_repo_id,
            name=r.name,
            full_name=r.full_name,
            url=r.url,
            default_branch=r.default_branch,
            visibility=r.visibility,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ).model_dump(mode="json")
        for r in repositories
    ]

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            items,
            request_id=request_id,
            meta_extra={
                "page": page,
                "page_size": page_size,
                "total": total_items,
                "total_pages": total_pages,
            },
        ),
    )


async def _get_owned_repository(session: AsyncSession, repository_id: int, user: User):
    """Ambil repository dan pastikan milik user yang sedang login."""
    return await verify_repository_owner(repository_id, user, session)


@router.get("/{repository_id}", status_code=200)
async def get_repository(
    repository_id: int,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Ambil detail satu repository berdasarkan ID."""
    repository = await _get_owned_repository(session, repository_id, current_user)

    response_data = RepositoryListItem(
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
        status_code=200,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )


@router.post("", status_code=201)
async def register_repository(
    body: RegisterRepositoryRequest,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    github_client: GitHubClient = Depends(get_github_client),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Daftarkan GitHub repository atau perbarui metadata-nya jika sudah ada.

    Repository akan dimiliki oleh user yang sedang login.
    """
    service = RepositorySyncService(session=session, github_client=github_client)
    repository = await service.sync_repository(body.url, owner_id=current_user.id)

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
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Memulai basic repository content & code scan."""
    await _get_owned_repository(session, repository_id, current_user)

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
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Jadwalkan asynchronous AI Static Analysis Engine pada repository."""
    await _get_owned_repository(session, repository_id, current_user)

    job_service = AnalysisJobService(session)
    analysis = await job_service.create_analysis_job(repository_id)

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
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Ambil history analysis untuk sebuah repository."""
    await _get_owned_repository(session, repository_id, current_user)

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
