"""Factory for building the deep research agent."""

from __future__ import annotations

from datetime import datetime

from deepagents import create_deep_agent

from research_agent.prompts import (
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from research_agent.tools import (
    crawl4ai_scrape_url,
    crawl4ai_scrape_urls,
    searxng_search,
    think_tool,
)
from .language import build_language_instruction
from .model_builder import build_chat_model
from .subagents import build_research_sub_agent


def build_agent(
    api_key: str,
    base_url: str | None,
    model_name: str,
    max_concurrent_research_units: int = 1,
    max_researcher_iterations: int = 1,
    search_date: str | None = None,
    response_language: str = "any",
    string_content_messages: bool = False,
):
    """Build the deep research agent with tools, prompts, and sub-agent setup."""
    if not search_date:
        search_date = datetime.now().strftime("%Y-%m-%d")

    language_instruction = build_language_instruction(response_language)
    tools = [
        searxng_search,
        crawl4ai_scrape_urls,
        crawl4ai_scrape_url,
        think_tool,
    ]
    research_sub_agent = build_research_sub_agent(
        search_date=search_date,
        language_instruction=language_instruction,
        tools=tools,
    )

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

    return create_deep_agent(
        model=build_chat_model(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            string_content_messages=string_content_messages,
        ),
        tools=tools,
        system_prompt=instructions,
        subagents=[research_sub_agent],
    )
