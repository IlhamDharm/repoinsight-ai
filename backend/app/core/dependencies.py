from fastapi import Request

from app.core.middleware import get_request_id


def get_request_id_dependency(request: Request) -> str:
    return getattr(request.state, "request_id", get_request_id())
