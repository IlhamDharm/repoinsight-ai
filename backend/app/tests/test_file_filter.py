from app.services.file_filter import FileFilter, FileFilterConfig


def test_file_filter_allowed_source_code_files():
    ff = FileFilter()
    assert ff.should_process("app/main.py") is True
    assert ff.should_process("src/index.ts") is True
    assert ff.should_process("components/Button.tsx") is True
    assert ff.should_process("main.go") is True
    assert ff.should_process("lib.rs") is True
    assert ff.should_process("config.json") is True
    assert ff.should_process("README.md") is True


def test_file_filter_ignored_directories():
    ff = FileFilter()
    assert ff.should_process(".git/HEAD") is False
    assert ff.should_process("node_modules/express/index.js") is False
    assert ff.should_process("__pycache__/main.cpython-310.pyc") is False
    assert ff.should_process(".venv/lib/site-packages/pytest.py") is False
    assert ff.should_process("dist/bundle.js") is False
    assert ff.should_process("build/output.js") is False
    assert ff.should_process("coverage/lcov.info") is False


def test_file_filter_ignored_binary_media_files():
    ff = FileFilter()
    assert ff.should_process("assets/logo.png") is False
    assert ff.should_process("images/photo.jpeg") is False
    assert ff.should_process("app.exe") is False
    assert ff.should_process("libsample.so") is False
    assert ff.should_process("archive.zip") is False
    assert ff.should_process("video.mp4") is False
    assert ff.should_process("audio.mp3") is False


def test_file_filter_ignored_generated_and_lockfiles():
    ff = FileFilter()
    assert ff.should_process("package-lock.json") is False
    assert ff.should_process("yarn.lock") is False
    assert ff.should_process("Cargo.lock") is False
    assert ff.should_process("jquery.min.js") is False
    assert ff.should_process("styles.min.css") is False


def test_file_filter_oversized_files():
    config = FileFilterConfig(max_file_size_bytes=100)
    ff = FileFilter(config=config)
    assert ff.should_process("small.py", size=50) is True
    assert ff.should_process("large.py", size=200) is False


def test_file_filter_directories():
    ff = FileFilter()
    assert ff.should_process("src", is_dir=True) is False
