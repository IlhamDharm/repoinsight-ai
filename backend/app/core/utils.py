from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


def serialize_for_response(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): serialize_for_response(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_for_response(item) for item in value]
    return value


def build_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
