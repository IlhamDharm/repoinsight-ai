# Security Policy

This document describes the security measures implemented in RepoInsight AI v0.1.0 and provides guidelines for secure deployment.

---

## 1. Security Overview

RepoInsight AI takes a defense-in-depth approach to security. Authentication, input validation, secure headers, and database-level protections work together to reduce the attack surface. No security mechanism is treated as a single point of failure.

---

## 2. Authentication

### JWT Bearer Tokens

- **Algorithm**: HS256 (HMAC-SHA256)
- **Token types**: Access token and refresh token
- **Transmission**: `Authorization: Bearer <token>` header
- **Storage**: Client-side localStorage (recommended: httpOnly cookies for production)

### Token Lifecycle

1. User registers or logs in → receives access + refresh tokens
2. Access token is sent with every authenticated request
3. When access token expires, client uses refresh token to obtain a new one
4. Refresh token expiry forces re-authentication

### Password Hashing

- **Algorithm**: bcrypt via passlib
- Salt is automatically generated per password
- Passwords are never stored in plaintext

### Password Strength Rules

| Rule       | Requirement                        |
|------------|------------------------------------|
| Min length | 8 characters                       |
| Max length | 128 characters                     |
| Uppercase  | At least one uppercase letter (A-Z) |
| Lowercase  | At least one lowercase letter (a-z) |
| Digit      | At least one digit (0-9)           |
| Special    | At least one special character     |

Passwords that do not meet all requirements are rejected at the API level with a 400 response.

---

## 3. Authorization

### Ownership Verification

All resource operations (read, update, delete) verify that the authenticated user owns the resource. Users cannot access, modify, or delete repositories or analyses belonging to other users.

### 403 Responses

When a user attempts to access a resource they do not own, the API returns:

```json
{
  "detail": "Not authorized to access this resource"
}
```

with HTTP status `403 Forbidden`.

---

## 4. Input Validation

### Pydantic Models

All API request bodies and query parameters are validated using Pydantic models. Invalid input is rejected before reaching business logic.

### URL Validation

Repository URLs are validated against expected GitHub URL patterns before processing.

### Sanitization

User-supplied strings that appear in responses or logs are treated as untrusted. The `X-Request-ID` header is sanitized using a regex whitelist to prevent injection into log pipelines.

---

## 5. Security Headers

The following security headers are applied to all responses via middleware:

| Header                        | Value (Development)       | Value (Production)          |
|-------------------------------|---------------------------|-----------------------------|
| X-Content-Type-Options       | nosniff                   | nosniff                     |
| X-Frame-Options              | DENY                      | DENY                        |
| X-XSS-Protection             | 0                         | 0                           |
| Referrer-Policy               | strict-origin-when-cross-origin | strict-origin-when-cross-origin |
| Strict-Transport-Security    | —                         | max-age=31536000; includeSubDomains |

> **Note**: `X-XSS-Protection: 0` is intentional. Modern browsers have deprecated this header, and setting it to `1` can introduce vulnerabilities in older browsers.

---

## 6. CORS Configuration

- **Development**: `allow_origins=["*"]` — all origins permitted for local development
- **Production**: Origins must be explicitly configured via the `CORS_ORIGINS` environment variable

```bash
# Production example
CORS_ORIGINS=["https://app.example.com"]
```

---

## 7. SQL Injection Prevention

All database queries use SQLAlchemy ORM with parameterized query construction. Raw SQL is not used in application code. This prevents SQL injection attacks at the ORM layer.

---

## 8. Secrets Management

### Environment Variables

All secrets and sensitive configuration are loaded from environment variables:

| Variable         | Description                    |
|------------------|--------------------------------|
| `DATABASE_URL`   | PostgreSQL connection string   |
| `SECRET_KEY`     | JWT signing key                |
| `CORS_ORIGINS`   | Allowed CORS origins           |

### Never in Code

- No API keys, passwords, or tokens are hardcoded in source files
- `.env` files are excluded from version control via `.gitignore`
- Default values are used only for non-sensitive configuration

---

## 9. Request Tracking

Every incoming request receives a unique `X-Request-ID` (UUID v4). This ID:

- Is returned in the response headers
- Is included in all log entries for the request
- Enables end-to-end request tracing across backend services

The `X-Request-ID` value is validated against a regex whitelist (`^[a-zA-Z0-9-]+$`) to prevent log injection.

---

## 10. Known Security Considerations

| Area                     | Status in v0.1.0                              |
|--------------------------|-----------------------------------------------|
| HTTPS enforcement        | HSTS header in production; TLS termination at reverse proxy |
| Rate limiting            | Not implemented — recommended for production  |
| CSRF protection          | Token-based auth mitigates CSRF; SameSite cookies recommended |
| Content Security Policy  | Not implemented — recommended for production  |
| Audit logging            | Request-ID logging present; no dedicated audit trail |
| Dependency scanning      | Not automated — recommend `pip-audit` and `npm audit` |

---

## 11. Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers with a description of the vulnerability
3. Include steps to reproduce, affected versions, and potential impact
4. Allow reasonable time for a fix before public disclosure

---

## 12. Security Checklist for Production

Before deploying to production, verify the following:

- [ ] `SECRET_KEY` is set to a strong, random value (minimum 32 characters)
- [ ] `DATABASE_URL` uses SSL connection (`?sslmode=require`)
- [ ] `CORS_ORIGINS` is configured with specific allowed origins (not `*`)
- [ ] HTTPS is configured at the reverse proxy / load balancer level
- [ ] HSTS header is being sent (production mode enabled)
- [ ] `DEBUG` / `ENVIRONMENT` is set to `production`
- [ ] No `.env` files are present in deployment artifacts
- [ ] `pip-audit` and `npm audit` pass with no critical vulnerabilities
- [ ] Rate limiting is implemented at the reverse proxy or application level
- [ ] CSP header is configured for the frontend
- [ ] Database credentials use a dedicated role with minimal privileges
- [ ] Backups are configured and tested
- [ ] Logging is directed to a secure, centralized log store
