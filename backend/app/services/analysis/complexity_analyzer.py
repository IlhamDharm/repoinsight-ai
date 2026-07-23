"""Code Complexity Analyzer module using safe static analysis."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from app.services.analysis.types import Finding, FindingSeverity
from app.services.code_scanner import NormalizedRepositoryStructure


@dataclass
class FileComplexityMetrics:
    path: str
    language: str
    lines: int
    functions_count: int | None
    classes_count: int | None
    status: str  # "analyzed" or "unsupported"


class ComplexityAnalyzer:
    """Analyzer untuk menganalisis fungsi, kelas, dan indikator kompleksitas kode statis."""

    def analyze(self, snapshot: NormalizedRepositoryStructure) -> tuple[list[Finding], list[FileComplexityMetrics]]:
        """Menganalisis kompleksitas file di snapshot dan mengembalikan (findings, file_metrics)."""
        findings: list[Finding] = []
        metrics_list: list[FileComplexityMetrics] = []

        for file_meta in snapshot.files:
            functions_count: int | None = None
            classes_count: int | None = None
            status = "unsupported"

            if file_meta.language == "Python" and file_meta.content:
                try:
                    tree = ast.parse(file_meta.content)
                    func_nodes = [
                        node for node in ast.walk(tree)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ]
                    class_nodes = [
                        node for node in ast.walk(tree)
                        if isinstance(node, ast.ClassDef)
                    ]
                    functions_count = len(func_nodes)
                    classes_count = len(class_nodes)
                    status = "analyzed"
                except Exception:
                    # Syntax error atau AST failure -> fallback ke status unsupported
                    status = "unsupported"

            metrics_list.append(
                FileComplexityMetrics(
                    path=file_meta.path,
                    language=file_meta.language,
                    lines=file_meta.lines,
                    functions_count=functions_count,
                    classes_count=classes_count,
                    status=status,
                )
            )

            # Rule: High function count (> 15 functions in a single file)
            if functions_count is not None and functions_count > 15:
                findings.append(
                    Finding(
                        rule_id="high-function-count",
                        severity=FindingSeverity.MEDIUM.value,
                        category="complexity",
                        title=f"High function count in `{file_meta.path}`",
                        description=f"File `{file_meta.path}` contains {functions_count} functions, indicating high file responsibility.",
                        file_path=file_meta.path,
                        recommendation="Consider breaking down the module into smaller single-responsibility files.",
                    )
                )

            # Rule: Complex source file (> 300 lines and > 10 functions)
            if functions_count is not None and functions_count > 10 and file_meta.lines > 300:
                findings.append(
                    Finding(
                        rule_id="complex-source-file",
                        severity=FindingSeverity.MEDIUM.value,
                        category="complexity",
                        title=f"Potentially complex source file `{file_meta.path}`",
                        description=f"File `{file_meta.path}` has {file_meta.lines} lines and {functions_count} functions.",
                        file_path=file_meta.path,
                        recommendation="Extract helper classes or sub-modules to improve maintainability.",
                    )
                )

        return findings, metrics_list
