from app.services.code_scanner import CodeScanner, ScannedFileMetadata, NormalizedRepositoryStructure


def test_code_scanner_count_lines():
    assert CodeScanner.count_lines("line1\nline2\nline3") == 3
    assert CodeScanner.count_lines("") == 0
    assert CodeScanner.count_lines(None) == 0


def test_code_scanner_analyze_scanned_files():
    scanner = CodeScanner()
    file_entries = [
        ("app/main.py", 1200, "import os\nimport sys\n\nprint('hello')"),  # 4 lines, Python
        ("app/config.py", 500, "DEBUG = True\nPORT = 8000"),  # 2 lines, Python
        ("src/index.ts", 800, "console.log('hi');\nexport default {};"),  # 2 lines, TypeScript
        ("README.md", 300, "# Title\n\nSome docs"),  # 3 lines, Markdown
        ("unknown.xyz", 100, "some content"),  # 1 line, Unknown
    ]

    result = scanner.analyze_scanned_files(
        repository_name="owner/repo",
        branch="main",
        total_tree_files=10,
        file_entries=file_entries,
    )

    assert isinstance(result, NormalizedRepositoryStructure)
    assert result.repository == "owner/repo"
    assert result.branch == "main"
    assert result.total_files == 10
    assert result.total_source_files == 5
    assert result.total_lines == 12
    assert result.languages == {
        "Python": 2,
        "TypeScript": 1,
        "Markdown": 1,
    }
    assert len(result.files) == 5
    assert result.files[0].path == "app/main.py"
    assert result.files[0].language == "Python"
    assert result.files[0].lines == 4
