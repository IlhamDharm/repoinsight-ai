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
