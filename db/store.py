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


def save_research_result(
    *,
    query: str,
    answer: str,
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
                        search_language,
                        search_date,
                        model_name,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        run_id,
                        query,
                        answer,
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
