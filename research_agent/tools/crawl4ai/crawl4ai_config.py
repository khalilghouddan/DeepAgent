"""Crawl4AI environment configuration helpers."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)


def build_candidate_crawl4ai_urls() -> list[str]:
    """Return candidate Crawl4AI API roots for Docker and local runs."""
    configured = os.getenv("CRAWL4AI_URL", "").strip().rstrip("/")
    if not configured:
        return []

    candidates = [configured]
    parsed = urlsplit(configured)
    if parsed.hostname == "crawl4ai":
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


def crawl4ai_headers() -> dict[str, str]:
    token = os.getenv("CRAWL4AI_API_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def crawl4ai_scrape_paths() -> list[str]:
    configured = os.getenv("CRAWL4AI_SCRAPE_PATH", "").strip()
    candidates = [configured] if configured else ["/scrape", "/crawl"]

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


def crawl4ai_timeout(default: float = 60.0) -> float:
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


def crawl4ai_batch_size(default: int = 10) -> int:
    configured = os.getenv("CRAWL4AI_BATCH_SIZE", "").strip()
    if not configured:
        return default

    try:
        return max(1, int(configured))
    except ValueError:
        logger.warning(
            "Invalid CRAWL4AI_BATCH_SIZE=%r; using default %s",
            configured,
            default,
        )
        return default
