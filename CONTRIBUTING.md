# Contributing to RepoInsight AI

Thank you for your interest in contributing to RepoInsight AI! This guide will help you get started and ensure a smooth contribution process.

---

## Code of Conduct

Be respectful, constructive, and professional. We are committed to providing a welcoming and inclusive experience for everyone. Harassment, discrimination, and bad-faith behavior are not tolerated.

---

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/<your-username>/repoinsight-ai.git
cd repoinsight-ai
git remote add upstream https://github.com/original-owner/repoinsight-ai.git
```

### 2. Create a Branch

```bash
git checkout -b feat/my-feature
```

Use a descriptive branch name prefixed with the type: `feat/`, `fix/`, `chore/`, `docs/`.

### 3. Install Dependencies

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

---

## Development Setup

### Environment Variables

Copy the example environment file and configure your local settings:

```bash
cp .env.example .env
```

At minimum, set:

- `DATABASE_URL` — your local PostgreSQL connection string
- `SECRET_KEY` — any random string for local development

### Database

```bash
# Create the database
createdb repoinsight

# Run migrations
cd backend
alembic upgrade head
```

### Start the Servers

```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

The backend runs on `http://localhost:8000` and the frontend on `http://localhost:5173`.

---

## Project Structure

```
repoinsight-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # Business logic
│   │   ├── middleware/          # Security headers, request tracking
│   │   └── utils/               # Shared utilities
│   ├── migrations/              # Alembic migration scripts
│   └── tests/                   # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Route-level page components
│   │   ├── contexts/            # React contexts (auth, etc.)
│   │   ├── api/                 # API client and endpoints
│   │   ├── hooks/               # Custom React hooks
│   │   └── styles/              # Design tokens and global styles
│   └── public/                  # Static assets
└── docs/                        # Project documentation
```

---

## Coding Standards

### Python (Backend)

- Follow **PEP 8** style guidelines
- Use type hints on all function signatures
- Keep functions focused and under 40 lines where possible
- Use Pydantic models for all data validation — never trust raw input
- Prefer async functions for I/O-bound operations
- No hardcoded strings for configuration — use environment variables

```python
# Good
async def get_repository(repo_id: int, user: User) -> Repository:
    repo = await db.get(Repository, repo_id)
    if not repo or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
```

### TypeScript (Frontend)

- Use **strict mode** in TypeScript configuration
- Prefer `interface` over `type` for object shapes
- Use functional components with hooks — no class components
- Keep components under 150 lines; extract sub-components when larger
- Handle loading and error states explicitly in every data-fetching component

```tsx
// Good
const RepositoryCard = ({ repo }: { repo: Repository }) => {
  return (
    <Link to={`/repositories/${repo.id}`}>
      <h3>{repo.name}</h3>
      <p>{repo.description}</p>
    </Link>
  );
};
```

---

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

### Types

| Type       | Description                                      |
|------------|--------------------------------------------------|
| `feat`     | New feature                                      |
| `fix`      | Bug fix                                          |
| `docs`     | Documentation changes only                       |
| `style`    | Formatting, missing semicolons (no code change)  |
| `refactor` | Code restructuring without behavior change       |
| `test`     | Adding or updating tests                         |
| `chore`    | Build, CI, dependencies, tooling                 |

### Examples

```
feat(analysis): add maintainability index scoring
fix(auth): handle expired refresh tokens gracefully
docs: update API endpoint documentation
test(repositories): add ownership verification tests
```

---

## Pull Request Process

1. **Update your branch** against `main` before submitting:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks** before pushing:
   ```bash
   # Backend
   cd backend && pytest

   # Frontend
   cd frontend && npm test
   ```

3. **Push and open a PR** against `main`:
   ```bash
   git push origin feat/my-feature
   ```

4. **PR description** should include:
   - What changed and why
   - Link to the related issue (if any)
   - Screenshots or recordings for UI changes
   - Any breaking changes or migration requirements

5. **Respond to review feedback** promptly. At least one approval is required before merge.

---

## Testing Requirements

- All new features must include tests
- All bug fixes must include a regression test
- Backend tests use `pytest` with async fixtures
- Frontend tests use Vitest with React Testing Library
- Target: no decrease in overall coverage

```bash
# Backend with coverage
cd backend
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm test
```

---

## Code Review Guidelines

When reviewing others' PRs:

- Focus on correctness, security, and maintainability
- Check for input validation and error handling
- Verify tests cover the changed logic
- Ensure documentation is updated if APIs or behavior change
- Be constructive — suggest improvements, don't just point out problems

---

## Issue Reporting

When reporting a bug or requesting a feature:

1. Check existing issues to avoid duplicates
2. Use a clear, descriptive title
3. Include steps to reproduce (for bugs)
4. Specify your environment (OS, Python version, Node version, browser)
5. For feature requests, explain the use case and expected behavior
