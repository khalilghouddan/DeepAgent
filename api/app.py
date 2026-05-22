"""FastAPI application setup and routes."""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .errors import (
    ResearchExecutionError,
    ResearchTimeoutError,
    http_error_for_research_failure,
)
from .schemas import ResearchRequest, ResearchResponse
from .research import run_research_with_timeout

logger = logging.getLogger(__name__)

app = FastAPI(title="Deep Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    load_dotenv(".env", override=False)


@app.post("/api/research", response_model=ResearchResponse)
def run_research(payload: ResearchRequest) -> ResearchResponse:
    try:
        return run_research_with_timeout(payload)
    except ResearchTimeoutError as exc:
        logger.warning("Research request timed out: %s", exc)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ResearchExecutionError as exc:
        logger.exception("Research execution failed")
        raise http_error_for_research_failure(exc) from exc
    except Exception as exc:
        logger.exception("Research execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
