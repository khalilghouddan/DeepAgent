"""Structured output orchestration service."""

from __future__ import annotations

import logging
from typing import Any

from api.errors import StructuredOutputError

from .extraction import extract_json_value
from .repair import repair_structured_answer, repair_with_structured_output
from .schema import validate_json_value

logger = logging.getLogger(__name__)


def validate_structured_answer(
    answer: str,
    schema: dict[str, Any] | None,
) -> Any | None:
    """Parse and validate model text against a schema."""
    if not schema:
        return None
    return validate_json_value(extract_json_value(answer), schema)


def coerce_structured_answer(
    answer: str,
    schema: dict[str, Any] | None,
    model_config: dict[str, Any],
) -> Any | None:
    """Validate a structured answer or repair it once if needed."""
    if not schema:
        return None

    validation_error: StructuredOutputError | None = None
    try:
        return validate_structured_answer(answer, schema)
    except StructuredOutputError as exc:
        validation_error = exc
        logger.info(
            "Structured output validation failed; attempting with_structured_output.",
        )

    try:
        return repair_with_structured_output(answer, schema, model_config)
    except Exception:
        logger.info(
            "with_structured_output failed; falling back to JSON repair prompt.",
            exc_info=True,
        )

    try:
        return repair_structured_answer(answer, schema, model_config)
    except StructuredOutputError as repair_error:
        if validation_error is not None:
            raise validation_error from repair_error
        raise
