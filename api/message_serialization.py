"""Helpers for serializing LangChain messages for the frontend."""

from __future__ import annotations

from typing import Any

from research_agent.utils import format_message_content


MISSING_FINAL_ANSWER = "No final assistant answer was returned."


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


def _tool_call_name(tool_call: Any) -> str:
    if isinstance(tool_call, dict):
        return str(tool_call.get("name") or "")
    return str(getattr(tool_call, "name", "") or "")


def _tool_call_args(tool_call: Any) -> dict[str, Any]:
    if isinstance(tool_call, dict):
        args = tool_call.get("args") or tool_call.get("input") or {}
    else:
        args = getattr(tool_call, "args", None) or getattr(tool_call, "input", None) or {}
    return args if isinstance(args, dict) else {}


def _message_tool_calls(message: Any) -> list[Any]:
    tool_calls = list(getattr(message, "tool_calls", None) or [])
    content = getattr(message, "content", None)
    if isinstance(content, list):
        tool_calls.extend(
            item
            for item in content
            if isinstance(item, dict) and item.get("type") == "tool_use"
        )
    return tool_calls


def _final_report_from_tool_calls(messages: list[Any]) -> str:
    fallback_content = ""
    for message in reversed(messages):
        if not message.__class__.__name__.startswith("AI"):
            continue
        for tool_call in reversed(_message_tool_calls(message)):
            if _tool_call_name(tool_call) != "write_file":
                continue
            args = _tool_call_args(tool_call)
            content = str(args.get("content") or "").strip()
            if not content:
                continue
            file_path = str(args.get("file_path") or "")
            if file_path.endswith(".json"):
                return content
            if "final_report" in file_path and not fallback_content:
                fallback_content = content
    return fallback_content


def extract_report_content(messages: list[Any]) -> str:
    """Return generated report/content written by the agent.

    Prefer the explicit final report, but also capture structured artifacts such
    as course.json when the run is constrained to JSON output.
    """
    fallback_content = ""
    for message in reversed(messages):
        if not message.__class__.__name__.startswith("AI"):
            continue
        for tool_call in reversed(_message_tool_calls(message)):
            if _tool_call_name(tool_call) != "write_file":
                continue
            args = _tool_call_args(tool_call)
            file_path = str(args.get("file_path") or "")
            content = str(args.get("content") or "").strip()
            if not content:
                continue
            if "final_report" in file_path:
                return content
            if file_path.endswith(".json") and "research_request" not in file_path:
                fallback_content = content
    return fallback_content


def extract_final_answer(messages: list[Any]) -> str:
    """Return the final AI message content from an agent result."""
    for message in reversed(messages):
        if message.__class__.__name__.startswith("AI"):
            text = message_to_text(getattr(message, "content", ""))
            if text:
                return text
    tool_call_answer = _final_report_from_tool_calls(messages)
    if tool_call_answer:
        return tool_call_answer
    return MISSING_FINAL_ANSWER


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
