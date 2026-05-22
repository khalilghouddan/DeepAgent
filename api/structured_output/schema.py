"""JSON Schema normalization and validation."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from api.errors import StructuredOutputError

_JSON_SCHEMA_MARKER_KEYS = {
    "$defs",
    "$id",
    "$schema",
    "$ref",
    "additionalProperties",
    "allOf",
    "anyOf",
    "const",
    "enum",
    "items",
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "oneOf",
    "pattern",
    "properties",
    "required",
}
_JSON_SCHEMA_TYPES = {
    "array",
    "boolean",
    "integer",
    "null",
    "number",
    "object",
    "string",
}


def _valid_schema_type(value: Any) -> bool:
    if isinstance(value, str):
        return value in _JSON_SCHEMA_TYPES
    if isinstance(value, list):
        return all(item in _JSON_SCHEMA_TYPES for item in value)
    return False


def _looks_like_json_schema(value: dict[str, Any]) -> bool:
    return any(key in value for key in _JSON_SCHEMA_MARKER_KEYS) or (
        "type" in value and _valid_schema_type(value["type"])
    )


def _template_value_to_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {
                key: _template_value_to_schema(child)
                for key, child in value.items()
            },
            "required": list(value.keys()),
            "additionalProperties": False,
        }

    if isinstance(value, list):
        return {
            "type": "array",
            "items": _template_value_to_schema(value[0]) if value else {"type": "string"},
        }

    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": ["string", "null"]}
    return {"type": "string"}


def template_to_json_schema(template: dict[str, Any]) -> dict[str, Any]:
    """Convert a user-provided JSON output template into JSON Schema."""
    return _template_value_to_schema(template)


def normalize_output_schema(schema: Any) -> dict[str, Any] | None:
    """Validate and normalize an optional JSON Schema or JSON output template."""
    if not schema:
        return None
    if not isinstance(schema, dict):
        raise StructuredOutputError("output_schema must be a JSON object.")

    if not _looks_like_json_schema(schema):
        schema = template_to_json_schema(schema)

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
