"""Model provider resolution and model construction."""

from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI

from model_config import StringContentChatOpenAI


def resolve_model_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve local or OpenAI provider settings from request and environment."""
    provider = str(
        payload.get("model_provider") or os.getenv("MODEL_PROVIDER", "openai")
    ).strip().lower()

    if provider == "local":
        model_name = os.getenv("CHAT_MODEL", "").strip()
        base_url = os.getenv("BASE_URL", "").strip()
        api_key = os.getenv("API_KEY", "").strip()
        if not model_name:
            raise ValueError("Missing CHAT_MODEL in .env for local provider")
        if not base_url:
            raise ValueError("Missing BASE_URL in .env for local provider")
        if not api_key:
            raise ValueError("Missing API_KEY in .env for local provider")
        return {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "string_content_messages": True,
        }

    if provider in {"openai", ""}:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env for OpenAI provider")
        return {
            "provider": "openai",
            "api_key": api_key,
            "base_url": os.getenv("OPENAI_BASE_URL", "").strip(),
            "model_name": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            or "gpt-4o-mini",
            "string_content_messages": False,
        }

    raise ValueError("model_provider must be either 'local' or 'openai'")


def build_chat_model(model_config: dict[str, Any]):
    """Build a direct chat model for structured-output repair."""
    model_cls = (
        StringContentChatOpenAI
        if model_config.get("string_content_messages")
        else ChatOpenAI
    )
    model_kwargs = {
        "model": model_config["model_name"],
        "api_key": model_config["api_key"],
        "temperature": 0,
    }
    if model_config.get("base_url"):
        model_kwargs["base_url"] = model_config["base_url"]
    return model_cls(**model_kwargs)
