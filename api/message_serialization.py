"""Helpers for serializing LangChain messages for the frontend."""

from __future__ import annotations

from typing import Any

from research_agent.utils import format_message_content


def message_to_text(content: Any) -> str:
    """Extract text from common LangChain message content shapes."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    chunks.append(text)
        return "\n".join(chunks).strip()

    return str(content).strip()


def extract_final_answer(messages: list[Any]) -> str:
    """Return the final AI message content from an agent result."""
    for message in reversed(messages):
        if message.__class__.__name__.startswith("AI"):
            text = message_to_text(getattr(message, "content", ""))
            if text:
                return text
    return "No final assistant answer was returned."


def _message_title(msg_type: str) -> str:
    if msg_type == "Human":
        return "Human"
    if msg_type == "Ai":
        return "Assistant"
    if msg_type == "Tool":
        return "Tool Output"
    return msg_type


def serialize_process(messages: list[Any]) -> list[dict[str, str | None]]:
    """Serialize agent messages into frontend process rows."""
    serialized: list[dict[str, str | None]] = []
    for message in messages:
        msg_type = message.__class__.__name__.replace("Message", "")
        content = format_message_content(message).strip()
        if not content:
            continue
        row: dict[str, str | None] = {
            "type": msg_type,
            "title": _message_title(msg_type),
            "content": content,
        }
        tool_name = getattr(message, "name", None)
        if tool_name:
            row["tool_name"] = str(tool_name)
        serialized.append(row)
    return serialized
