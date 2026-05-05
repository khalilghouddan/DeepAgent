from __future__ import annotations

import logging
import multiprocessing
import os
import queue
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db.store import save_research_result
from deep_research_searxng import build_agent, configure_logging
from research_agent.tools import (
    get_research_trace,
    reset_research_trace,
    start_research_trace,
)
from utils import format_message_content

logger = logging.getLogger(__name__)


class ResearchTimeoutError(TimeoutError):
    """Raised when a research run exceeds the configured API timeout."""


class ResearchExecutionError(RuntimeError):
    """Raised when the worker process returns a typed research failure."""

    def __init__(self, message: str, error_type: str | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type or "RuntimeError"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)
    search_language: str = "any"
    log_level: str = "INFO"
    search_date: str | None = None


class ResearchResponse(BaseModel):
    answer: str
    process: list[dict[str, str | None]] = Field(default_factory=list)


def _normalize_response_language(search_language: str) -> str:
    value = (search_language or "any").strip().lower()
    if value in {"", "any", "all", "*"}:
        return "any"
    return value


app = FastAPI(title="Deep Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _message_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    chunks.append(text)
        return "\n".join(chunks).strip()

    return str(content).strip()


def _extract_final_answer(messages: list[Any]) -> str:
    for message in reversed(messages):
        if message.__class__.__name__.startswith("AI"):
            text = _message_to_text(getattr(message, "content", ""))
            if text:
                return text
    return "No final assistant answer was returned."


def _message_title(msg_type: str) -> str:
    if msg_type == "Human":
        return "Human"
    if msg_type == "Ai":
        return "Assistant"
    if msg_type == "Tool":
        return "Tool Output"
    return msg_type


def _serialize_process(messages: list[Any]) -> list[dict[str, str | None]]:
    serialized: list[dict[str, str | None]] = []
    for message in messages:
        msg_type = message.__class__.__name__.replace("Message", "")
        content = format_message_content(message).strip()
        if not content:
            continue
        row: dict[str, str | None] = {
            "type": msg_type,
            "title": _message_title(msg_type),
            "content": content,
        }
        tool_name = getattr(message, "name", None)
        if tool_name:
            row["tool_name"] = str(tool_name)
        serialized.append(row)
    return serialized


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, os.getenv(name), default)
        return default


def _research_timeout_seconds() -> int | None:
    configured = os.getenv("AGENT_TIMEOUT_SECONDS", "").strip()
    if not configured:
        return None

    try:
        timeout_seconds = int(configured)
    except ValueError:
        logger.warning(
            "Invalid AGENT_TIMEOUT_SECONDS=%r; running without a timeout",
            configured,
        )
        return None

    if timeout_seconds <= 0:
        return None

    return timeout_seconds


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _execute_research(payload: dict[str, Any]) -> ResearchResponse:
    configure_logging(str(payload.get("log_level") or "INFO"))
    search_language = str(payload.get("search_language") or "any")
    os.environ["SEARXNG_LANGUAGE"] = search_language
    response_language = _normalize_response_language(search_language)
    trace_token = start_research_trace()

    try:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env")

        agent = build_agent(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_concurrent_research_units=_env_int("MAX_CONCURRENT_RESEARCH_UNITS", 1),
            max_researcher_iterations=_env_int("MAX_RESEARCHER_ITERATIONS", 1),
            search_date=payload.get("search_date"),
            response_language=response_language,
        )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": payload["query"]}]}
        )
        messages = result.get("messages", [])
        answer = _extract_final_answer(messages)
        process = _serialize_process(messages)
        process.extend(get_research_trace())
        save_research_result(
            query=str(payload["query"]),
            answer=answer,
            process=process,
            search_language=search_language,
            search_date=payload.get("search_date"),
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )
        return ResearchResponse(answer=answer, process=process)
    finally:
        reset_research_trace(trace_token)


def _research_worker(
    payload: dict[str, Any],
    result_queue: multiprocessing.Queue,
) -> None:
    load_dotenv(".env", override=False)
    try:
        response = _execute_research(payload)
        result_queue.put({"ok": True, "response": _model_dump(response)})
    except Exception as exc:
        logger.exception("Research execution failed")
        result_queue.put(
            {
                "ok": False,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }
        )


def _multiprocessing_context() -> multiprocessing.context.BaseContext:
    try:
        return multiprocessing.get_context("fork")
    except ValueError:
        return multiprocessing.get_context()


def _run_research_with_timeout(payload: ResearchRequest) -> ResearchResponse:
    timeout_seconds = _research_timeout_seconds()
    context = _multiprocessing_context()
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_research_worker,
        args=(_model_dump(payload), result_queue),
        daemon=True,
    )
    process.start()
    process.join(timeout_seconds)

    if timeout_seconds is not None and process.is_alive():
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
        raise ResearchTimeoutError(
            "Research timed out after "
            f"{timeout_seconds} seconds. Try a narrower query or lower "
            "MAX_RESEARCHER_ITERATIONS / MAX_CONCURRENT_RESEARCH_UNITS."
        )

    try:
        result = result_queue.get_nowait()
    except queue.Empty as exc:
        raise RuntimeError(
            f"Research process exited without a response (exit code {process.exitcode})."
        ) from exc

    if result.get("ok"):
        return ResearchResponse(**result["response"])
    raise ResearchExecutionError(
        result.get("error") or "Research execution failed",
        result.get("error_type"),
    )


def _http_error_for_research_failure(exc: ResearchExecutionError) -> HTTPException:
    error_type = exc.error_type
    message = str(exc) or "Research execution failed"

    if error_type == "APIConnectionError":
        return HTTPException(
            status_code=502,
            detail=(
                "Could not connect to the model provider. Check OPENAI_BASE_URL, "
                "Docker/network connectivity, and provider availability. "
                f"Provider error: {message}"
            ),
        )
    if error_type == "AuthenticationError":
        return HTTPException(
            status_code=401,
            detail="Model provider authentication failed. Check OPENAI_API_KEY.",
        )
    if error_type == "PermissionDeniedError":
        return HTTPException(
            status_code=403,
            detail=f"Model provider permission denied: {message}",
        )
    if error_type == "NotFoundError":
        return HTTPException(
            status_code=404,
            detail=(
                "Model provider resource was not found. "
                f"Check OPENAI_MODEL. {message}"
            ),
        )
    if error_type == "BadRequestError":
        return HTTPException(
            status_code=400,
            detail=f"Model request failed: {message}",
        )
    if error_type == "RateLimitError":
        return HTTPException(
            status_code=429,
            detail=f"Model rate limit hit: {message}",
        )

    return HTTPException(status_code=500, detail=f"{error_type}: {message}")


@app.on_event("startup")
def startup() -> None:
    load_dotenv(".env", override=False)


@app.post("/api/research", response_model=ResearchResponse)
def run_research(payload: ResearchRequest) -> ResearchResponse:
    try:
        return _run_research_with_timeout(payload)
    except ResearchTimeoutError as exc:
        logger.warning("Research request timed out: %s", exc)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ResearchExecutionError as exc:
        logger.exception("Research execution failed")
        raise _http_error_for_research_failure(exc) from exc
    except Exception as exc:
        logger.exception("Research execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
