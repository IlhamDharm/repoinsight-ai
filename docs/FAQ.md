# Frequently Asked Questions

## General

### What is RepoInsight AI?

RepoInsight AI is an AI-powered GitHub repository analysis platform. It connects to your GitHub repositories, performs automated code quality and security analysis, and presents actionable insights through a modern web dashboard.

### What tech stack does it use?

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, Pydantic
- **Frontend**: React 19, TypeScript, Vite, React Router v7
- **Database**: PostgreSQL 15+
- **Authentication**: JWT (HS256), bcrypt password hashing

### Is it free?

Yes. RepoInsight AI is released under the MIT license. You can use, modify, and distribute it freely.

---

## Installation & Setup

### What are the prerequisites?

- Python 3.12 or higher
- Node.js 20+ and npm/yarn
- PostgreSQL 15 or higher
- Git

### Can I use SQLite instead of PostgreSQL?

No. The application uses async SQLAlchemy features that require a PostgreSQL backend. SQLite does not support the async drivers used in this project.

### How do I install the backend?

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### How do I install the frontend?

```bash
cd frontend
npm install
npm run dev
```

---

## Development

### How do I add a new API endpoint?

1. Create or update a router file in `backend/app/routers/`
2. Define Pydantic schemas in `backend/app/schemas/`
3. Add database model changes if needed in `backend/app/models/`
4. Create an Alembic migration: `alembic revision --autogenerate -m "description"`
5. Write tests in `backend/tests/`

### How do I add a new database migration?

```bash
alembic revision --autogenerate -m "add feature x"
alembic upgrade head
```

Always review the generated migration file before applying it.

### How do I run the tests?

**Backend:**
```bash
cd backend
pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

### How do I reset the database?

```bash
alembic downgrade base
alembic upgrade head
```

---

## API

### Is authentication required?

Yes. Most endpoints require a valid JWT Bearer token in the `Authorization` header. Public endpoints are limited to `/health/*`, `/api/auth/register`, and `/api/auth/login`.

### How do I get an authentication token?

Send a POST request to `/api/auth/login` with your email and password. The response includes an `access_token` and `refresh_token`.

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "YourPass1!"}'
```

### How do I refresh my token?

Send a POST request to `/api/auth/refresh` with your refresh token in the request body.

### Does the API support pagination?

Yes. List endpoints support `skip` and `limit` query parameters for pagination.

### How are errors returned?

All errors follow a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

HTTP status codes are used conventionally (400, 401, 403, 404, 422, 500).

### Is there rate limiting?

Rate limiting is not implemented in v0.1.0. It is planned for a future release.

---

## Database

### How do I back up the database?

```bash
pg_dump -U postgres repoinsight > backup.sql
```

### How do I restore a backup?

```bash
psql -U postgres repoinsight < backup.sql
```

### Can I roll back a migration?

```bash
alembic downgrade -1     # Roll back one step
alembic downgrade base   # Roll back to the beginning
```

---

## Deployment

### Is it production ready?

RepoInsight AI v0.1.0 includes production-readiness improvements (security headers, ErrorBoundary, dead code removal, N+1 query fixes), but has not yet been hardened with Docker, CI/CD, or monitoring. Use it in production with appropriate caution.

### Does it support Docker?

Docker support is planned for Phase 7 of the roadmap. Currently, manual deployment is required.

### How do I scale the application?

The backend is stateless (tokens are self-contained JWTs), so you can run multiple instances behind a load balancer. Ensure all instances share the same PostgreSQL database and environment configuration.

---

## Troubleshooting

### I get "Invalid token" errors

Your JWT may have expired. Use the refresh token endpoint to obtain a new access token, or log in again.

### The frontend shows "Network Error"

Ensure the backend is running and the `VITE_API_URL` environment variable in the frontend points to the correct backend URL (default: `http://localhost:8000`).

### Database connection refused

Verify PostgreSQL is running and the `DATABASE_URL` environment variable is correct. Check that the database `repoinsight` exists.

### Migration errors after pulling new code

Run `alembic upgrade head` to apply any new migrations. If you encounter conflicts, check the migration history with `alembic history`.

### Analysis fails or stays in "pending"

Check backend logs for errors in the GitHub API integration. Ensure your GitHub token (if configured) has the required repository permissions.
