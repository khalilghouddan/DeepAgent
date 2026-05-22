"""Prompt helpers for structured output conversion."""

from __future__ import annotations

import json
from typing import Any


def query_with_output_schema(query: str, schema: dict[str, Any] | None) -> str:
    """Append strict JSON-output instructions when a schema is provided."""
    if not schema:
        return query

    return (
        query
        + "\n\n"
        + "Structured output requirement:\n"
        + "The final answer must be ONLY valid JSON. Do not wrap it in Markdown. "
        + "Do not add commentary, citations outside JSON, headings, or explanations. "
        + "Start with '{' or '[' and end with the matching JSON closing character. "
        + "The JSON must validate against this JSON Schema, which may have been generated "
        + "from a Pydantic model:\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
    )


def build_conversion_prompt(answer: str, schema: dict[str, Any]) -> str:
    """Build the final-answer conversion prompt for structured output repair."""
    return (
        "Convert the following model answer into structured data that validates "
        "against the provided JSON Schema. Use only information present in the "
        "answer. If a required string is missing, use an empty string. If a "
        "required array is missing, use an empty array.\n\n"
        "JSON Schema:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "Model answer to convert:\n"
        f"{answer}"
    )
