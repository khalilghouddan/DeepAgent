"""Pydantic schemas for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)
    model_provider: str | None = None
    search_language: str = "any"
    log_level: str = "INFO"
    search_date: str | None = None
    max_sources: int | None = Field(default=None, ge=1, le=20)
    researcher_iterations: int | None = Field(default=None, ge=1, le=10)
    output_schema: dict[str, Any] | None = None


class ResearchResponse(BaseModel):
    answer: str
    report_content: str | None = None
    structured_answer: Any | None = None
    process: list[dict[str, str | None]] = Field(default_factory=list)


def model_dump(model: BaseModel) -> dict[str, Any]:
    """Return a dict for Pydantic v1/v2 models."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
