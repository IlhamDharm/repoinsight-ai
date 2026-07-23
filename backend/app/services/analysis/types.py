"""Data structures and types for the Analysis Engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Finding:
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    file_path: str | None = None
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "recommendation": self.recommendation,
        }


@dataclass
class AnalysisScores:
    code_quality: int
    architecture: int
    maintainability: int

    def to_dict(self) -> dict[str, int]:
        return {
            "code_quality": self.code_quality,
            "architecture": self.architecture,
            "maintainability": self.maintainability,
        }


@dataclass
class AnalysisSummary:
    total_files: int
    total_source_files: int
    total_lines: int
    dominant_language: str | None
    languages: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_source_files": self.total_source_files,
            "total_lines": self.total_lines,
            "dominant_language": self.dominant_language,
            "languages": self.languages,
        }


@dataclass
class AnalysisResult:
    repository_id: int
    summary: AnalysisSummary
    scores: AnalysisScores
    findings: list[Finding]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "summary": self.summary.to_dict(),
            "scores": self.scores.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
        }
