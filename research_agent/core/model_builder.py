"""Chat model construction helpers."""

from __future__ import annotations

import logging
import os

from langchain_openai import ChatOpenAI

from model_config import StringContentChatOpenAI

logger = logging.getLogger(__name__)


def build_chat_model(
    api_key: str,
    base_url: str | None,
    model_name: str,
    string_content_messages: bool,
):
    """Build a chat model for OpenAI-compatible providers."""
    normalized_base_url = (base_url or "").strip()
    if normalized_base_url:
        os.environ["OPENAI_BASE_URL"] = normalized_base_url
    else:
        os.environ.pop("OPENAI_BASE_URL", None)

    model_kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0,
    }
    if normalized_base_url:
        model_kwargs["base_url"] = normalized_base_url

    model_cls = StringContentChatOpenAI if string_content_messages else ChatOpenAI
    model = model_cls(**model_kwargs)
    logger.info(
        "Initialized %s model='%s'%s",
        model_cls.__name__,
        model_name,
        " with custom base_url" if normalized_base_url else "",
    )
    return model
