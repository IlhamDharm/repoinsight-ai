"""Analysis Service orchestrating static code analysis and database persistence."""
from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Analysis, AnalysisStatus
from app.integrations.github.client import GitHubClient
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository
from app.services.analysis.complexity_analyzer import ComplexityAnalyzer
from app.services.analysis.dependency_analyzer import DependencyAnalyzer
from app.services.analysis.language_analyzer import LanguageAnalyzer
from app.services.analysis.quality_analyzer import QualityAnalyzer
from app.services.analysis.recommendation_engine import RecommendationEngine
from app.services.analysis.scoring_engine import ScoringEngine
from app.services.analysis.structure_analyzer import StructureAnalyzer
from app.services.repository_scanner import RepositoryScanService

logger = logging.getLogger("repoinsight.services.analysis_service")


class AnalysisService:
    """Service utama yang mengorkestrasi analisis repository secara modular:

    1. Ambil repository dari database
    2. Jalankan repository scanner (mengambil normalized snapshot)
    3. Jalankan language analyzer
    4. Jalankan structure analyzer
    5. Jalankan complexity analyzer
    6. Jalankan dependency analyzer
    7. Jalankan quality analyzer
    8. Gabungkan findings
    9. Hitung scores
    10. Generate recommendations
    11. Simpan ke database dan kembalikan model Analysis
    """

    def __init__(
        self,
        session: AsyncSession,
        github_client: GitHubClient,
        scanner_service: RepositoryScanService | None = None,
    ) -> None:
        self._session = session
        self._github_client = github_client
        self._scanner_service = scanner_service or RepositoryScanService(session, github_client)
        self._analysis_repo = AnalysisRepository(session)
        self._repo_repo = RepositoryRepository(session)

        self._language_analyzer = LanguageAnalyzer()
        self._structure_analyzer = StructureAnalyzer()
        self._complexity_analyzer = ComplexityAnalyzer()
        self._dependency_analyzer = DependencyAnalyzer()
        self._quality_analyzer = QualityAnalyzer()
        self._scoring_engine = ScoringEngine()
        self._recommendation_engine = RecommendationEngine()

    async def analyze_repository(self, repository_id: int) -> Analysis:
        """Menjalankan repository analysis secara lengkap berdasarkan ID repository.

        Args:
            repository_id: ID repository lokal di database.

        Returns:
            Model Analysis yang telah diselesaikan.

        Raises:
            NotFoundError: Jika repository tidak ditemukan di database.
        """
        repository = await self._repo_repo.get_by_id(repository_id)
        if repository is None:
            raise NotFoundError(f"Repository dengan ID {repository_id} tidak ditemukan")

        logger.info(
            "Memulai analysis service untuk repository id=%d full_name=%s",
            repository.id,
            repository.full_name,
        )

        # Buat record analysis di DB dengan status RUNNING
        now = datetime.now(timezone.utc)
        analysis_record = Analysis(
            repository_id=repository_id,
            status=AnalysisStatus.RUNNING,
            started_at=now,
        )
        analysis_record = await self._analysis_repo.create(analysis_record)

        try:
            # Step 1: Scan repository
            snapshot = await self._scanner_service.scan_repository(repository_id)

            # Step 2: Run Analyzers
            summary = self._language_analyzer.analyze(snapshot)
            struct_findings = self._structure_analyzer.analyze(snapshot)
            comp_findings, _ = self._complexity_analyzer.analyze(snapshot)
            dep_findings, _ = self._dependency_analyzer.analyze(snapshot)
            qual_findings = self._quality_analyzer.analyze(snapshot)

            # Step 3: Combine findings
            all_findings = struct_findings + comp_findings + dep_findings + qual_findings

            # Step 4: Compute scores & recommendations
            scores = self._scoring_engine.calculate_scores(all_findings)
            recommendations = self._recommendation_engine.generate_recommendations(all_findings)

            # Step 5: Update DB record as COMPLETED
            completed_time = datetime.now(timezone.utc)
            updated_analysis = await self._analysis_repo.update_status(
                analysis_id=analysis_record.id,
                status=AnalysisStatus.COMPLETED,
                completed_at=completed_time,
                summary=summary.to_dict(),
                scores=scores.to_dict(),
                findings=[f.to_dict() for f in all_findings],
                recommendations=recommendations,
            )

            logger.info("Analysis selesai untuk repository id=%d", repository_id)
            return updated_analysis or analysis_record

        except Exception as exc:
            logger.exception("Analysis gagal untuk repository id=%d: %s", repository_id, str(exc))
            completed_time = datetime.now(timezone.utc)
            await self._analysis_repo.update_status(
                analysis_id=analysis_record.id,
                status=AnalysisStatus.FAILED,
                completed_at=completed_time,
                error_message=str(exc),
            )
            raise
