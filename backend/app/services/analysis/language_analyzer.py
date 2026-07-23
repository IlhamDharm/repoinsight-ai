"""Language Analyzer module for RepoInsight AI."""
from __future__ import annotations

from typing import Any

from app.services.analysis.types import AnalysisSummary
from app.services.code_scanner import NormalizedRepositoryStructure


class LanguageAnalyzer:
    """Analyzer untuk mengkategorikan dan mengkalkulasi statistik penggunaan bahasa."""

    def analyze(self, snapshot: NormalizedRepositoryStructure) -> AnalysisSummary:
        """Menganalisis statistik bahasa dari NormalizedRepositoryStructure snapshot.

        Returns:
            AnalysisSummary berisi total_files, total_source_files, total_lines,
            dominant_language, dan dict breakdown per bahasa.
        """
        total_files = snapshot.total_files
        total_source_files = snapshot.total_source_files
        total_lines = snapshot.total_lines

        # Hitung statistik per bahasa dari snapshot.files
        lang_stats: dict[str, dict[str, int]] = {}

        for file_meta in snapshot.files:
            lang = file_meta.language
            if lang == "Unknown":
                continue
            if lang not in lang_stats:
                lang_stats[lang] = {"files": 0, "lines": 0}
            lang_stats[lang]["files"] += 1
            lang_stats[lang]["lines"] += file_meta.lines

        # Hitung persentase dan dominant language
        languages_output: dict[str, dict[str, Any]] = {}
        dominant_language: str | None = None
        max_lines_or_files = -1

        for lang, stats in lang_stats.items():
            f_count = stats["files"]
            l_count = stats["lines"]

            if total_lines > 0:
                percentage = round((l_count / total_lines) * 100, 2)
            elif total_source_files > 0:
                percentage = round((f_count / total_source_files) * 100, 2)
            else:
                percentage = 0.0

            languages_output[lang] = {
                "files": f_count,
                "lines": l_count,
                "percentage": percentage,
            }

            # Tentukan dominant language berdasarkan lines, lalu files
            metric = l_count if total_lines > 0 else f_count
            if metric > max_lines_or_files:
                max_lines_or_files = metric
                dominant_language = lang

        return AnalysisSummary(
            total_files=total_files,
            total_source_files=total_source_files,
            total_lines=total_lines,
            dominant_language=dominant_language,
            languages=languages_output,
        )
