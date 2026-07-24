"""Analysis Job Service — mengelola lifecycle analysis job.

Status transitions yang valid:
    PENDING  → RUNNING     (start_analysis_job)
    RUNNING  → COMPLETED   (complete_analysis_job)
    RUNNING  → FAILED      (fail_analysis_job)
    PENDING  → FAILED      (fail_analysis_job, jika gagal sebelum RUNNING)

Transisi yang tidak valid akan raise InvalidStatusTransitionError.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundError
from app.db.models import Analysis, AnalysisStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository

logger = logging.getLogger("repoinsight.services.analysis_job_service")


class InvalidStatusTransitionError(AppException):
    """Raised ketika transisi status analysis job tidak valid."""

    def __init__(self, current: AnalysisStatus, target: AnalysisStatus) -> None:
        super().__init__(
            f"Transisi status tidak valid: {current.value} → {target.value}",
            status_code=409,
            code="invalid_status_transition",
        )
        self.current = current
        self.target = target


class DuplicateActiveAnalysisError(AppException):
    """Raised ketika repository sudah memiliki analysis yang sedang berjalan."""

    def __init__(self, analysis_id: int) -> None:
        super().__init__(
            f"Repository sudah memiliki analysis aktif (id={analysis_id}). "
            "Tunggu hingga selesai sebelum memulai analysis baru.",
            status_code=409,
            code="duplicate_active_analysis",
        )
        self.analysis_id = analysis_id


# Mapping valid transitions
_VALID_TRANSITIONS: dict[AnalysisStatus, set[AnalysisStatus]] = {
    AnalysisStatus.PENDING: {AnalysisStatus.RUNNING, AnalysisStatus.FAILED},
    AnalysisStatus.RUNNING: {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED},
    AnalysisStatus.COMPLETED: set(),
    AnalysisStatus.FAILED: set(),
}


class AnalysisJobService:
    """Service untuk mengelola lifecycle analysis job.

    Bertanggung jawab atas:
    - Pembuatan job baru (create_analysis_job)
    - Transisi status yang valid (start, complete, fail)
    - Pencegahan duplicate job yang aktif
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._analysis_repo = AnalysisRepository(session)
        self._repo_repo = RepositoryRepository(session)

    # ─── Public Methods ───────────────────────────────────────────────────────

    async def create_analysis_job(self, repository_id: int) -> Analysis:
        """Buat analysis job baru dengan status PENDING.

        Jika sudah ada analysis aktif (PENDING atau RUNNING) untuk
        repository yang sama, akan raise DuplicateActiveAnalysisError.

        Raises:
            NotFoundError: Repository tidak ditemukan.
            DuplicateActiveAnalysisError: Ada analysis aktif untuk repository ini.
        """
        repository = await self._repo_repo.get_by_id(repository_id)
        if repository is None:
            raise NotFoundError(f"Repository dengan ID {repository_id} tidak ditemukan")

        active = await self._analysis_repo.get_active_analysis_by_repo(repository_id)
        if active is not None:
            logger.warning(
                "Menolak pembuatan analysis baru: repository id=%d sudah memiliki "
                "analysis aktif id=%d status=%s",
                repository_id,
                active.id,
                active.status.value,
            )
            raise DuplicateActiveAnalysisError(active.id)

        analysis = Analysis(
            repository_id=repository_id,
            status=AnalysisStatus.PENDING,
        )
        analysis = await self._analysis_repo.create(analysis)
        await self._session.commit()
        await self._session.refresh(analysis)

        logger.info(
            "Analysis job dibuat: id=%d repository_id=%d status=PENDING",
            analysis.id,
            repository_id,
        )
        return analysis

    async def start_analysis_job(self, analysis_id: int) -> Analysis:
        """Transisikan status job dari PENDING ke RUNNING.

        Raises:
            NotFoundError: Analysis tidak ditemukan.
            InvalidStatusTransitionError: Status saat ini bukan PENDING.
        """
        analysis = await self._get_or_raise(analysis_id)
        self._assert_valid_transition(analysis, AnalysisStatus.RUNNING)

        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(analysis)

        logger.info("Analysis job id=%d dimulai (RUNNING)", analysis_id)
        return analysis

    async def complete_analysis_job(
        self,
        analysis_id: int,
        summary: dict[str, Any],
        scores: dict[str, Any],
        findings: list[dict[str, Any]],
        recommendations: list[str],
    ) -> Analysis:
        """Transisikan status job dari RUNNING ke COMPLETED dan simpan hasil analisis.

        Raises:
            NotFoundError: Analysis tidak ditemukan.
            InvalidStatusTransitionError: Status saat ini bukan RUNNING.
        """
        analysis = await self._get_or_raise(analysis_id)
        self._assert_valid_transition(analysis, AnalysisStatus.COMPLETED)

        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.summary = summary
        analysis.scores = scores
        analysis.findings = findings
        analysis.recommendations = recommendations
        await self._session.commit()
        await self._session.refresh(analysis)

        logger.info("Analysis job id=%d selesai (COMPLETED)", analysis_id)
        return analysis

    async def fail_analysis_job(
        self, analysis_id: int, error_message: str
    ) -> Analysis:
        """Transisikan status job ke FAILED dan simpan pesan error yang aman.

        Mendukung transisi dari PENDING atau RUNNING.

        Raises:
            NotFoundError: Analysis tidak ditemukan.
            InvalidStatusTransitionError: Status tidak bisa di-FAIL-kan.
        """
        analysis = await self._get_or_raise(analysis_id)
        self._assert_valid_transition(analysis, AnalysisStatus.FAILED)

        analysis.status = AnalysisStatus.FAILED
        analysis.completed_at = datetime.now(timezone.utc)
        # Truncate dan sanitize error message — jangan bocorkan stack trace
        safe_message = str(error_message)[:1000]
        analysis.error_message = safe_message
        await self._session.commit()
        await self._session.refresh(analysis)

        logger.info("Analysis job id=%d gagal (FAILED): %s", analysis_id, safe_message)
        return analysis

    async def get_analysis_by_id(self, analysis_id: int) -> Analysis:
        """Ambil analysis berdasarkan ID.

        Raises:
            NotFoundError: Analysis tidak ditemukan.
        """
        return await self._get_or_raise(analysis_id)

    # ─── Private Helpers ──────────────────────────────────────────────────────

    async def _get_or_raise(self, analysis_id: int) -> Analysis:
        analysis = await self._analysis_repo.get_by_id(analysis_id)
        if analysis is None:
            raise NotFoundError(f"Analysis dengan ID {analysis_id} tidak ditemukan")
        return analysis

    def _assert_valid_transition(
        self, analysis: Analysis, target: AnalysisStatus
    ) -> None:
        current = analysis.status
        if target not in _VALID_TRANSITIONS.get(current, set()):
            raise InvalidStatusTransitionError(current, target)
