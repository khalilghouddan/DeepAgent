"""Logging setup shared by API and CLI entrypoints."""

from __future__ import annotations

import logging


def configure_logging(log_level: str) -> None:
    """Configure root logging for application entrypoints."""
    level_name = (log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
