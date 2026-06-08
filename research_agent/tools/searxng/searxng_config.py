"""SearXNG environment configuration helpers."""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit


def resolve_max_results(max_results: int | None = None) -> int:
    if max_results and max_results > 0:
        return max_results
    try:
        return max(1, int(os.getenv("SEARXNG_MAX_RESULTS", "5")))
    except ValueError:
        return 5


def searxng_timeout(default: float = 30.0) -> float:
    configured = os.getenv("SEARXNG_TIMEOUT", "").strip()
    if not configured:
        return default

    try:
        return max(1.0, float(configured))
    except ValueError:
        return default


def build_candidate_searxng_urls() -> list[str]:
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


def searxng_params(query: str) -> dict[str, str]:
    params = {
        "q": query,
        "format": "json",
    }
    language = os.getenv("SEARXNG_LANGUAGE", "any").strip().lower()
    if language not in {"", "any", "all", "*"}:
        params["language"] = language
    return params


def searxng_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1",
    }
