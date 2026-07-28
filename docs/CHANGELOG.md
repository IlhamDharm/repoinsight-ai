# Changelog

All notable changes to RepoInsight AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-28

Initial release of RepoInsight AI — an AI-powered GitHub repository analysis platform.

### Backend Foundation
- FastAPI application with modular router architecture
- SQLAlchemy ORM with async support for PostgreSQL
- Pydantic models for request/response validation
- Alembic migration framework integrated
- Health check endpoints (liveness, readiness, startup)
- Request ID tracking via X-Request-ID header (UUID per request)
- Structured logging with correlation IDs

### Authentication & Security
- JWT Bearer token authentication (HS256 signing)
- bcrypt password hashing via passlib
- Password strength enforcement (min 8, max 128 chars; uppercase, lowercase, digit, special char)
- User registration and login endpoints
- Token refresh endpoint
- Ownership verification on all resource operations
- Security headers middleware (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy)
- HSTS header in production mode
- CORS middleware with configurable origins
- X-Request-ID input sanitization (regex whitelist)
- Environment-based secrets management (no hardcoded credentials)

### Database
- User model with secure credential storage
- Repository model with GitHub metadata fields
- Analysis model with status tracking and result storage
- One-to-many relationships (User → Repositories → Analyses)
- Database migration scripts via Alembic
- N+1 query optimization for repository listings

### GitHub Integration
- GitHub API client for repository metadata fetching
- Repository cloning and file structure analysis
- Language distribution detection
- Commit history analysis
- README and documentation parsing
- Contributor statistics aggregation

### AI Analysis Engine
- Automated code quality scoring
- Security vulnerability pattern detection
- Documentation completeness analysis
- Dependency health assessment
- Maintainability index calculation
- Analysis result storage with structured JSON output
- Asynchronous analysis execution

### Async Workflow & History
- Background task processing for long-running analyses
- Analysis status tracking (pending, running, completed, failed)
- Analysis history with full result retrieval
- Repository analysis comparison support
- Timestamp-based ordering and filtering

### Frontend Foundation
- React 19 application with Vite build tooling
- React Router v7 with nested route layout
- TypeScript throughout the frontend codebase
- Centralized API client with interceptors
- Auth context with token persistence
- Protected route components
- Responsive layout with mobile support

### UI/UX — Dark-Tech Theme
- Custom design token system (colors, spacing, typography, shadows)
- Dark-tech color palette with accent highlights
- Redesigned navigation bar with responsive collapse
- Landing page with feature showcase
- Login and registration pages with form validation
- Dashboard with repository list and quick stats
- Repository detail page with metadata display
- Analysis results page with structured data visualization
- Loading states and skeleton screens
- Toast notification system
- Consistent iconography and spacing

### API Endpoints (15 total)
- Auth: register, login, token refresh (3)
- Health: liveness, readiness, startup (3)
- Repositories: CRUD operations with ownership checks (6)
- Analyses: trigger analysis, get analysis results (2)
- Dashboard: aggregated stats (1)

### Production Readiness
- Dead code removal across backend and frontend
- React ErrorBoundary for graceful crash handling
- Accessibility audit and ARIA attribute fixes
- Security headers hardened for production deployment
- Environment-based configuration for all secrets
- CORS origins configurable per environment

### Testing
- 212 backend unit and integration tests
- 12 frontend component tests
- Authentication flow test coverage
- API endpoint validation tests
- Database model and relationship tests
