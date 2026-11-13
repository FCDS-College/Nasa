from datetime import UTC, datetime
from typing import Any

from fastapi import Request


API_VERSION = "0.7.0"  # = docs/api/openapi.json info.version (ResponseMeta.api_version is the contract version)


def response_meta(request: Request) -> dict[str, str]:
    return {
        "request_id": request.state.request_id,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "api_version": API_VERSION,
    }


def error_body(
    request: Request,
    code: str,
    message: str,
    *,
    retryable: bool = False,
    field_errors: list[dict[str, str]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request.state.request_id,
            "retryable": retryable,
            "field_errors": field_errors or [],
            "details": details or {},
        }
    }
