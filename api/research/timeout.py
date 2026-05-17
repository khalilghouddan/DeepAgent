"""Subprocess timeout handling for research requests."""

from __future__ import annotations

import multiprocessing
import queue

from api.errors import ResearchExecutionError, ResearchTimeoutError
from api.schemas import ResearchRequest, ResearchResponse, model_dump

from .env import research_timeout_seconds
from .worker import multiprocessing_context, research_worker


def run_research_with_timeout(payload: ResearchRequest) -> ResearchResponse:
    """Run research in a subprocess and enforce configured timeout."""
    timeout_seconds = research_timeout_seconds()
    context = multiprocessing_context()
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=research_worker,
        args=(model_dump(payload), result_queue),
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
