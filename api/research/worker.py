"""Research subprocess worker."""

from __future__ import annotations

import logging
import multiprocessing

from dotenv import load_dotenv

from api.schemas import model_dump

from .execution import execute_research

logger = logging.getLogger(__name__)


def research_worker(
    payload: dict,
    result_queue: multiprocessing.Queue,
) -> None:
    """Run research in a child process and send a serializable result."""
    load_dotenv(".env", override=False)
    try:
        response = execute_research(payload)
        result_queue.put({"ok": True, "response": model_dump(response)})
    except Exception as exc:
        logger.exception("Research execution failed")
        result_queue.put(
            {
                "ok": False,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }
        )


def multiprocessing_context() -> multiprocessing.context.BaseContext:
    try:
        return multiprocessing.get_context("fork")
    except ValueError:
        return multiprocessing.get_context()
