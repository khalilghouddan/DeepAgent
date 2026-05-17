"""Crawl4AI response parsing and polling helpers."""

from __future__ import annotations

import time
from typing import Any

import httpx


def extract_crawl4ai_markdown(payload: Any) -> str:
    """Extract markdown from common Crawl4AI Docker response shapes."""
    if isinstance(payload, list):
        return "\n\n".join(
            text
            for item in payload
            if (text := extract_crawl4ai_markdown(item).strip())
        )

    if not isinstance(payload, dict):
        return ""

    for key in ("markdown", "markdown_v2", "fit_markdown"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested_key in ("raw_markdown", "fit_markdown", "markdown"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    return nested

    for key in ("result", "results", "data", "response"):
        value = payload.get(key)
        text = extract_crawl4ai_markdown(value)
        if text:
            return text

    for value in payload.values():
        text = extract_crawl4ai_markdown(value)
        if text:
            return text

    return ""


def crawl4ai_task_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    task_id = payload.get("task_id") or payload.get("id")
    return str(task_id) if task_id else ""


def poll_crawl4ai_task(
    client: httpx.Client,
    base_url: str,
    task_id: str,
    timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_payload: dict[str, Any] = {}

    while time.monotonic() < deadline:
        for path in (f"/task/{task_id}", f"/crawl/job/{task_id}"):
            response = client.get(f"{base_url}{path}")
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                last_payload = payload
                status = str(payload.get("status", "")).lower()
                if status in {"completed", "complete", "done", "success", "finished"}:
                    return payload
                if extract_crawl4ai_markdown(payload):
                    return payload
                if status in {"failed", "error"}:
                    raise ValueError(payload.get("error") or payload)
        time.sleep(1.0)

    raise TimeoutError(f"Crawl4AI task {task_id} did not finish: {last_payload}")
