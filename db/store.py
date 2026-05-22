from __future__ import annotations

import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
TOOL_CALL_PATTERN = re.compile(r"Tool Call:\s*([^\n]+)")
SEARXNG_CALL_TITLE = "Tool Call: searxng_search"
SEARXNG_OUTPUT_TITLE = "Tool Output: searxng_search"
SEARCH_QUERY_PATTERN = re.compile(r"^Query:\s*(.+)$", re.MULTILINE)
SEARCH_MAX_RESULTS_PATTERN = re.compile(r"^Max results:\s*(\d+)$", re.MULTILINE)
SEARCH_RESULT_COUNT_PATTERN = re.compile(
    r"Found\s+(\d+)\s+SearXNG result\(s\)",
    re.IGNORECASE,
)
SEARCH_CANDIDATE_PATTERN = re.compile(
    r"^## Result\s+(\d+):\s*(.+?)\n"
    r"\*\*URL:\*\*\s*(\S+)\n\n"
    r"(.*?)(?=\n---|\Z)",
    re.MULTILINE | re.DOTALL,
)
SEARCH_SUMMARY_PATTERN = re.compile(
    r"^\s*(\d+)\.\s*(.+):\s*(https?://\S+)\s*$",
    re.MULTILINE,
)


def db_enabled() -> bool:
    value = os.getenv("DEEP_AGENT_DB_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def connection_kwargs() -> dict[str, Any]:
    return {
        "host": os.getenv("DEEP_AGENT_DB_HOST", "localhost"),
        "port": int(os.getenv("DEEP_AGENT_DB_PORT", "5433")),
        "dbname": os.getenv("DEEP_AGENT_DB_NAME", "crawl4ai_results"),
        "user": os.getenv("DEEP_AGENT_DB_USER", "postgres"),
        "password": os.getenv("DEEP_AGENT_DB_PASSWORD", "08012025"),
    }


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Missing psycopg. Install requirements or rebuild the API image."
        ) from exc

    return psycopg.connect(**connection_kwargs())


def init_db() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()


def _extract_tool_name(message: dict[str, str | None]) -> str | None:
    explicit_tool_name = message.get("tool_name")
    if explicit_tool_name:
        return explicit_tool_name

    if (message.get("type") or "").lower() == "tool":
        content = message.get("content", "")
        match = TOOL_CALL_PATTERN.search(content)
        if match:
            return match.group(1).strip()
        return message.get("title") or "Tool"
    return None


def _search_query_from_content(content: str) -> tuple[str | None, int | None]:
    query_match = SEARCH_QUERY_PATTERN.search(content)
    max_results_match = SEARCH_MAX_RESULTS_PATTERN.search(content)
    max_results = int(max_results_match.group(1)) if max_results_match else None
    return (query_match.group(1).strip() if query_match else None, max_results)


def _search_result_count_from_content(content: str) -> int | None:
    match = SEARCH_RESULT_COUNT_PATTERN.search(content)
    return int(match.group(1)) if match else None


def _search_sources_from_content(content: str) -> list[dict[str, str | int]]:
    sources: list[dict[str, str | int]] = []
    seen_urls: set[str] = set()

    for match in SEARCH_CANDIDATE_PATTERN.finditer(content):
        url = match.group(3).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append(
            {
                "position": int(match.group(1)),
                "title": match.group(2).strip(),
                "url": url,
                "snippet": match.group(4).strip(),
            }
        )

    if sources:
        return sources

    for match in SEARCH_SUMMARY_PATTERN.finditer(content):
        url = match.group(3).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append(
            {
                "position": int(match.group(1)),
                "title": match.group(2).strip(),
                "url": url,
                "snippet": "",
            }
        )
    return sources


def _extract_searches(
    process: list[dict[str, str | None]],
) -> list[dict[str, Any]]:
    searches: list[dict[str, Any]] = []
    pending_search: dict[str, Any] | None = None

    for message in process:
        title = message.get("title") or ""
        content = message.get("content") or ""
        tool_name = _extract_tool_name(message)

        is_call = title == SEARXNG_CALL_TITLE
        if is_call:
            query, max_results = _search_query_from_content(content)
            if query:
                pending_search = {
                    "query": query,
                    "max_results": max_results,
                    "result_count": None,
                    "sources": [],
                }
                searches.append(pending_search)
            continue

        is_output = title == SEARXNG_OUTPUT_TITLE or tool_name == "searxng_search"
        if not is_output:
            continue

        sources = _search_sources_from_content(content)
        result_count = _search_result_count_from_content(content)

        if pending_search is None:
            query_match = re.search(r"for '(.+?)'", content)
            pending_search = {
                "query": query_match.group(1) if query_match else "unknown",
                "max_results": None,
                "result_count": result_count,
                "sources": sources,
            }
            searches.append(pending_search)
            continue

        pending_search["result_count"] = result_count
        pending_search["sources"] = sources
        pending_search = None

    return searches


def _save_searches(cur: Any, run_id: str, process: list[dict[str, str | None]]) -> None:
    for position, search in enumerate(_extract_searches(process), start=1):
        sources = search.get("sources") or []
        search_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO deep_agent_searches (
                id,
                run_id,
                position,
                query,
                max_results,
                source_count
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                search_id,
                run_id,
                position,
                search["query"],
                search.get("max_results"),
                search.get("result_count") if search.get("result_count") is not None else len(sources),
            ),
        )
        for source in sources:
            cur.execute(
                """
                INSERT INTO deep_agent_search_sources (
                    search_id,
                    position,
                    title,
                    url,
                    snippet
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    search_id,
                    source["position"],
                    source["title"],
                    source["url"],
                    source["snippet"],
                ),
            )


def save_research_result(
    *,
    query: str,
    answer: str,
    report_content: str | None,
    process: list[dict[str, str | None]],
    search_language: str,
    search_date: str | None,
    model_name: str,
) -> str | None:
    if not db_enabled():
        return None

    run_id = str(uuid.uuid4())
    metadata = {
        "process_count": len(process),
    }

    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO deep_agent_runs (
                        id,
                        query,
                        answer,
                        report_content,
                        search_language,
                        search_date,
                        model_name,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        run_id,
                        query,
                        answer,
                        report_content,
                        search_language,
                        search_date,
                        model_name,
                        json.dumps(metadata),
                    ),
                )
                for position, message in enumerate(process, start=1):
                    cur.execute(
                        """
                        INSERT INTO deep_agent_process_messages (
                            run_id,
                            position,
                            message_type,
                            title,
                            tool_name,
                            content
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            run_id,
                            position,
                            message.get("type") or "",
                            message.get("title") or "",
                            _extract_tool_name(message),
                            message.get("content") or "",
                        ),
                    )
                _save_searches(cur, run_id, process)
            conn.commit()
        logger.info("Saved deep-agent research run to Postgres: %s", run_id)
        return run_id
    except Exception as exc:
        logger.warning("Could not save deep-agent run to Postgres: %s", exc)
        return None


if __name__ == "__main__":
    load_dotenv(".env", override=False)
    init_db()
    print("Deep-agent database tables are ready.")
