"""Direct webpage fetch fallback when Crawl4AI is unavailable."""

from __future__ import annotations

import logging

import httpx
from markdownify import markdownify

from .client import fetch_webpage_content_with_crawl4ai
from .config import build_candidate_crawl4ai_urls

logger = logging.getLogger(__name__)


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown."""
    if build_candidate_crawl4ai_urls():
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

    except Exception as exc:
        logger.exception("Failed fetching webpage content: %s", url)
        return f"Error fetching content from {url}: {exc}"
