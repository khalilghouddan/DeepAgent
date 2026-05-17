"""SearXNG result formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def source_rows_from_results(
    search_results: dict[str, Any],
    max_results: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in search_results.get("results", [])[:max_results]:
        url = result.get("url")
        if not url:
            continue

        rows.append(
            {
                "title": result.get("title", "Untitled result"),
                "url": url,
                "snippet": result.get("content", ""),
            }
        )
    return rows


def format_search_candidates(source_rows: list[dict[str, str]]) -> str:
    result_texts = []
    for index, row in enumerate(source_rows, start=1):
        result_texts.append(
            f"""## Result {index}: {row['title']}
**URL:** {row['url']}

{row['snippet']}

---
"""
        )
    return "\n".join(result_texts)


def format_tool_response(query: str, source_rows: list[dict[str, str]]) -> str:
    urls = [row["url"] for row in source_rows]
    return f"""Found {len(source_rows)} SearXNG result(s) for '{query}'.

Use crawl4ai_scrape_urls with all of these URLs before writing findings:
{json.dumps(urls, ensure_ascii=False, indent=2)}

Search candidates:

{format_search_candidates(source_rows)}"""


def format_source_summary(source_rows: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{index}. {row['title']}: {row['url']}"
        for index, row in enumerate(source_rows, start=1)
    )
