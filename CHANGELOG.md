# Changelog

## [0.1.0] - 2026-07-16

### Added
- Initial backend foundation for RepoInsight AI using FastAPI
- Modular app structure following clean architecture conventions
- Health endpoints for liveness and readiness
- Initial pytest coverage for health routes

### Files changed
- backend/app/main.py
- backend/app/core/config.py
- backend/app/api/v1/health.py
- backend/app/schemas/health.py
- backend/app/tests/test_health.py
- backend/requirements.txt
- backend/README.md

### New dependencies
- fastapi
- uvicorn
- pytest
- httpx
- pydantic-settings

### Commit message
- feat(backend): scaffold initial API foundation
