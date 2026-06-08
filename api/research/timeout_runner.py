"""Subprocess timeout handling for research requests."""

from __future__ import annotations

import multiprocessing
import queue
import time

from api.errors import ResearchExecutionError, ResearchTimeoutError
from api.schemas import ResearchRequest, ResearchResponse, model_dump

from .env_config import research_timeout_seconds
from .subprocess_worker import multiprocessing_context, research_worker


def _terminate_process(
    process: multiprocessing.context.Process,
    timeout_seconds: int | None,
) -> None:
    process.terminate()
    process.join(5)
    if process.is_alive():
        process.kill()
        process.join(5)
    if timeout_seconds is not None:
        raise ResearchTimeoutError(
            "Research timed out after "
            f"{timeout_seconds} seconds. Try a narrower query or lower "
            "MAX_RESEARCHER_ITERATIONS / MAX_CONCURRENT_RESEARCH_UNITS."
        )


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

    deadline = (
        time.monotonic() + timeout_seconds
        if timeout_seconds is not None
        else None
    )
    result: dict | None = None

    while result is None:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_process(process, timeout_seconds)
            wait_seconds = min(0.2, max(0.0, remaining))
        else:
            wait_seconds = 0.2

        try:
            # Read while the child is alive. Large process traces can otherwise
            # fill the pipe and make process.join() wait forever.
            result = result_queue.get(timeout=wait_seconds)
        except queue.Empty as exc:
            if process.is_alive():
                continue
            try:
                result = result_queue.get_nowait()
            except queue.Empty:
                raise RuntimeError(
                    "Research process exited without a response "
                    f"(exit code {process.exitcode})."
                ) from exc

    process.join(5)
    if process.is_alive():
        _terminate_process(process, None)

    if result.get("ok"):
        return ResearchResponse(**result["response"])
    raise ResearchExecutionError(
        result.get("error") or "Research execution failed",
        result.get("error_type"),
    )
