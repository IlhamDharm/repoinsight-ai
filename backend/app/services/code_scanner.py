"""Service untuk mengekstraksi metadata kode dan menghasilkan normalized repository structure."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_detector import detect_language


@dataclass
class ScannedFileMetadata:
    """Metadata hasil scan untuk sebuah file source code."""

    path: str
    language: str
    size: int
    lines: int
    content: str | None = None

    def to_dict(self) -> dict:
        data = {
            "path": self.path,
            "language": self.language,
            "size": self.size,
            "lines": self.lines,
        }
        if self.content is not None:
            data["content"] = self.content
        return data


@dataclass
class NormalizedRepositoryStructure:
    """Hasil akhir normalized repository structure dari code scanner."""

    repository: str
    branch: str
    total_files: int
    total_source_files: int
    total_lines: int
    languages: dict[str, int] = field(default_factory=dict)
    files: list[ScannedFileMetadata] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repository": self.repository,
            "branch": self.branch,
            "total_files": self.total_files,
            "total_source_files": self.total_source_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "files": [f.to_dict() for f in self.files],
        }


class CodeScanner:
    """Engine untuk menghitung baris kode, statistik bahasa, dan metadata file."""

    @staticmethod
    def count_lines(content: str | None) -> int:
        """Hitung jumlah baris dalam string konten text."""
        if not content:
            return 0
        return len(content.splitlines())

    def analyze_scanned_files(
        self,
        repository_name: str,
        branch: str,
        total_tree_files: int,
        file_entries: list[tuple[str, int, str | None]],
    ) -> NormalizedRepositoryStructure:
        """Menghasilkan NormalizedRepositoryStructure dari kumpulan file entries.

        Args:
            repository_name: Nama full repository ('owner/repo').
            branch: Nama branch (mis. 'main').
            total_tree_files: Total seluruh file yang ditemukan di git tree.
            file_entries: List of tuple (path, size, content_or_none).

        Returns:
            NormalizedRepositoryStructure yang teragregasi.
        """
        scanned_files: list[ScannedFileMetadata] = []
        language_counts: dict[str, int] = {}
        sum_lines = 0

        for path, size, content in file_entries:
            lang = detect_language(path)
            lines = self.count_lines(content)
            sum_lines += lines

            if lang != "Unknown":
                language_counts[lang] = language_counts.get(lang, 0) + 1

            scanned_files.append(
                ScannedFileMetadata(
                    path=path,
                    language=lang,
                    size=size,
                    lines=lines,
                    content=content,
                )
            )

        return NormalizedRepositoryStructure(
            repository=repository_name,
            branch=branch,
            total_files=total_tree_files,
            total_source_files=len(scanned_files),
            total_lines=sum_lines,
            languages=language_counts,
            files=scanned_files,
        )
