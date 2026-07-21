from typing import Any

from app.core.utils import build_timestamp, serialize_for_response


def build_success_payload(data: Any, request_id: str | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "data": serialize_for_response(data),
        "meta": {
            "request_id": request_id or "unknown",
            "timestamp": build_timestamp(),
        },
    }


def build_error_payload(
    message: str,
    code: str,
    *,
    request_id: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    error_payload: dict[str, Any] = {"message": message, "code": code}
    if details is not None:
        error_payload["details"] = serialize_for_response(details)

    return {
        "success": False,
        "error": error_payload,
        "meta": {
            "request_id": request_id or "unknown",
            "timestamp": build_timestamp(),
        },
    }
