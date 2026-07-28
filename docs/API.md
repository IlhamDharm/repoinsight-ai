# RepoInsight AI — API Reference

## Overview

| Property | Value |
|----------|-------|
| **Base URL** | `http://localhost:8000` |
| **API Prefix** | `/api/v1/` |
| **Auth Method** | JWT Bearer Token |
| **Content Type** | `application/json` |
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |

All responses follow a standard envelope format described in [Standard Response Format](#standard-response-format).

---

## Authentication

### Obtaining a Token

Register a new account or log in with existing credentials:

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
```

The login endpoint returns an `access_token` (JWT, HS256 algorithm, 24-hour expiry).

### Using the Token

Include the token in the `Authorization` header for all authenticated endpoints:

```
Authorization: Bearer <access_token>
```

Example with `curl`:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     http://localhost:8000/api/v1/auth/me
```

The frontend stores the token in `localStorage` under the key `repoinsight_token`.

### Token Lifecycle

| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Expiry | 1440 minutes (24 hours) |
| Payload | `{"sub": "<user_id>", "exp": "<timestamp>"}` |

When a token expires or is invalid, the API returns `401` with error code `authentication_error`.

---

## Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register a new user | No |
| POST | `/api/v1/auth/login` | Log in and receive access token | No |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |

---

### POST `/api/v1/auth/register`

Register a new user account.

**Authentication Required:** No

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ss1"
}
```

**Field Validation — `password`:**

| Rule | Detail |
|------|--------|
| Minimum length | 8 characters |
| Maximum length | 128 characters |
| Uppercase | At least 1 (`A-Z`) |
| Lowercase | At least 1 (`a-z`) |
| Digit | At least 1 (`0-9`) |
| Special character | At least 1 from `!@#$%^&*(),.?":{}|<>` |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true
  },
  "meta": {
    "request_id": "abc-123",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 201 | User registered successfully |
| 409 | Email already registered (`duplicate_resource`) |
| 422 | Validation error (invalid email, weak password) |

---

### POST `/api/v1/auth/login`

Authenticate and receive a JWT access token.

**Authentication Required:** No

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ss1"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  },
  "meta": {
    "request_id": "abc-456",
    "timestamp": "2026-07-28T12:05:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Login successful |
| 401 | Invalid email or password (`authentication_error`) |

---

### GET `/api/v1/auth/me`

Retrieve the profile of the currently authenticated user.

**Authentication Required:** Yes — `Authorization: Bearer <token>`

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true
  },
  "meta": {
    "request_id": "abc-789",
    "timestamp": "2026-07-28T12:10:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | User profile returned |
| 401 | Missing, invalid, or expired token (`authentication_error`) |

---

## Health Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/health/live` | Liveness probe | No |
| GET | `/api/v1/health/ready` | Readiness probe | No |
| GET | `/api/v1/health/db` | Database connectivity check | No |

---

### GET `/api/v1/health/live`

Liveness probe — confirms the service is running.

**Authentication Required:** No

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "RepoInsight AI API",
    "environment": "development"
  },
  "meta": {
    "request_id": "abc-001",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Service is alive |

---

### GET `/api/v1/health/ready`

Readiness probe — confirms the service is ready to accept requests.

**Authentication Required:** No

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "RepoInsight AI API",
    "environment": "development"
  },
  "meta": {
    "request_id": "abc-002",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Service is ready |

---

### GET `/api/v1/health/db`

Database connectivity check — executes `SELECT 1` against PostgreSQL.

**Authentication Required:** No

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": "postgresql",
    "dialect": "asyncpg"
  },
  "meta": {
    "request_id": "abc-003",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Database is reachable |
| 503 | Database is unavailable (`database_unavailable`) |

---

## Repository Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/repositories` | List user's repositories (paginated) | Yes |
| GET | `/api/v1/repositories/{repository_id}` | Get repository detail | Yes |
| POST | `/api/v1/repositories` | Register a GitHub repository | Yes |
| POST | `/api/v1/repositories/{repository_id}/scan` | Scan repository content | Yes |
| POST | `/api/v1/repositories/{repository_id}/analyze` | Start async analysis | Yes |
| GET | `/api/v1/repositories/{repository_id}/analyses` | Get analysis history (paginated) | Yes |

---

### GET `/api/v1/repositories`

List all repositories owned by the authenticated user, with pagination.

**Authentication Required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Min | Max | Description |
|-----------|------|---------|-----|-----|-------------|
| `page` | int | 1 | 1 | — | Page number |
| `page_size` | int | 20 | 1 | 100 | Items per page |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "github_repo_id": 123456789,
      "name": "my-project",
      "full_name": "username/my-project",
      "url": "https://github.com/username/my-project",
      "default_branch": "main",
      "visibility": "public",
      "created_at": "2026-07-20T10:00:00.000Z",
      "updated_at": "2026-07-28T12:00:00.000Z"
    }
  ],
  "meta": {
    "request_id": "abc-010",
    "timestamp": "2026-07-28T12:00:00.000Z",
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Repositories returned |
| 401 | Authentication required |

---

### GET `/api/v1/repositories/{repository_id}`

Retrieve details for a specific repository.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `repository_id` | int | Repository ID |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "github_repo_id": 123456789,
    "name": "my-project",
    "full_name": "username/my-project",
    "url": "https://github.com/username/my-project",
    "default_branch": "main",
    "visibility": "public",
    "created_at": "2026-07-20T10:00:00.000Z",
    "updated_at": "2026-07-28T12:00:00.000Z"
  },
  "meta": {
    "request_id": "abc-011",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Repository returned |
| 401 | Authentication required |
| 404 | Repository not found (`not_found`) |
| 403 | Not the repository owner (`forbidden`) |

---

### POST `/api/v1/repositories`

Register a GitHub repository by URL. If the repository already exists for the user, its metadata is updated.

**Authentication Required:** Yes

**Request Body:**

```json
{
  "url": "https://github.com/owner/repo"
}
```

**Field Validation — `url`:**

| Rule | Detail |
|------|--------|
| Required | Yes, non-empty |
| Format | Must match `https://github.com/<owner>/<repo>` |
| Max length | 2048 characters |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "github_repo_id": 123456789,
    "name": "repo",
    "full_name": "owner/repo",
    "url": "https://github.com/owner/repo",
    "default_branch": "main",
    "visibility": "public",
    "created_at": "2026-07-28T12:00:00.000Z",
    "updated_at": "2026-07-28T12:00:00.000Z"
  },
  "meta": {
    "request_id": "abc-012",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 201 | Repository registered (new or updated) |
| 401 | Authentication required |
| 404 | GitHub repository not found (`github_not_found`) |
| 422 | Invalid URL format (`validation_error`) |
| 429 | GitHub API rate limit exceeded (`github_rate_limit`) |
| 502 | GitHub API error (`external_service_error`) |

---

### POST `/api/v1/repositories/{repository_id}/scan`

Trigger a content scan of the repository. Fetches the file tree from GitHub, filters source files, detects languages, and counts lines.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `repository_id` | int | Repository ID |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "repository": "owner/repo",
    "branch": "main",
    "total_files": 42,
    "total_source_files": 15,
    "total_lines": 3200,
    "languages": {
      "Python": 2400,
      "TypeScript": 800
    },
    "files": [
      {
        "path": "src/main.py",
        "language": "Python",
        "size": 1024,
        "lines": 45
      }
    ]
  },
  "meta": {
    "request_id": "abc-013",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Scan completed successfully |
| 401 | Authentication required |
| 404 | Repository not found (`not_found`) |
| 403 | Not the repository owner (`forbidden`) |
| 502 | GitHub API error during scan (`external_service_error`) |
| 504 | GitHub API timeout (`github_timeout`) |

---

### POST `/api/v1/repositories/{repository_id}/analyze`

Schedule an asynchronous AI static analysis job. Returns immediately with status `202 Accepted`. Poll the analysis endpoint or use the background task to get results.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `repository_id` | int | Repository ID |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "analysis_id": 1,
    "repository_id": 1,
    "status": "pending"
  },
  "meta": {
    "request_id": "abc-014",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 202 | Analysis job scheduled |
| 401 | Authentication required |
| 404 | Repository not found (`not_found`) |
| 403 | Not the repository owner (`forbidden`) |

---

### GET `/api/v1/repositories/{repository_id}/analyses`

Retrieve paginated analysis history for a repository.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `repository_id` | int | Repository ID |

**Query Parameters:**

| Parameter | Type | Default | Min | Max | Description |
|-----------|------|---------|-----|-----|-------------|
| `page` | int | 1 | 1 | — | Page number |
| `page_size` | int | 20 | 1 | 100 | Items per page |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "status": "completed",
      "created_at": "2026-07-28T12:00:00.000Z",
      "completed_at": "2026-07-28T12:02:30.000Z",
      "score": 85
    }
  ],
  "meta": {
    "request_id": "abc-015",
    "timestamp": "2026-07-28T12:00:00.000Z",
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Analysis history returned |
| 401 | Authentication required |
| 404 | Repository not found (`not_found`) |
| 403 | Not the repository owner (`forbidden`) |

---

## Analysis Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/analyses/{analysis_id}` | Get analysis status and results | Yes |
| GET | `/api/v1/analyses/{analysis_id}/compare/{previous_analysis_id}` | Compare two analyses | Yes |

---

### GET `/api/v1/analyses/{analysis_id}`

Retrieve the full status and results of a specific analysis.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `analysis_id` | int | Analysis ID |

**Response (200 OK) — Completed Analysis:**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "repository_id": 1,
    "status": "completed",
    "started_at": "2026-07-28T12:00:00.000Z",
    "completed_at": "2026-07-28T12:02:30.000Z",
    "created_at": "2026-07-28T11:59:55.000Z",
    "updated_at": "2026-07-28T12:02:30.000Z",
    "summary": {
      "total_files": 42,
      "total_source_files": 15,
      "total_lines": 3200,
      "dominant_language": "Python",
      "languages": {
        "Python": { "files": 10, "lines": 2400, "percentage": 75.0 },
        "TypeScript": { "files": 5, "lines": 800, "percentage": 25.0 }
      }
    },
    "scores": {
      "code_quality": 85,
      "architecture": 78,
      "maintainability": 90
    },
    "findings": [
      {
        "rule_id": "CQ-001",
        "severity": "warning",
        "category": "code_quality",
        "title": "Long function detected",
        "description": "Function exceeds 50 lines",
        "file_path": "src/main.py",
        "recommendation": "Split into smaller functions"
      }
    ],
    "recommendations": [
      "Consider adding type hints to improve code readability",
      "Split large functions into smaller, testable units"
    ],
    "error": null
  },
  "meta": {
    "request_id": "abc-020",
    "timestamp": "2026-07-28T12:05:00.000Z"
  }
}
```

**Response (200 OK) — Failed Analysis:**

```json
{
  "success": true,
  "data": {
    "id": 2,
    "repository_id": 1,
    "status": "failed",
    "started_at": "2026-07-28T13:00:00.000Z",
    "completed_at": null,
    "created_at": "2026-07-28T12:59:55.000Z",
    "updated_at": "2026-07-28T13:00:05.000Z",
    "summary": null,
    "scores": null,
    "findings": null,
    "recommendations": null,
    "error": {
      "code": "ANALYSIS_FAILED",
      "message": "Analysis failed. Please check the error details or retry."
    }
  },
  "meta": {
    "request_id": "abc-021",
    "timestamp": "2026-07-28T13:05:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Analysis data returned (status may be `pending`, `running`, `completed`, or `failed`) |
| 401 | Authentication required |
| 404 | Analysis not found (`not_found`) |
| 403 | Not the analysis owner (`forbidden`) |

---

### GET `/api/v1/analyses/{analysis_id}/compare/{previous_analysis_id}`

Compare two analysis results from the same repository. Returns score changes, category-level deltas, and finding count differences.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `analysis_id` | int | Current (newer) analysis ID |
| `previous_analysis_id` | int | Previous (older) analysis ID |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "current_analysis_id": 2,
    "previous_analysis_id": 1,
    "score_change": 5,
    "current_score": 90,
    "previous_score": 85,
    "category_changes": {
      "code_quality": 3,
      "architecture": 5,
      "maintainability": 7
    },
    "findings_change": -2
  },
  "meta": {
    "request_id": "abc-030",
    "timestamp": "2026-07-28T14:00:00.000Z"
  }
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Comparison data returned |
| 401 | Authentication required |
| 404 | One or both analyses not found (`not_found`) |
| 403 | Not the owner of one or both analyses (`forbidden`) |

---

## Dashboard Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/dashboard/stats` | Get dashboard summary statistics | Yes |

---

### GET `/api/v1/dashboard/stats`

Retrieve aggregate statistics and recent analysis activity for the authenticated user.

**Authentication Required:** Yes

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "repository_count": 5,
    "analysis_count": 12,
    "recent_analyses": [
      {
        "id": 12,
        "status": "completed",
        "created_at": "2026-07-28T12:00:00.000Z",
        "completed_at": "2026-07-28T12:02:30.000Z",
        "repository_id": 1,
        "repository_name": "owner/my-project",
        "score": 85
      },
      {
        "id": 11,
        "status": "running",
        "created_at": "2026-07-28T11:30:00.000Z",
        "completed_at": null,
        "repository_id": 2,
        "repository_name": "owner/other-project",
        "score": null
      }
    ]
  },
  "meta": {
    "request_id": "abc-040",
    "timestamp": "2026-07-28T12:00:00.000Z"
  }
}
```

- `recent_analyses` contains up to the 5 most recent analyses.
- `score` is the average of all numeric score values for completed analyses, or `null` for non-completed analyses.

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Dashboard stats returned |
| 401 | Authentication required |

---

## Standard Response Format

Every API response follows a consistent envelope structure.

### Success Response

```json
{
  "success": true,
  "data": "<payload>",
  "meta": {
    "request_id": "<uuid>",
    "timestamp": "<ISO 8601>"
  }
}
```

For paginated endpoints, `meta` includes additional fields:

```json
{
  "meta": {
    "request_id": "<uuid>",
    "timestamp": "<ISO 8601>",
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "message": "Human-readable error description",
    "code": "error_code_identifier",
    "details": "<optional additional context>"
  },
  "meta": {
    "request_id": "<uuid>",
    "timestamp": "<ISO 8601>"
  }
}
```

The `details` field is optional and may contain validation error details or other context-specific information.

---

## Error Codes Reference

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 401 | `authentication_error` | Missing, invalid, or expired JWT token |
| 401 | `github_auth_error` | GitHub API authentication failed (invalid/missing token) |
| 403 | `forbidden` | Authenticated but not authorized to access the resource |
| 404 | `not_found` | Requested resource does not exist |
| 404 | `github_not_found` | GitHub repository or resource not found |
| 409 | `duplicate_resource` | Resource already exists (e.g., duplicate email registration) |
| 422 | `validation_error` | Request body or query parameters failed validation |
| 429 | `github_rate_limit` | GitHub API rate limit exceeded |
| 500 | `internal_server_error` | Unexpected server error |
| 502 | `external_service_error` | Error communicating with an external service (GitHub) |
| 503 | `database_unavailable` | Database is unreachable or degraded |
| 504 | `github_timeout` | GitHub API request timed out |

### Password Validation Errors

Password validation failures return HTTP 422 with code `validation_error` and a descriptive message:

| Rule | Error Message |
|------|---------------|
| Too short | Password harus minimal 8 karakter |
| Too long | Password maksimal 128 karakter |
| No uppercase | Password harus mengandung minimal 1 huruf besar |
| No lowercase | Password harus mengandung minimal 1 huruf kecil |
| No digit | Password harus mengandung minimal 1 angka |
| No special char | Password harus mengandung minimal 1 karakter spesial |
