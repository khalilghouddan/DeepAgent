"""Research request execution."""

from __future__ import annotations

import json
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

from api.message_serialization import extract_final_answer, serialize_process
from api.model_provider import resolve_model_config
from api.schemas import ResearchResponse
from api.structured_output import (
    coerce_structured_answer,
    normalize_output_schema,
    query_with_output_schema,
)

from .env import env_int, normalize_response_language


def execute_research(payload: dict[str, Any]) -> ResearchResponse:
    """Execute one research request in the worker process."""
    configure_logging(str(payload.get("log_level") or "INFO"))
    search_language = str(payload.get("search_language") or "any")
    os.environ["SEARXNG_LANGUAGE"] = search_language
    if payload.get("max_sources"):
        os.environ["SEARXNG_MAX_RESULTS"] = str(payload["max_sources"])
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
        answer = extract_final_answer(messages)
        structured_answer = coerce_structured_answer(
            answer,
            output_schema,
            model_config,
        )
        if structured_answer is not None:
            answer = json.dumps(structured_answer, ensure_ascii=False, indent=2)
        process = serialize_process(messages)
        process.extend(get_research_trace())
        save_research_result(
            query=str(payload["query"]),
            answer=answer,
            process=process,
            search_language=search_language,
            search_date=payload.get("search_date"),
            model_name=model_config["model_name"],
        )
        return ResearchResponse(
            answer=answer,
            structured_answer=structured_answer,
            process=process,
        )
    finally:
        reset_research_trace(trace_token)
