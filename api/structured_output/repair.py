"""Structured output repair strategies."""

from __future__ import annotations

from typing import Any

from api.message_serialization import message_to_text
from api.model_provider import build_chat_model

from .extraction import extract_json_value
from .prompts import build_conversion_prompt
from .schema import validate_json_value


def _structured_response_to_json_value(response: Any) -> Any:
    """Convert a structured model response into a plain JSON-compatible value."""
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    if isinstance(response, str):
        return extract_json_value(response)
    if isinstance(response, (dict, list, int, float, bool)) or response is None:
        return response

    content = getattr(response, "content", None)
    if content is not None:
        return extract_json_value(message_to_text(content))

    return extract_json_value(message_to_text(response))


def repair_with_structured_output(
    answer: str,
    schema: dict[str, Any],
    model_config: dict[str, Any],
) -> Any:
    """Use LangChain structured output to convert an answer into schema JSON."""
    structured_llm = build_chat_model(model_config).with_structured_output(schema)
    structured_response = structured_llm.invoke(build_conversion_prompt(answer, schema))
    return validate_json_value(
        _structured_response_to_json_value(structured_response),
        schema,
    )


def repair_structured_answer(
    answer: str,
    schema: dict[str, Any],
    model_config: dict[str, Any],
) -> Any:
    """Ask the same model provider to convert an answer into valid schema JSON."""
    repair_prompt = (
        "Return ONLY valid JSON. Do not add Markdown or commentary.\n\n"
        + build_conversion_prompt(answer, schema)
    )
    repair_response = build_chat_model(model_config).invoke(repair_prompt)
    repaired_text = message_to_text(getattr(repair_response, "content", repair_response))
    return validate_json_value(extract_json_value(repaired_text), schema)
