"""SearXNG HTTP client."""

from __future__ import annotations

import logging

import httpx

from .config import build_candidate_searxng_urls, searxng_headers, searxng_params

logger = logging.getLogger(__name__)


def searxng_search_request(
    query: str,
    max_results: int = 5,
) -> dict:
    """Call SearXNG API and return results."""
    errors: list[str] = []
    for url in build_candidate_searxng_urls():
        try:
            logger.debug("Calling SearXNG search API for query='%s' url='%s'", query, url)
            response = httpx.get(
                url,
                params=searxng_params(query),
                headers=searxng_headers(),
                timeout=20.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            errors.append(f"{url} -> {exc}")
            logger.warning("SearXNG request failed at %s: %s", url, exc)

    logger.error("SearXNG search failed for query='%s' after trying all URLs", query)
    raise ValueError(
        "SearXNG search failed. Tried URLs: "
        + "; ".join(build_candidate_searxng_urls())
        + ". Last errors: "
        + " | ".join(errors)
    )
