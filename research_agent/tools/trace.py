"""Trace helpers for research tool calls."""

from __future__ import annotations

from contextvars import ContextVar, Token

_research_trace: ContextVar[list[dict[str, str]] | None] = ContextVar(
    "research_trace",
    default=None,
)


def start_research_trace() -> Token[list[dict[str, str]] | None]:
    """Start collecting research-tool events for the current request."""
    return _research_trace.set([])


def reset_research_trace(token: Token[list[dict[str, str]] | None]) -> None:
    """Restore the previous trace context."""
    _research_trace.reset(token)


def get_research_trace() -> list[dict[str, str]]:
    """Return collected research-tool events for display."""
    return list(_research_trace.get() or [])


def record_research_trace(title: str, content: str) -> None:
    """Record a tool event in the active research trace."""
    trace = _research_trace.get()
    if trace is None:
        return
    trace.append(
        {
            "type": "Tool",
            "title": title,
            "content": content.strip(),
        }
    )
