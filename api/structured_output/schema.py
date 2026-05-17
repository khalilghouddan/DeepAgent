"""JSON Schema normalization and validation."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from api.errors import StructuredOutputError


def normalize_output_schema(schema: Any) -> dict[str, Any] | None:
    """Validate and normalize an optional user-provided JSON Schema."""
    if not schema:
        return None
    if not isinstance(schema, dict):
        raise StructuredOutputError("output_schema must be a JSON object.")

    serialized = json.dumps(schema, ensure_ascii=False)
    if len(serialized) > 12000:
        raise StructuredOutputError(
            "output_schema is too large; keep it under 12000 characters."
        )

    try:
        Draft202012Validator.check_schema(schema)
    except JsonSchemaError as exc:
        raise StructuredOutputError(f"Invalid output_schema: {exc.message}") from exc

    return schema


def validate_json_value(value: Any, schema: dict[str, Any]) -> Any:
    """Validate a parsed JSON value against a schema."""
    try:
        Draft202012Validator(schema).validate(value)
    except JsonSchemaValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        location = f" at '{path}'" if path else ""
        raise StructuredOutputError(
            f"Model output does not match output_schema{location}: {exc.message}"
        ) from exc
    return value
