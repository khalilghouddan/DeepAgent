"""Research request execution."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from config import configure_logging
from db.store import save_research_result
from research_agent.core import build_agent
from research_agent.tools import (
    get_research_trace,
    reset_research_trace,
    start_research_trace,
)

from api.message_serialization import (
    MISSING_FINAL_ANSWER,
    extract_final_answer,
    extract_report_content,
    message_to_text,
    serialize_process,
)
from api.model_provider import build_chat_model, resolve_model_config
from api.schemas import ResearchResponse
from api.structured_output import (
    coerce_structured_answer,
    normalize_output_schema,
    query_with_output_schema,
)

from .env import env_int, normalize_response_language


logger = logging.getLogger(__name__)


def _truncate_text(text: str, limit: int) -> str:
    """Keep fallback prompts bounded while preserving the earliest evidence."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[truncated]"


def _format_process_for_fallback(process: list[dict[str, str | None]]) -> str:
    """Build a compact research transcript for answer recovery."""
    chunks: list[str] = []
    for row in process:
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        title = str(row.get("title") or row.get("type") or "Process").strip()
        chunks.append(f"{title}:\n{_truncate_text(content, 6000)}")
    return _truncate_text("\n\n".join(chunks), 30000)


def _synthesize_missing_answer(
    *,
    original_query: str,
    process: list[dict[str, str | None]],
    output_schema: dict[str, Any] | None,
    model_config: dict[str, Any],
) -> str:
    """Recover a final answer when the agent produced tool work but no reply."""
    transcript = _format_process_for_fallback(process)
    if not transcript:
        return MISSING_FINAL_ANSWER

    schema_instruction = ""
    if output_schema:
        schema_instruction = (
            "\nThe user requested structured output. Return ONLY valid JSON that "
            "can satisfy this JSON Schema, with no Markdown or commentary:\n"
            f"{json.dumps(output_schema, ensure_ascii=False)}\n"
        )

    prompt = (
        "The research agent completed useful tool work but did not write a final "
        "assistant answer. Write the missing final answer using only the user "
        "request and the collected process/tool outputs below. Do not mention "
        "internal tools, missing messages, or this recovery step."
        f"{schema_instruction}\n\n"
        f"User request:\n{original_query}\n\n"
        f"Collected process/tool outputs:\n{transcript}"
    )
    response = build_chat_model(model_config).invoke(prompt)
    recovered = message_to_text(getattr(response, "content", response))
    return recovered or MISSING_FINAL_ANSWER


def execute_research(payload: dict[str, Any]) -> ResearchResponse:
    """Execute one research request in the worker process."""
    configure_logging(str(payload.get("log_level") or "INFO"))
    search_language = str(payload.get("search_language") or "any")
    os.environ["SEARXNG_LANGUAGE"] = search_language
    if payload.get("max_sources"):
        os.environ["SEARXNG_MAX_RESULTS"] = str(payload["max_sources"])
    if payload.get("crawl4ai_batch_size"):
        os.environ["CRAWL4AI_BATCH_SIZE"] = str(payload["crawl4ai_batch_size"])
    response_language = normalize_response_language(search_language)
    output_schema = normalize_output_schema(payload.get("output_schema"))
    trace_token = start_research_trace()

    try:
        model_config = resolve_model_config(payload)

        agent = build_agent(
            api_key=model_config["api_key"],
            base_url=model_config["base_url"],
            model_name=model_config["model_name"],
            max_concurrent_research_units=env_int("MAX_CONCURRENT_RESEARCH_UNITS", 1),
            max_researcher_iterations=int(
                payload.get("researcher_iterations")
                or env_int("MAX_RESEARCHER_ITERATIONS", 1)
            ),
            search_date=payload.get("search_date"),
            response_language=response_language,
            string_content_messages=model_config["string_content_messages"],
        )

        user_query = query_with_output_schema(str(payload["query"]), output_schema)
        result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})
        messages = result.get("messages", [])
        report_content = extract_report_content(messages)
        answer = extract_final_answer(messages)
        process = serialize_process(messages)
        process.extend(get_research_trace())
        if answer == MISSING_FINAL_ANSWER:
            logger.info("Final assistant answer missing; synthesizing from process.")
            answer = _synthesize_missing_answer(
                original_query=str(payload["query"]),
                process=process,
                output_schema=output_schema,
                model_config=model_config,
            )
        structured_answer = coerce_structured_answer(
            answer,
            output_schema,
            model_config,
        )
        if structured_answer is not None:
            answer = json.dumps(structured_answer, ensure_ascii=False, indent=2)
        save_research_result(
            query=str(payload["query"]),
            answer=answer,
            report_content=report_content or None,
            process=process,
            search_language=search_language,
            search_date=payload.get("search_date"),
            model_name=model_config["model_name"],
        )
        return ResearchResponse(
            answer=answer,
            report_content=report_content or None,
            structured_answer=structured_answer,
            process=process,
        )
    finally:
        reset_research_trace(trace_token)
