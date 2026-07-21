# RepoInsight AI Backend

This module contains the initial backend foundation for RepoInsight AI.

## Current feature

- FastAPI application bootstrap
- Structured app package following clean architecture principles
- Health endpoints for liveness and readiness
- Automated tests for the initial API surface

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
