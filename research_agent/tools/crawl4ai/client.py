"""Crawl4AI HTTP client helpers."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import httpx

from .config import (
    build_candidate_crawl4ai_urls,
    crawl4ai_headers,
    crawl4ai_scrape_paths,
    crawl4ai_timeout,
)
from .response import crawl4ai_task_id, extract_crawl4ai_markdown, poll_crawl4ai_task

logger = logging.getLogger(__name__)


def _scrape_body(path: str, url: str, timeout: float) -> dict[str, Any]:
    if path == "/crawl":
        return {
            "urls": [url],
            "priority": 10,
        }

    return {
        "url": url,
        "return_html": False,
        "timeout_ms": int(timeout * 1000),
        "headless": True,
    }


def fetch_webpage_content_with_crawl4ai(url: str, timeout: float | None = None) -> str:
    """Fetch a URL through a configured Crawl4AI Docker API."""
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("Crawl4AI only accepts http:// and https:// URLs")

    timeout = crawl4ai_timeout() if timeout is None else timeout
    errors: list[str] = []
    headers = crawl4ai_headers()

    for base_url in build_candidate_crawl4ai_urls():
        with httpx.Client(headers=headers, timeout=timeout) as client:
            for path in crawl4ai_scrape_paths():
                try:
                    logger.debug(
                        "Calling Crawl4AI for url='%s' api='%s%s'",
                        url,
                        base_url,
                        path,
                    )
                    response = client.post(
                        f"{base_url}{path}",
                        json=_scrape_body(path, url, timeout),
                    )
                    if response.status_code == 404:
                        errors.append(f"{base_url}{path} -> 404 Not Found")
                        continue
                    response.raise_for_status()
                    payload = response.json()

                    if isinstance(payload, dict) and payload.get("success") is False:
                        raise ValueError(payload.get("error") or payload)

                    task_id = crawl4ai_task_id(payload)
                    if task_id and not extract_crawl4ai_markdown(payload):
                        payload = poll_crawl4ai_task(
                            client,
                            base_url,
                            task_id,
                            timeout,
                        )

                    markdown_text = extract_crawl4ai_markdown(payload).strip()
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
