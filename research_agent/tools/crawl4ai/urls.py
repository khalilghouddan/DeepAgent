"""URL normalization helpers for Crawl4AI tools."""

from __future__ import annotations

from urllib.parse import urlsplit


def normalize_url_list(urls: str | list[str]) -> list[str]:
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
