"""JSON extraction helpers for structured output."""

from __future__ import annotations

import json
from typing import Any

from api.errors import StructuredOutputError


def extract_json_value(text: str) -> Any:
    """Extract the first valid JSON value from model text."""
    stripped = text.strip()
    if not stripped:
        raise StructuredOutputError("The model returned an empty answer.")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            fenced = "\n".join(lines[1:-1]).strip()
            if fenced.lower().startswith("json"):
                fenced = fenced[4:].strip()
            try:
                return json.loads(fenced)
            except json.JSONDecodeError:
                pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
            return value
        except json.JSONDecodeError:
            continue

    raise StructuredOutputError("The model answer did not contain valid JSON.")
