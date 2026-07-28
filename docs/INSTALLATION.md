# RepoInsight AI — Installation Guide

## Overview

RepoInsight AI is an AI-powered GitHub repository analysis platform built with FastAPI (Python 3.12) on the backend and React 19 + TypeScript + Vite on the frontend. This guide covers local development setup from scratch.

---

## System Requirements

| Component | Minimum Version | Notes |
|-----------|-----------------|-------|
| **Python** | 3.12+ | Required for backend |
| **Node.js** | 18+ | Required for frontend |
| **npm** | 9+ | Bundled with Node.js |
| **PostgreSQL** | 14+ | Async driver: `asyncpg` |
| **Git** | 2.x+ | For cloning and repository scanning |
| **OS** | Windows, macOS, or Linux | Windows instructions included |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/username/repoinsight-ai.git
cd repoinsight-ai

# 2. Set up backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
cp .env.example .env            # Edit database URL as needed
createdb repoinsight_ai
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Set up frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Detailed Installation

### Prerequisites

#### Python 3.12+

Download from [python.org](https://www.python.org/downloads/). Verify installation:

```bash
python --version   # Should output Python 3.12.x or later
```

#### Node.js 18+

Download from [nodejs.org](https://nodejs.org/). Verify installation:

```bash
node --version     # Should output v18.x.x or later
npm --version      # Should output 9.x.x or later
```

#### PostgreSQL 14+

Install from [postgresql.org](https://www.postgresql.org/download/) or use your system package manager. Ensure the `psql` CLI is available:

```bash
psql --version     # Should output 14.x or later
```

#### Git

```bash
git --version      # Should output 2.x or later
```

---

### Clone Repository

```bash
git clone https://github.com/username/repoinsight-ai.git
cd repoinsight-ai
```

---

### Backend Setup

#### 1. Create and Activate Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate
```

#### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies installed:

| Package | Purpose |
|---------|---------|
| `fastapi==0.115.0` | Web framework |
| `uvicorn[standard]==0.32.0` | ASGI server |
| `sqlalchemy[asyncio]==2.0.36` | Async ORM |
| `asyncpg==0.30.0` | PostgreSQL async driver |
| `alembic==1.14.1` | Database migrations |
| `passlib[bcrypt]==1.7.4` | Password hashing |
| `bcrypt==4.2.1` | bcrypt backend |
| `python-jose[cryptography]==3.5.0` | JWT token handling |
| `python-multipart==0.0.32` | Form data parsing |
| `email-validator>=2.0.0` | Email validation |

#### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and edit the required values. At minimum, set:

```env
REPOINSIGHT_DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/repoinsight_ai
REPOINSIGHT_JWT_SECRET_KEY=your-secure-random-secret-key
REPOINSIGHT_GITHUB_TOKEN=ghp_your_github_personal_access_token
```

See [Configuration](#configuration) for all available variables.

---

### Frontend Setup

#### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Frontend Environment (Optional)

The frontend works out of the box with the default configuration. To customize:

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

The Vite dev server runs on port 3000 and proxies `/api` requests to the backend at port 8000.

---

## Configuration

### Backend Environment Variables

All backend environment variables use the `REPOINSIGHT_` prefix.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `REPOINSIGHT_APP_NAME` | `RepoInsight AI API` | No | Application name displayed in responses |
| `REPOINSIGHT_ENVIRONMENT` | `development` | No | Environment mode (`development`, `production`) |
| `REPOINSIGHT_DEBUG` | `false` | No | Enable debug mode |
| `REPOINSIGHT_DATABASE_URL` | `postgresql+asyncpg://postgres:12345678@localhost:5432/repoinsight_ai` | **Yes** | PostgreSQL connection string |
| `REPOINSIGHT_DATABASE_ECHO` | `false` | No | Log all SQL statements |
| `REPOINSIGHT_GITHUB_API_URL` | `https://api.github.com` | No | GitHub API base URL |
| `REPOINSIGHT_GITHUB_TOKEN` | `""` | **Yes** | GitHub Personal Access Token for API access |
| `REPOINSIGHT_GITHUB_TIMEOUT` | `10.0` | No | HTTP timeout for GitHub API calls (seconds) |
| `REPOINSIGHT_JWT_SECRET_KEY` | `repoinsight-dev-secret-key-change-in-production-2026` | **Yes** | Secret key for JWT signing — **change in production** |
| `REPOINSIGHT_JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `REPOINSIGHT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | No | Token expiry time (default: 24 hours) |

### Frontend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Database Setup

### 1. Create the Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE repoinsight_ai;

# Exit
\q
```

Or using the command line:

```bash
createdb -U postgres repoinsight_ai
```

### 2. Run Migrations

From the `backend` directory with the virtual environment activated:

```bash
alembic upgrade head
```

This creates all required tables:

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, hashed password, active status) |
| `repositories` | Registered GitHub repositories |
| `analyses` | Analysis jobs and results |
| `repository_files` | Scanned file metadata |

### 3. Create a Superuser (Optional)

```bash
python -c "
from app.core.database import get_session_factory
from app.db.models import User
from app.core.security import hash_password
import asyncio

async def create_user():
    _, factory = get_session_factory()
    async with factory() as session:
        user = User(
            email='admin@repoinsight.dev',
            hashed_password=hash_password('Admin@1234'),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f'Created user: {user.email} (id={user.id})')

asyncio.run(create_user())
"
```

---

## Running the Application

### Backend Only

```bash
cd backend
.venv\Scripts\activate       # Windows
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`.

### Frontend Only

```bash
cd frontend
npm run dev
```

The dev server is available at `http://localhost:3000`.

### Both Simultaneously

Open two terminal windows:

**Terminal 1 — Backend:**
```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### Available Scripts

#### Backend

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload --port 8000` | Start development server with hot reload |
| `alembic upgrade head` | Apply all pending database migrations |
| `alembic revision --autogenerate -m "description"` | Generate a new migration |
| `pytest` | Run the test suite (212 tests) |

#### Frontend

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server on port 3000 |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build |
| `npm run test` | Run the test suite (12 tests) |
| `npm run test:watch` | Run tests in watch mode |
| `npm run lint` | Run oxlint linter |

---

## Verification

### 1. Health Check

```bash
# Liveness
curl http://localhost:8000/api/v1/health/live

# Readiness
curl http://localhost:8000/api/v1/health/ready

# Database
curl http://localhost:8000/api/v1/health/db
```

All three should return `"success": true`.

### 2. Register and Login

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234"}'

# Use the returned access_token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <your_token>"
```

### 3. Interactive API Docs

Open http://localhost:8000/docs in your browser to access the Swagger UI. You can test all endpoints interactively from there.

---

## Troubleshooting

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| `ModuleNotFoundError: No module named 'app'` | Virtual environment not activated or wrong directory | Activate `.venv` and run from `backend/` |
| `asyncpg.exceptions.ConnectionDoesNotExistError` | PostgreSQL not running or wrong connection string | Start PostgreSQL and verify `REPOINSIGHT_DATABASE_URL` |
| `FATAL: database "repoinsight_ai" does not exist` | Database not created | Run `createdb -U postgres repoinsight_ai` |
| `alembic.util.exc.CommandError: Can't create migrations` | Database not at latest revision or missing tables | Run `alembic upgrade head` first |
| `401 Authentication error` on API calls | Missing or invalid JWT token | Include `Authorization: Bearer <token>` header |
| `ECONNREFUSED` on frontend API calls | Backend not running | Start the backend on port 8000 |
| Frontend shows blank page | Node modules not installed | Run `npm install` in `frontend/` |
| `GitHub API rate limit exceeded` (429) | Too many unauthenticated GitHub requests | Set a valid `REPOINSIGHT_GITHUB_TOKEN` |
| `GitHub API authentication failed` (401) | Invalid or expired GitHub token | Generate a new Personal Access Token at github.com/settings/tokens |
| Port 8000 already in use | Another process using the port | Kill the process or use `--port 8001` |
| Port 3000 already in use | Another Vite dev server running | Kill it or Vite will auto-increment the port |
| `bcrypt` install fails on Windows | Missing C compiler | Install Visual Studio Build Tools or use `pip install bcrypt` (pure Python fallback) |
| `ssl.SSLCertVerificationError` during `pip install` | Corporate proxy or outdated certificates | Set `PIP_TRUSTED_HOST=pypi.org` or use `--trusted-host` flags |

---

## FAQ

**Q: Do I need a GitHub token to use the API?**

A: Yes. A GitHub Personal Access Token is required for repository registration, scanning, and analysis. Generate one at https://github.com/settings/tokens with `repo` scope. Set it as `REPOINSIGHT_GITHUB_TOKEN` in your `.env` file.

**Q: Can I use SQLite instead of PostgreSQL?**

A: No. The project uses `asyncpg` (an async PostgreSQL driver) and Alembic migrations configured for PostgreSQL. SQLite is not supported.

**Q: How long do JWT tokens last?**

A: Tokens expire after 1440 minutes (24 hours) by default. Configure via `REPOINSIGHT_ACCESS_TOKEN_EXPIRE_MINUTES`.

**Q: How do I run tests?**

A: Backend: `cd backend && pytest`. Frontend: `cd frontend && npm run test`. The project has 212 backend tests and 12 frontend tests.

**Q: What does the `/analyze` endpoint do?**

A: It schedules an asynchronous background task that performs AI static analysis on the repository. Returns immediately with HTTP 202. Use `GET /api/v1/analyses/{analysis_id}` to poll for completion.

**Q: How do I generate a new Alembic migration after model changes?**

A: Run from the `backend` directory:
```bash
alembic revision --autogenerate -m "description of changes"
alembic upgrade head
```

**Q: The frontend cannot reach the backend. What should I check?**

A: Ensure the backend is running on port 8000. The Vite dev server automatically proxies `/api` requests to `http://localhost:8000`. Check `VITE_API_BASE_URL` in your frontend `.env` if you changed the backend port.

**Q: How do I reset the database?**

A: Drop and recreate the database, then re-run migrations:
```bash
psql -U postgres -c "DROP DATABASE repoinsight_ai;"
psql -U postgres -c "CREATE DATABASE repoinsight_ai;"
cd backend && alembic upgrade head
```
