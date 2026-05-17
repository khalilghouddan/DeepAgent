"""Sub-agent configuration helpers."""

from research_agent.prompts import RESEARCHER_INSTRUCTIONS


def build_research_sub_agent(
    search_date: str,
    language_instruction: str,
    tools: list,
) -> dict:
    """Build the researcher sub-agent configuration."""
    return {
        "name": "research-agent",
        "description": "Delegate research to the sub-agent researcher.",
        "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=search_date)
        + language_instruction,
        "tools": tools,
    }
