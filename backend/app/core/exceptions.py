from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        code: str = "internal_server_error",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(message, status_code=404, code="not_found", details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid request", details: Any = None) -> None:
        super().__init__(message, status_code=422, code="validation_error", details=details)


class DuplicateResourceError(AppException):
    def __init__(self, message: str = "Resource already exists", details: Any = None) -> None:
        super().__init__(message, status_code=409, code="duplicate_resource", details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required", details: Any = None) -> None:
        super().__init__(message, status_code=401, code="authentication_error", details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied", details: Any = None) -> None:
        super().__init__(message, status_code=403, code="forbidden", details=details)


# --- External Service Errors ---

class ExternalServiceError(AppException):
    """Base class for errors originating from external services (e.g., GitHub)."""
    def __init__(self, message: str = "External service error", details: Any = None) -> None:
        super().__init__(message, status_code=502, code="external_service_error", details=details)


class GitHubNotFoundError(NotFoundError):
    def __init__(self, message: str = "GitHub repository not found", details: Any = None) -> None:
        super().__init__(message, details=details)


class GitHubRateLimitError(AppException):
    def __init__(self, message: str = "GitHub API rate limit exceeded", details: Any = None) -> None:
        super().__init__(message, status_code=429, code="github_rate_limit", details=details)


class GitHubAuthError(AppException):
    def __init__(self, message: str = "GitHub API authentication failed", details: Any = None) -> None:
        super().__init__(message, status_code=401, code="github_auth_error", details=details)


class GitHubTimeoutError(AppException):
    def __init__(self, message: str = "GitHub API request timed out", details: Any = None) -> None:
        super().__init__(message, status_code=504, code="github_timeout", details=details)


class GitHubConnectionError(ExternalServiceError):
    def __init__(self, message: str = "Cannot connect to GitHub API", details: Any = None) -> None:
        super().__init__(message, details=details)
