"""Environment parsing helpers for research execution."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def normalize_response_language(search_language: str) -> str:
    value = (search_language or "any").strip().lower()
    if value in {"", "any", "all", "*"}:
        return "any"
    return value


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, os.getenv(name), default)
        return default


def research_timeout_seconds() -> int | None:
    configured = os.getenv("AGENT_TIMEOUT_SECONDS", "").strip()
    if not configured:
        return None

    try:
        timeout_seconds = int(configured)
    except ValueError:
        logger.warning(
            "Invalid AGENT_TIMEOUT_SECONDS=%r; running without a timeout",
            configured,
        )
        return None

    if timeout_seconds <= 0:
        return None

    return timeout_seconds
