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
from urllib.parse import urlsplit, urlunsplit

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from typing_extensions import Annotated

logger = logging.getLogger(__name__)


def _build_candidate_searxng_urls() -> list[str]:
    """Return candidate SearXNG URLs that work in Docker and local runs."""
    configured = os.getenv("SEARXNG_URL", "").strip()
    default_url = "http://searxng:8080/search"

    candidates: list[str] = []
    if configured:
        candidates.append(configured)
    else:
        candidates.append(default_url)

    primary = candidates[0]
    parsed = urlsplit(primary)
    if parsed.hostname == "searxng":
        for host in ("localhost", "127.0.0.1"):
            fallback = urlunsplit(
                (
                    parsed.scheme or "http",
                    f"{host}:{parsed.port or 8080}",
                    parsed.path or "/search",
                    parsed.query,
                    parsed.fragment,
                )
            )
            candidates.append(fallback)

    seen: set[str] = set()
    deduped: list[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


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

    params = {
        "q": query,
        "format": "json",
    }
    language = os.getenv("SEARXNG_LANGUAGE", "any").strip().lower()
    if language not in {"", "any", "all", "*"}:
        params["language"] = language
        
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

    errors: list[str] = []
    for url in _build_candidate_searxng_urls():
        try:
            logger.debug("Calling SearXNG search API for query='%s' url='%s'", query, url)
            response = httpx.get(url, params=params, headers=headers, timeout=20.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            errors.append(f"{url} -> {e}")
            logger.warning("SearXNG request failed at %s: %s", url, e)

    logger.error("SearXNG search failed for query='%s' after trying all URLs", query)
    raise ValueError(
        "SearXNG search failed. Tried URLs: "
        + "; ".join(_build_candidate_searxng_urls())
        + ". Last errors: "
        + " | ".join(errors)
    )


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
