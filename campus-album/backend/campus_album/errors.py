from typing import Any


def error_response(code: str, message: str, status: int) -> tuple[dict[str, Any], int]:
    """Build a unified JSON error response payload and HTTP status code."""
    return {"error": {"code": code, "message": message}}, status
