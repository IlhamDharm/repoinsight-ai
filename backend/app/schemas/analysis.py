"""Pydantic schemas for Analysis API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FindingSchema(BaseModel):
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    file_path: str | None = None
    recommendation: str


class LanguageSummarySchema(BaseModel):
    files: int
    lines: int
    percentage: float


class AnalysisSummarySchema(BaseModel):
    total_files: int
    total_source_files: int
    total_lines: int
    dominant_language: str | None = None
    languages: dict[str, LanguageSummarySchema]


class AnalysisScoresSchema(BaseModel):
    code_quality: int
    architecture: int
    maintainability: int


class AnalysisResponse(BaseModel):
    id: int
    repository_id: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    error_message: str | None = None
    summary: dict[str, Any] | None = None
    scores: dict[str, int] | None = None
    findings: list[dict[str, Any]] | None = None
    recommendations: list[str] | None = None
