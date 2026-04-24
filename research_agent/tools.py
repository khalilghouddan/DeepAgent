"""
Research Tools.

This module provides search and content processing utilities for the research agent,
using SearXNG for URL discovery and fetching full webpage content.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from typing_extensions import Annotated

logger = logging.getLogger(__name__)


def _save_sources_json(query: str, sources: list[dict[str, Any]]) -> None:
    """Persist returned sources into a JSON history file."""
    json_path = os.getenv("SEARXNG_SOURCES_JSON_PATH") or os.getenv(
        "SOURCES_JSON_PATH"
    )
    if not json_path:
        json_path = "outputs/sources_history.json"

    output_path = Path(json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload_entry = {
        "query": query,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(sources),
        "sources": sources,
    }
    history: list[dict[str, Any]] = []
    if output_path.exists():
        try:
            raw = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                history = raw
        except Exception:
            logger.warning(
                "Could not parse existing sources JSON at %s, recreating file.",
                output_path,
            )

    history.append(payload_entry)
    output_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Appended %s source(s) to %s", len(sources), output_path)


# -----------------------------
# Fetch webpage content
# -----------------------------
def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    try:
        logger.debug("Fetching webpage content: %s", url)
        response = httpx.get(
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return markdownify(response.text)

    except Exception as e:
        logger.exception("Failed fetching webpage content: %s", url)
        return f"Error fetching content from {url}: {str(e)}"


# -----------------------------
# SearXNG search request
# -----------------------------
def searxng_search_request(
    query: str,
    max_results: int = 5,
) -> dict:
    """Call SearXNG API and return results."""

    url = os.getenv("SEARXNG_URL", "http://searxng:8080/search")

    params = {
        "q": query,
        "format": "json",
        "language": "en",
    }
    # SearXNG's bot detection can require client IP headers even on internal networks.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1",
    }

    try:
        logger.debug("Calling SearXNG search API for query: %s", query)
        response = httpx.get(url, params=params, headers=headers, timeout=20.0)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logger.exception("SearXNG search failed for query: %s", query)
        raise ValueError(f"SearXNG search failed: {str(e)}")


# -----------------------------
# Tool: SearXNG search
# -----------------------------
@tool(parse_docstring=True)
def searxng_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
) -> str:
    """Search the web using SearXNG.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 3)

    Returns:
        Formatted search results with full webpage content
    """

    try:
        logger.info("Running searxng_search query='%s' max_results=%s", query, max_results)
        search_results = searxng_search_request(query=query)
    except Exception as e:
        logger.exception("Error during searxng_search")
        return f"Error during SearXNG search: {str(e)}"

    items = search_results.get("results", [])
    result_texts = []
    source_rows: list[dict[str, Any]] = []

    for result in items[:max_results]:
        url = result.get("url")
        title = result.get("title", "Untitled result")
        snippet = result.get("content", "")

        if not url:
            continue

        content = fetch_webpage_content(url)
        source_rows.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
        )

        result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
        result_texts.append(result_text)

    _save_sources_json(query=query, sources=source_rows)

    logger.info("searxng_search found %s result(s) for query='%s'", len(result_texts), query)

    return f"""🔍 Found {len(result_texts)} result(s) for '{query}':

{chr(10).join(result_texts)}"""


# -----------------------------
# Tool: Think (reflection)
# -----------------------------
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
