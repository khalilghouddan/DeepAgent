"""
Research Tools.

This module provides search and content processing utilities for the research agent,
using SearXNG for URL discovery and fetching full webpage content.
"""

import json
import logging
import os
import time
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from typing_extensions import Annotated

logger = logging.getLogger(__name__)
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


def _record_research_trace(title: str, content: str) -> None:
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


def _build_candidate_crawl4ai_urls() -> list[str]:
    """Return candidate Crawl4AI API roots for Docker and local runs."""
    configured = os.getenv("CRAWL4AI_URL", "").strip().rstrip("/")
    if not configured:
        return []

    candidates = [configured]
    parsed = urlsplit(configured)
    if parsed.hostname in {"crawl4ai", "host.docker.internal"}:
        port = parsed.port or 11235
        for host in ("host.docker.internal", "localhost", "127.0.0.1"):
            fallback = urlunsplit(
                (
                    parsed.scheme or "http",
                    f"{host}:{port}",
                    parsed.path.rstrip("/"),
                    "",
                    "",
                )
            ).rstrip("/")
            candidates.append(fallback)

    seen: set[str] = set()
    deduped: list[str] = []
    for url in candidates:
        if url and url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _crawl4ai_headers() -> dict[str, str]:
    token = os.getenv("CRAWL4AI_API_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _crawl4ai_scrape_paths() -> list[str]:
    configured = os.getenv("CRAWL4AI_SCRAPE_PATH", "").strip()
    candidates = [configured] if configured else []
    candidates.extend(["/scrape", "/crawl"])

    paths: list[str] = []
    seen: set[str] = set()
    for path in candidates:
        if not path:
            continue
        normalized = path if path.startswith("/") else f"/{path}"
        if normalized not in seen:
            seen.add(normalized)
            paths.append(normalized)
    return paths


def _crawl4ai_timeout(default: float = 60.0) -> float:
    configured = os.getenv("CRAWL4AI_TIMEOUT", "").strip()
    if not configured:
        return default

    try:
        return max(1.0, float(configured))
    except ValueError:
        logger.warning(
            "Invalid CRAWL4AI_TIMEOUT=%r; using default %.1fs",
            configured,
            default,
        )
        return default


def _extract_crawl4ai_markdown(payload: Any) -> str:
    """Extract markdown from common Crawl4AI Docker response shapes."""
    if isinstance(payload, list):
        return "\n\n".join(
            text
            for item in payload
            if (text := _extract_crawl4ai_markdown(item).strip())
        )

    if not isinstance(payload, dict):
        return ""

    for key in ("markdown", "markdown_v2", "fit_markdown"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested_key in ("raw_markdown", "fit_markdown", "markdown"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    return nested

    for key in ("result", "results", "data", "response"):
        value = payload.get(key)
        text = _extract_crawl4ai_markdown(value)
        if text:
            return text

    for value in payload.values():
        text = _extract_crawl4ai_markdown(value)
        if text:
            return text

    return ""


def _crawl4ai_task_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    task_id = payload.get("task_id") or payload.get("id")
    return str(task_id) if task_id else ""


def _poll_crawl4ai_task(
    client: httpx.Client,
    base_url: str,
    task_id: str,
    timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_payload: dict[str, Any] = {}

    while time.monotonic() < deadline:
        for path in (f"/task/{task_id}", f"/crawl/job/{task_id}"):
            response = client.get(f"{base_url}{path}")
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                last_payload = payload
                status = str(payload.get("status", "")).lower()
                if status in {"completed", "complete", "done", "success", "finished"}:
                    return payload
                if _extract_crawl4ai_markdown(payload):
                    return payload
                if status in {"failed", "error"}:
                    raise ValueError(payload.get("error") or payload)
        time.sleep(1.0)

    raise TimeoutError(f"Crawl4AI task {task_id} did not finish: {last_payload}")


def fetch_webpage_content_with_crawl4ai(url: str, timeout: float | None = None) -> str:
    """Fetch a URL through a configured Crawl4AI Docker API."""
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("Crawl4AI only accepts http:// and https:// URLs")

    timeout = _crawl4ai_timeout() if timeout is None else timeout
    errors: list[str] = []
    headers = _crawl4ai_headers()

    for base_url in _build_candidate_crawl4ai_urls():
        with httpx.Client(headers=headers, timeout=timeout) as client:
            for path in _crawl4ai_scrape_paths():
                try:
                    logger.debug(
                        "Calling Crawl4AI for url='%s' api='%s%s'",
                        url,
                        base_url,
                        path,
                    )
                    if path == "/crawl":
                        body: dict[str, Any] = {
                            "urls": [url],
                            "priority": 10,
                        }
                    else:
                        body = {
                            "url": url,
                            "return_html": False,
                            "timeout_ms": int(timeout * 1000),
                            "headless": True,
                        }

                    response = client.post(f"{base_url}{path}", json=body)
                    if response.status_code == 404:
                        errors.append(f"{base_url}{path} -> 404 Not Found")
                        continue
                    response.raise_for_status()
                    payload = response.json()

                    if isinstance(payload, dict) and payload.get("success") is False:
                        raise ValueError(payload.get("error") or payload)

                    task_id = _crawl4ai_task_id(payload)
                    if task_id and not _extract_crawl4ai_markdown(payload):
                        payload = _poll_crawl4ai_task(
                            client, base_url, task_id, timeout
                        )

                    markdown_text = _extract_crawl4ai_markdown(payload).strip()
                    if markdown_text:
                        return markdown_text
                    errors.append(f"{base_url}{path} -> no markdown in response")
                except Exception as exc:
                    errors.append(f"{base_url}{path} -> {exc}")
                    logger.warning(
                        "Crawl4AI request failed at %s%s: %s",
                        base_url,
                        path,
                        exc,
                    )

    raise ValueError("Crawl4AI fetch failed: " + " | ".join(errors))


def _normalize_url_list(urls: str | list[str]) -> list[str]:
    if isinstance(urls, str):
        candidates = [
            line.strip().strip("-*0123456789. ")
            for line in urls.replace(",", "\n").splitlines()
        ]
    else:
        candidates = [str(url).strip() for url in urls]

    normalized: list[str] = []
    seen: set[str] = set()
    for url in candidates:
        if not url:
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if url not in seen:
            seen.add(url)
            normalized.append(url)
    return normalized


def _resolve_max_results(max_results: int | None = None) -> int:
    if max_results and max_results > 0:
        return max_results
    try:
        return max(1, int(os.getenv("SEARXNG_MAX_RESULTS", "5")))
    except ValueError:
        return 5


@tool(parse_docstring=True)
def crawl4ai_scrape_url(
    url: str,
    max_chars: Annotated[int, InjectedToolArg] = 12000,
) -> str:
    """Scrape a webpage URL using the configured Crawl4AI Docker API.

    Args:
        url: HTTP or HTTPS webpage URL to scrape.
        max_chars: Maximum markdown characters to return.

    Returns:
        Markdown extracted from the page.
    """
    _record_research_trace(
        "Tool Call: crawl4ai_scrape_url",
        f"URL: {url}",
    )

    if not _build_candidate_crawl4ai_urls():
        _record_research_trace(
            "Tool Output: crawl4ai_scrape_url",
            "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it.",
        )
        return "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it."

    try:
        markdown_text = fetch_webpage_content_with_crawl4ai(url).strip()
    except Exception as exc:
        logger.exception("Crawl4AI scrape failed for url='%s'", url)
        _record_research_trace(
            "Tool Output: crawl4ai_scrape_url",
            f"Failed scraping {url}: {exc}",
        )
        return f"Error scraping {url} with Crawl4AI: {exc}"

    if max_chars > 0:
        markdown_text = markdown_text[:max_chars]

    _record_research_trace(
        "Tool Output: crawl4ai_scrape_url",
        f"Scraped {url}\nReturned markdown characters: {len(markdown_text)}",
    )

    return f"""## Crawl4AI scrape result
**URL:** {url}

{markdown_text}"""


@tool(parse_docstring=True)
def crawl4ai_scrape_urls(
    urls: list[str],
    max_chars_per_url: Annotated[int, InjectedToolArg] = 12000,
) -> str:
    """Scrape multiple webpage URLs using the configured Crawl4AI Docker API.

    Args:
        urls: HTTP or HTTPS webpage URLs returned by searxng_search.
        max_chars_per_url: Maximum markdown characters to return per URL.

    Returns:
        Scraped markdown grouped by source URL.
    """
    normalized_urls = _normalize_url_list(urls)
    _record_research_trace(
        "Tool Call: crawl4ai_scrape_urls",
        "URLs:\n" + json.dumps(normalized_urls, ensure_ascii=False, indent=2),
    )

    if not _build_candidate_crawl4ai_urls():
        _record_research_trace(
            "Tool Output: crawl4ai_scrape_urls",
            "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it.",
        )
        return "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it."

    if not normalized_urls:
        _record_research_trace(
            "Tool Output: crawl4ai_scrape_urls",
            "No valid HTTP/HTTPS URLs were provided to Crawl4AI.",
        )
        return "No valid HTTP/HTTPS URLs were provided to Crawl4AI."

    scraped_results: list[str] = []
    failed_results: list[str] = []
    scrape_summaries: list[str] = []
    for index, url in enumerate(normalized_urls, start=1):
        try:
            markdown_text = fetch_webpage_content_with_crawl4ai(url).strip()
            if max_chars_per_url > 0:
                markdown_text = markdown_text[:max_chars_per_url]
            scrape_summaries.append(
                f"{index}. OK - {url} ({len(markdown_text)} markdown chars)"
            )
            scraped_results.append(
                f"""## Source {index}
**URL:** {url}

{markdown_text}

---"""
            )
        except Exception as exc:
            logger.exception("Crawl4AI scrape failed for url='%s'", url)
            failed_results.append(f"- {url}: {exc}")
            scrape_summaries.append(f"{index}. FAILED - {url}: {exc}")

    if failed_results:
        scraped_results.append(
            "## Crawl4AI scrape failures\n" + "\n".join(failed_results)
        )

    successful_count = len(scraped_results) - bool(failed_results)
    _record_research_trace(
        "Tool Output: crawl4ai_scrape_urls",
        f"Crawl4AI scraped {successful_count} of {len(normalized_urls)} URL(s).\n\n"
        + "\n".join(scrape_summaries),
    )

    return f"""Crawl4AI scraped {len(scraped_results) - bool(failed_results)} of {len(normalized_urls)} URL(s).

{chr(10).join(scraped_results)}"""


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
    """Persist returned sources into a JSON history file when explicitly enabled."""
    json_path = os.getenv("SEARXNG_SOURCES_JSON_PATH") or os.getenv(
        "SOURCES_JSON_PATH"
    )
    if not json_path:
        return

    payload_entry = {
        "query": query,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(sources),
        "sources": sources,
    }

    try:
        output_path = Path(json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        history: list[dict[str, Any]] = []
        if output_path.exists():
            try:
                raw = json.loads(output_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    history = raw
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse existing sources JSON at %s, recreating file.",
                    output_path,
                )

        history.append(payload_entry)
        output_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Appended %s source(s) to %s", len(sources), output_path)
    except OSError as exc:
        logger.warning("Could not save sources JSON to %s: %s", json_path, exc)


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
    if _build_candidate_crawl4ai_urls():
        try:
            return fetch_webpage_content_with_crawl4ai(url)
        except Exception as exc:
            logger.warning(
                "Falling back to direct fetch for %s after Crawl4AI error: %s",
                url,
                exc,
            )

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
    max_results: Annotated[int, InjectedToolArg] = 0,
) -> str:
    """Search the web using SearXNG and return source candidate URLs.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return.

    Returns:
        Search result titles, snippets, and URLs to pass to crawl4ai_scrape_urls.
    """

    resolved_max_results = _resolve_max_results(max_results)
    _record_research_trace(
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
    except Exception as e:
        logger.exception("Error during searxng_search")
        _record_research_trace(
            "Tool Output: searxng_search",
            f"Error during SearXNG search: {e}",
        )
        return f"Error during SearXNG search: {str(e)}"

    items = search_results.get("results", [])
    result_texts = []
    source_rows: list[dict[str, Any]] = []

    for index, result in enumerate(items[:resolved_max_results], start=1):
        url = result.get("url")
        title = result.get("title", "Untitled result")
        snippet = result.get("content", "")

        if not url:
            continue

        source_rows.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
        )

        result_text = f"""## Result {index}: {title}
**URL:** {url}

{snippet}

---
"""
        result_texts.append(result_text)

    _save_sources_json(query=query, sources=source_rows)

    logger.info("searxng_search found %s result(s) for query='%s'", len(result_texts), query)

    urls = [row["url"] for row in source_rows]
    source_summary = [
        f"{index}. {row['title']}: {row['url']}"
        for index, row in enumerate(source_rows, start=1)
    ]
    _record_research_trace(
        "Tool Output: searxng_search",
        f"Found {len(result_texts)} SearXNG result(s) for '{query}'.\n\n"
        + "\n".join(source_summary),
    )
    return f"""Found {len(result_texts)} SearXNG result(s) for '{query}'.

Use crawl4ai_scrape_urls with all of these URLs before writing findings:
{json.dumps(urls, ensure_ascii=False, indent=2)}

Search candidates:

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
