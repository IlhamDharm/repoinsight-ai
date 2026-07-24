"""Background analysis task untuk RepoInsight AI.

Background task TIDAK menggunakan database session dari HTTP request.
Setiap background task membuat AsyncSession baru dari session factory.

Workflow:
    1. Buat AsyncSession baru (bukan dari request scope)
    2. Ubah status job: PENDING → RUNNING
    3. Jalankan repository scanner
    4. Jalankan static analyzers
    5. Hitung scores & recommendations
    6. Simpan hasil ke DB
    7. Ubah status job: RUNNING → COMPLETED
    Jika exception:
    8. Log internal error (bukan ke client)
    9. Ubah status job → FAILED (dengan safe error message)
"""
from __future__ import annotations

import logging

from app.core.database import get_session_factory
from app.integrations.github.client import GitHubClient
from app.services.analysis.complexity_analyzer import ComplexityAnalyzer
from app.services.analysis.dependency_analyzer import DependencyAnalyzer
from app.services.analysis.job_service import AnalysisJobService
from app.services.analysis.language_analyzer import LanguageAnalyzer
from app.services.analysis.quality_analyzer import QualityAnalyzer
from app.services.analysis.recommendation_engine import RecommendationEngine
from app.services.analysis.scoring_engine import ScoringEngine
from app.services.analysis.structure_analyzer import StructureAnalyzer
from app.services.repository_scanner import RepositoryScanService

logger = logging.getLogger("repoinsight.services.background_analysis")


async def run_background_analysis(
    analysis_id: int,
    repository_id: int,
    github_client: GitHubClient,
) -> None:
    """Jalankan analisis repository secara asynchronous di background.

    Fungsi ini dipanggil oleh FastAPI BackgroundTasks setelah HTTP request
    sudah mengembalikan HTTP 202 Accepted kepada client.

    PENTING: Fungsi ini membuat AsyncSession BARU — tidak menggunakan
    session dari HTTP request yang sudah ditutup.

    Args:
        analysis_id: ID analysis job yang sudah dibuat (status PENDING).
        repository_id: ID repository yang akan dianalisis.
        github_client: Instance GitHubClient yang dikonfigurasi.
    """
    logger.info(
        "Memulai background analysis: analysis_id=%d repository_id=%d",
        analysis_id,
        repository_id,
    )

    session_factory = get_session_factory()

    # Buat sesi database baru — independen dari HTTP request
    async with session_factory() as session:
        job_service = AnalysisJobService(session)

        try:
            # Step 1: Transisi PENDING → RUNNING
            await job_service.start_analysis_job(analysis_id)
            logger.info("Analysis id=%d: PENDING → RUNNING", analysis_id)

            # Step 2: Scan repository (mengambil normalized snapshot)
            scanner_service = RepositoryScanService(session, github_client)
            snapshot = await scanner_service.scan_repository(repository_id)
            logger.info(
                "Analysis id=%d: scan selesai — %d files",
                analysis_id,
                snapshot.total_source_files,
            )

            # Step 3: Jalankan static analyzers
            language_analyzer = LanguageAnalyzer()
            structure_analyzer = StructureAnalyzer()
            complexity_analyzer = ComplexityAnalyzer()
            dependency_analyzer = DependencyAnalyzer()
            quality_analyzer = QualityAnalyzer()

            summary = language_analyzer.analyze(snapshot)
            struct_findings = structure_analyzer.analyze(snapshot)
            comp_findings, _ = complexity_analyzer.analyze(snapshot)
            dep_findings, _ = dependency_analyzer.analyze(snapshot)
            qual_findings = quality_analyzer.analyze(snapshot)

            # Step 4: Gabungkan findings
            all_findings = struct_findings + comp_findings + dep_findings + qual_findings

            # Step 5: Hitung scores & recommendations
            scoring_engine = ScoringEngine()
            recommendation_engine = RecommendationEngine()
            scores = scoring_engine.calculate_scores(all_findings)
            recommendations = recommendation_engine.generate_recommendations(all_findings)

            # Step 6: Simpan hasil & transisi RUNNING → COMPLETED
            await job_service.complete_analysis_job(
                analysis_id=analysis_id,
                summary=summary.to_dict(),
                scores=scores.to_dict(),
                findings=[f.to_dict() for f in all_findings],
                recommendations=recommendations,
            )

            logger.info(
                "Background analysis selesai: analysis_id=%d repository_id=%d status=COMPLETED",
                analysis_id,
                repository_id,
            )

        except Exception as exc:
            # Log detail exception secara internal — jangan bocorkan ke client
            logger.exception(
                "Background analysis gagal: analysis_id=%d repository_id=%d error=%s",
                analysis_id,
                repository_id,
                type(exc).__name__,
            )

            # Safe error message tanpa stack trace
            safe_message = f"{type(exc).__name__}: {str(exc)}"[:1000]

            try:
                # Buat sesi baru untuk update FAILED (sesi lama mungkin sudah rusak)
                async with session_factory() as fail_session:
                    fail_job_service = AnalysisJobService(fail_session)
                    await fail_job_service.fail_analysis_job(analysis_id, safe_message)
                    logger.info(
                        "Analysis id=%d ditandai FAILED dengan safe error message",
                        analysis_id,
                    )
            except Exception as fail_exc:
                # Worst-case: tidak bisa update status — log saja
                logger.exception(
                    "Gagal mengupdate status FAILED untuk analysis id=%d: %s",
                    analysis_id,
                    str(fail_exc),
                )
