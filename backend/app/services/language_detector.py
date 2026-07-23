"""Mekanisme sederhana untuk mendeteksi bahasa pemrograman berdasarkan ekstensi file."""
from __future__ import annotations

import os

# Pemetaan ekstensi file (lowercase) ke nama bahasa
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".php": "PHP",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".c": "C",
    ".h": "C",
    ".cs": "C#",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".markdown": "Markdown",
}


def detect_language(file_path: str) -> str:
    """Mendeteksi bahasa pemrograman atau format file berdasarkan ekstensi.

    Args:
        file_path: Path file (misal 'app/main.py' atau 'index.tsx').

    Returns:
        Nama bahasa (mis. 'Python', 'TypeScript') atau 'Unknown' jika ekstensi tidak dikenali.
    """
    _, ext = os.path.splitext(file_path)
    if not ext:
        return "Unknown"

    ext_lower = ext.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext_lower, "Unknown")
