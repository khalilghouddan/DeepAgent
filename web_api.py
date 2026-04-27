from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from deep_research_searxng import build_agent, configure_logging
from utils import format_message_content

logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)
    search_language: str = "any"
    log_level: str = "INFO"
    search_date: str | None = None


class ResearchResponse(BaseModel):
    answer: str
    process: list[dict[str, str]] = Field(default_factory=list)


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


def _serialize_process(messages: list[Any]) -> list[dict[str, str]]:
    serialized: list[dict[str, str]] = []
    for message in messages:
        msg_type = message.__class__.__name__.replace("Message", "")
        content = format_message_content(message).strip()
        if not content:
            continue
        serialized.append(
            {
                "type": msg_type,
                "title": _message_title(msg_type),
                "content": content,
            }
        )
    return serialized


@app.on_event("startup")
def startup() -> None:
    load_dotenv(".env", override=True)


@app.post("/api/research", response_model=ResearchResponse)
def run_research(payload: ResearchRequest) -> ResearchResponse:
    configure_logging(payload.log_level)
    os.environ["SEARXNG_LANGUAGE"] = payload.search_language
    response_language = _normalize_response_language(payload.search_language)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="Missing OPENAI_API_KEY in .env"
        )

    try:
        agent = build_agent(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_concurrent_research_units=int(
                os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", "1")
            ),
            max_researcher_iterations=int(
                os.getenv("MAX_RESEARCHER_ITERATIONS", "1")
            ),
            search_date=payload.search_date,
            response_language=response_language,
        )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": payload.query}]}
        )
        messages = result.get("messages", [])
        answer = _extract_final_answer(messages)
        process = _serialize_process(messages)
        return ResearchResponse(answer=answer, process=process)
    except Exception as exc:
        logger.exception("Research execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
