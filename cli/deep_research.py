"""CLI for running the deep research agent."""

from __future__ import annotations

import argparse
import logging
import os

from dotenv import load_dotenv

from config import configure_logging
from research_agent.core import build_agent
from research_agent.utils import format_messages

logger = logging.getLogger(__name__)


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
