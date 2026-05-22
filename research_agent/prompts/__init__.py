"""Prompt templates for the research deep agent."""

from .delegation_prompt import SUBAGENT_DELEGATION_INSTRUCTIONS
from .researcher_prompt import RESEARCHER_INSTRUCTIONS
from .workflow_prompt import RESEARCH_WORKFLOW_INSTRUCTIONS

__all__ = [
    "RESEARCHER_INSTRUCTIONS",
    "RESEARCH_WORKFLOW_INSTRUCTIONS",
    "SUBAGENT_DELEGATION_INSTRUCTIONS",
]
