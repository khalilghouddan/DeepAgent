"""Standalone script version of deep_research_searxng.ipynb.

Usage:
    python deep_research_searxng.py --query "What are the latest features of OpenAI?" --search-language any
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent
from research_agent.prompts import (
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from research_agent.tools import (
    crawl4ai_scrape_url,
    crawl4ai_scrape_urls,
    searxng_search,
    think_tool,
)
from utils import format_messages

logger = logging.getLogger(__name__)


def configure_logging(log_level: str) -> None:
    """Configure root logging for the CLI entrypoint."""
    level_name = (log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_agent(
    api_key: str,
    base_url: str | None,
    model_name: str,
    max_concurrent_research_units: int = 1,
    max_researcher_iterations: int = 1,
    search_date: str | None = None,
    response_language: str = "any",
):
    if not search_date:
        search_date = datetime.now().strftime("%Y-%m-%d")

    language = (response_language or "any").strip().lower()
    language_instruction = ""
    if language not in {"", "any", "all", "*"}:
        language_instruction = (
            "\n\nOutput language requirement: "
            f"write the final answer strictly in '{language}'."
        )

    research_sub_agent = {
        "name": "research-agent",
        "description": "Delegate research to the sub-agent researcher.",
        "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=search_date)
        + language_instruction,
        "tools": [
            searxng_search,
            crawl4ai_scrape_urls,
            crawl4ai_scrape_url,
            think_tool,
        ],
    }

    instructions = (
        RESEARCH_WORKFLOW_INSTRUCTIONS
        + "\n\n"
        + "=" * 80
        + "\n\n"
        + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
            max_concurrent_research_units=max_concurrent_research_units,
            max_researcher_iterations=max_researcher_iterations,
        )
        + language_instruction
    )

    normalized_base_url = (base_url or "").strip()
    model_kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0,
    }
    if normalized_base_url:
        model_kwargs["base_url"] = normalized_base_url

    model = ChatOpenAI(**model_kwargs)
    logger.info(
        "Initialized ChatOpenAI model='%s'%s",
        model_name,
        " with custom base_url" if normalized_base_url else "",
    )
    return create_deep_agent(
        model=model,
        tools=[
            searxng_search,
            crawl4ai_scrape_urls,
            crawl4ai_scrape_url,
            think_tool,
        ],
        system_prompt=instructions,
        subagents=[research_sub_agent],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deep research agent from a Python script."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="User question for the deep research agent.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", ""),
        help="Optional OpenAI-compatible base URL override.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key.",
    )
    parser.add_argument(
        "--max-concurrent-research-units",
        type=int,
        default=int(os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", "1")),
        help="Parallel sub-agent limit.",
    )
    parser.add_argument(
        "--max-researcher-iterations",
        type=int,
        default=int(os.getenv("MAX_RESEARCHER_ITERATIONS", "1")),
        help="Max delegation rounds.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--sources-json",
        default=os.getenv("SOURCES_JSON_PATH", "outputs/sources_history.json"),
        help="Path to append returned search sources as JSON history.",
    )
    parser.add_argument(
        "--search-language",
        default=os.getenv("SEARXNG_LANGUAGE", "any"),
        help=(
            "SearXNG language filter. Use 'any' for multilingual results, "
            "or a specific code like 'en', 'fr', 'ar'."
        ),
    )
    parser.add_argument(
        "--search-date",
        default="",
        help=(
            "Optional date override for prompts in YYYY-MM-DD format. "
            "Defaults to today's date."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(".env", override=False)
    args = parse_args()
    configure_logging(args.log_level)
    os.environ["SOURCES_JSON_PATH"] = args.sources_json
    os.environ["SEARXNG_LANGUAGE"] = args.search_language

    if not args.api_key:
        raise ValueError(
            "Missing API key. Set OPENAI_API_KEY in .env or pass --api-key."
        )
    logger.info("Building deep research agent")

    agent = build_agent(
        api_key=args.api_key,
        base_url=args.base_url,
        model_name=args.model,
        max_concurrent_research_units=args.max_concurrent_research_units,
        max_researcher_iterations=args.max_researcher_iterations,
        search_date=args.search_date,
    )

    logger.info("Invoking agent with query: %s", args.query)
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": args.query,
                }
            ],
        }
    )
    logger.info("Agent execution complete")
    format_messages(result["messages"])


if __name__ == "__main__":
    main()
