"""Recommendation Engine module generating actionable project improvements."""
from __future__ import annotations

from app.services.analysis.types import Finding


class RecommendationEngine:
    """Engine untuk menghasilkan daftar rekomendasi perbaikan dari findings."""

    def generate_recommendations(self, findings: list[Finding]) -> list[str]:
        """Menghasilkan list of recommendation strings unik berdasarkan findings.

        Returns:
            List of actionable recommendation strings.
        """
        recommendations: list[str] = []
        seen: set[str] = set()

        for f in findings:
            rec_text = f.recommendation.strip() if f.recommendation else ""
            if not rec_text:
                continue

            # Jika finding memiliki file_path dan rec_text belum mencantumkannya, buat lebih spesifik
            if f.file_path and f.file_path not in rec_text:
                rec_text = f"{rec_text} (Target: `{f.file_path}`)."

            if rec_text not in seen:
                seen.add(rec_text)
                recommendations.append(rec_text)

        return recommendations
