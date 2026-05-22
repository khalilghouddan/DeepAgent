"""API exception types and HTTP error mapping."""

from __future__ import annotations

from fastapi import HTTPException


class ResearchTimeoutError(TimeoutError):
    """Raised when a research run exceeds the configured API timeout."""


class ResearchExecutionError(RuntimeError):
    """Raised when the worker process returns a typed research failure."""

    def __init__(self, message: str, error_type: str | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type or "RuntimeError"


class StructuredOutputError(ValueError):
    """Raised when model output cannot be parsed or validated against a schema."""


def http_error_for_research_failure(exc: ResearchExecutionError) -> HTTPException:
    """Map typed worker failures to API responses."""
    error_type = exc.error_type
    message = str(exc) or "Research execution failed"

    if error_type == "APIConnectionError":
        return HTTPException(
            status_code=502,
            detail=(
                "Could not connect to the model provider. Check OPENAI_BASE_URL, "
                "Docker/network connectivity, and provider availability. "
                f"Provider error: {message}"
            ),
        )
    if error_type == "AuthenticationError":
        return HTTPException(
            status_code=401,
            detail="Model provider authentication failed. Check OPENAI_API_KEY.",
        )
    if error_type == "PermissionDeniedError":
        return HTTPException(
            status_code=403,
            detail=f"Model provider permission denied: {message}",
        )
    if error_type == "NotFoundError":
        return HTTPException(
            status_code=404,
            detail=(
                "Model provider resource was not found. "
                f"Check OPENAI_MODEL. {message}"
            ),
        )
    if error_type == "BadRequestError":
        return HTTPException(
            status_code=400,
            detail=f"Model request failed: {message}",
        )
    if error_type == "StructuredOutputError":
        return HTTPException(status_code=422, detail=message)
    if error_type == "RateLimitError":
        return HTTPException(
            status_code=429,
            detail=f"Model rate limit hit: {message}",
        )

    return HTTPException(status_code=500, detail=f"{error_type}: {message}")
