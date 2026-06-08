"""Reflection tool for the research agent."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.

    Args:
        reflection: Detailed reflection on findings, gaps, and next steps

    Returns:
        Confirmation message
    """
    logger.debug("think_tool reflection length=%s", len(reflection))
    return f"Reflection recorded: {reflection}"
