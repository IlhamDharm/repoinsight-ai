"""Scoring Engine module calculating transparent repository quality metrics."""
from __future__ import annotations

from app.services.analysis.types import AnalysisScores, Finding


class ScoringEngine:
    """Engine untuk menghitung skor kualitas, arsitektur, dan maintainability secara transparan.

    Formula:
        Score = max(0, min(100, Base (100) - Total Penalties))

    Semua penalty dihitung secara deterministik dari list of Finding.
    """

    def calculate_scores(self, findings: list[Finding]) -> AnalysisScores:
        """Kalkulasi skor berdasarkan findings yang ditemukan.

        Returns:
            AnalysisScores(code_quality, architecture, maintainability)
        """
        quality_penalty = 0
        architecture_penalty = 0
        maintainability_penalty = 0

        # Cap penalty berulang dari file-level findings agar tidak menghancurkan skor secara ekstrem
        large_file_quality_pen = 0
        large_file_maint_pen = 0
        very_large_file_quality_pen = 0
        very_large_file_maint_pen = 0
        high_func_maint_pen = 0
        complex_file_maint_pen = 0

        for f in findings:
            rule = f.rule_id

            if rule == "missing-readme":
                quality_penalty += 10
                maintainability_penalty += 10

            elif rule == "missing-tests":
                quality_penalty += 15
                maintainability_penalty += 15

            elif rule == "missing-dependency-manifest":
                architecture_penalty += 10
                maintainability_penalty += 10

            elif rule == "excessive-root-files":
                architecture_penalty += 10
                maintainability_penalty += 5

            elif rule == "excessive-directory-depth":
                architecture_penalty += 15
                maintainability_penalty += 10

            elif rule == "unorganized-source-structure":
                architecture_penalty += 10
                maintainability_penalty += 5

            elif rule == "large-source-file":
                large_file_quality_pen += 5
                large_file_maint_pen += 5

            elif rule == "very-large-source-file":
                very_large_file_quality_pen += 15
                very_large_file_maint_pen += 15

            elif rule == "high-function-count":
                high_func_maint_pen += 5

            elif rule == "complex-source-file":
                complex_file_maint_pen += 10
                quality_penalty += 5

        # Apply capped per-file penalties
        quality_penalty += min(20, large_file_quality_pen) + min(30, very_large_file_quality_pen)
        maintainability_penalty += (
            min(20, large_file_maint_pen)
            + min(30, very_large_file_maint_pen)
            + min(15, high_func_maint_pen)
            + min(20, complex_file_maint_pen)
        )

        code_quality = max(0, min(100, 100 - quality_penalty))
        architecture = max(0, min(100, 100 - architecture_penalty))
        maintainability = max(0, min(100, 100 - maintainability_penalty))

        return AnalysisScores(
            code_quality=code_quality,
            architecture=architecture,
            maintainability=maintainability,
        )
