from app.services.language_detector import detect_language


def test_detect_language_standard_extensions():
    assert detect_language("app/main.py") == "Python"
    assert detect_language("src/index.js") == "JavaScript"
    assert detect_language("components/App.tsx") == "TypeScript"
    assert detect_language("server/main.go") == "Go"
    assert detect_language("src/main.rs") == "Rust"
    assert detect_language("App.java") == "Java"
    assert detect_language("index.php") == "PHP"
    assert detect_language("main.cpp") == "C++"
    assert detect_language("core.c") == "C"
    assert detect_language("Program.cs") == "C#"
    assert detect_language("schema.sql") == "SQL"
    assert detect_language("index.html") == "HTML"
    assert detect_language("style.css") == "CSS"
    assert detect_language("config.json") == "JSON"
    assert detect_language("docker-compose.yml") == "YAML"
    assert detect_language("Cargo.toml") == "TOML"
    assert detect_language("README.md") == "Markdown"


def test_detect_language_unknown_extension():
    assert detect_language("binary.bin") == "Unknown"
    assert detect_language("script.sh") == "Unknown"
    assert detect_language("Dockerfile") == "Unknown"
    assert detect_language(".gitignore") == "Unknown"
