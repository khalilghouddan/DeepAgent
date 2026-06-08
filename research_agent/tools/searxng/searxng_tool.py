"""LangChain SearXNG search tool."""

from __future__ import annotations

import logging

from langchain_core.tools import InjectedToolArg, tool
from typing_extensions import Annotated

from research_agent.tools.research_trace import record_research_trace

from .searxng_client import searxng_search_request
from .searxng_config import resolve_max_results
from .searxng_formatting import format_source_summary, format_tool_response, source_rows_from_results

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
def searxng_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 0,
) -> str:
    """Search the web using SearXNG and return source candidate URLs.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return.

    Returns:
        Search result titles, snippets, and URLs to pass to crawl4ai_scrape_urls.
    """
    resolved_max_results = resolve_max_results(max_results)
    record_research_trace(
        "Tool Call: searxng_search",
        f"Query: {query}\nMax results: {resolved_max_results}",
    )
    try:
        logger.info(
            "Running searxng_search query='%s' max_results=%s",
            query,
            resolved_max_results,
        )
        search_results = searxng_search_request(
            query=query,
            max_results=resolved_max_results,
        )
    except Exception as exc:
        logger.exception("Error during searxng_search")
        record_research_trace(
            "Tool Output: searxng_search",
            f"Error during SearXNG search: {exc}",
        )
        return f"Error during SearXNG search: {exc}"

    source_rows = source_rows_from_results(search_results, resolved_max_results)
    logger.info(
        "searxng_search found %s result(s) for query='%s'",
        len(source_rows),
        query,
    )

    record_research_trace(
        "Tool Output: searxng_search",
        format_tool_response(query, source_rows),
    )
    return format_tool_response(query, source_rows)
