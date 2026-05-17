"""Model client adapters used by the deep research agent."""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI


class StringContentChatOpenAI(ChatOpenAI):
    """ChatOpenAI variant for endpoints that only accept string message content."""

    @staticmethod
    def _content_to_string(content: Any) -> str:
        """Convert LangChain message content blocks into a plain string."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or item))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    def _normalize_messages(self, messages):
        """Return copies of messages with string-only content."""
        return [
            message.model_copy(
                update={"content": self._content_to_string(message.content)}
            )
            for message in messages
        ]

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Synchronously generate after normalizing message content."""
        return super()._generate(
            self._normalize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """Asynchronously generate after normalizing message content."""
        return await super()._agenerate(
            self._normalize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )
