"""LangChain tools backed by Crawl4AI."""

from __future__ import annotations

import json
import logging

from langchain_core.tools import InjectedToolArg, tool
from typing_extensions import Annotated

from research_agent.tools.trace import record_research_trace

from .client import (
    fetch_webpage_content_with_crawl4ai,
    fetch_webpage_contents_with_crawl4ai,
)
from .config import build_candidate_crawl4ai_urls, crawl4ai_batch_size
from .urls import normalize_url_list

logger = logging.getLogger(__name__)


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _retry_missing_urls(
    urls: list[str],
    markdown_by_url: dict[str, str],
    failed_results: list[str],
    batch_error: Exception | None = None,
) -> int:
    recovered_count = 0
    for url in urls:
        if markdown_by_url.get(url, "").strip():
            continue

        try:
            markdown_by_url[url] = fetch_webpage_content_with_crawl4ai(url).strip()
            recovered_count += 1
        except Exception as exc:
            logger.warning(
                "Crawl4AI single-url retry failed for url='%s': %s",
                url,
                exc,
            )
            if batch_error is None:
                failed_results.append(f"- {url}: no markdown returned; retry failed: {exc}")
            else:
                failed_results.append(
                    f"- {url}: batch failed ({batch_error}); single-url retry failed: {exc}"
                )
    return recovered_count


@tool(parse_docstring=True)
def crawl4ai_scrape_url(
    url: str,
    max_chars: Annotated[int, InjectedToolArg] = 0,
) -> str:
    """Scrape a webpage URL using the configured Crawl4AI Docker API.

    Args:
        url: HTTP or HTTPS webpage URL to scrape.
        max_chars: Maximum markdown characters to return. Use 0 for the whole page.

    Returns:
        Markdown extracted from the page.
    """
    record_research_trace(
        "Tool Call: crawl4ai_scrape_url",
        f"URL: {url}",
    )

    if not build_candidate_crawl4ai_urls():
        record_research_trace(
            "Tool Output: crawl4ai_scrape_url",
            "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it.",
        )
        return "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it."

    try:
        markdown_text = fetch_webpage_content_with_crawl4ai(url).strip()
    except Exception as exc:
        logger.exception("Crawl4AI scrape failed for url='%s'", url)
        record_research_trace(
            "Tool Output: crawl4ai_scrape_url",
            f"Failed scraping {url}: {exc}",
        )
        return f"Error scraping {url} with Crawl4AI: {exc}"

    if max_chars > 0:
        markdown_text = markdown_text[:max_chars]

    record_research_trace(
        "Tool Output: crawl4ai_scrape_url",
        f"Scraped {url}\nReturned markdown characters: {len(markdown_text)}",
    )

    return f"""## Crawl4AI scrape result
**URL:** {url}

{markdown_text}"""


@tool(parse_docstring=True)
def crawl4ai_scrape_urls(
    urls: list[str],
    max_chars_per_url: Annotated[int, InjectedToolArg] = 0,
) -> str:
    """Scrape multiple webpage URLs using the configured Crawl4AI Docker API.

    Args:
        urls: HTTP or HTTPS webpage URLs returned by searxng_search.
        max_chars_per_url: Maximum markdown characters to return per URL. Use 0 for
            the whole page.

    Returns:
        Scraped markdown grouped by source URL.
    """
    normalized_urls = normalize_url_list(urls)
    record_research_trace(
        "Tool Call: crawl4ai_scrape_urls",
        "URLs:\n" + json.dumps(normalized_urls, ensure_ascii=False, indent=2),
    )

    if not build_candidate_crawl4ai_urls():
        record_research_trace(
            "Tool Output: crawl4ai_scrape_urls",
            "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it.",
        )
        return "Crawl4AI is not configured. Set CRAWL4AI_URL to enable it."

    if not normalized_urls:
        record_research_trace(
            "Tool Output: crawl4ai_scrape_urls",
            "No valid HTTP/HTTPS URLs were provided to Crawl4AI.",
        )
        return "No valid HTTP/HTTPS URLs were provided to Crawl4AI."

    markdown_by_url: dict[str, str] = {}
    failed_results: list[str] = []
    batch_size = crawl4ai_batch_size()
    batches = _chunks(normalized_urls, batch_size)
    retry_count = 0
    recovered_count = 0
    for url_batch in batches:
        try:
            if len(url_batch) == 1:
                url = url_batch[0]
                markdown_by_url[url] = fetch_webpage_content_with_crawl4ai(url).strip()
            else:
                markdown_by_url.update(fetch_webpage_contents_with_crawl4ai(url_batch))
        except Exception as exc:
            logger.warning("Crawl4AI scrape failed for urls=%s: %s", url_batch, exc)
            if len(url_batch) == 1:
                failed_results.append(f"- {url_batch[0]}: {exc}")
                continue

            retry_count += len(url_batch)
            recovered_count += _retry_missing_urls(
                url_batch,
                markdown_by_url,
                failed_results,
                batch_error=exc,
            )
            continue

        missing_urls = [
            url for url in url_batch if not markdown_by_url.get(url, "").strip()
        ]
        if missing_urls:
            retry_count += len(missing_urls)
            recovered_count += _retry_missing_urls(
                missing_urls,
                markdown_by_url,
                failed_results,
            )

    scraped_results: list[str] = []
    scrape_summaries: list[str] = []
    for index, url in enumerate(normalized_urls, start=1):
        markdown_text = markdown_by_url.get(url, "").strip()
        if not markdown_text:
            scrape_summaries.append(f"{index}. FAILED - {url}: no markdown returned")
            if not any(item.startswith(f"- {url}:") for item in failed_results):
                failed_results.append(f"- {url}: no markdown returned")
            continue

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

    if failed_results:
        scraped_results.append(
            "## Crawl4AI scrape failures\n" + "\n".join(failed_results)
        )

    successful_count = sum(
        1 for url in normalized_urls if markdown_by_url.get(url, "").strip()
    )
    retry_summary = ""
    if retry_count:
        retry_summary = (
            f", with {recovered_count} recovered from {retry_count} "
            "single-url retry request(s)"
        )
    request_kind = "single-url" if batch_size == 1 else "batch"
    record_research_trace(
        "Tool Output: crawl4ai_scrape_urls",
        f"Crawl4AI scraped {successful_count} of {len(normalized_urls)} URL(s) "
        f"in {len(batches)} {request_kind} request(s){retry_summary}.\n\n"
        + "\n".join(scrape_summaries),
    )

    return f"""Crawl4AI scraped {successful_count} of {len(normalized_urls)} URL(s).

{chr(10).join(scraped_results)}"""
