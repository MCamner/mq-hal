#!/usr/bin/env python3
"""Small dependency-free client for structured OpenAI Responses calls."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")


def _output_text(envelope: dict[str, Any]) -> str | None:
    for item in envelope.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict) or content.get("type") != "output_text":
                continue
            value = content.get("text")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def generate_structured(
    *,
    model: str,
    reasoning_effort: str,
    instructions: str,
    input_text: str,
    schema: dict[str, Any],
    schema_name: str,
    timeout: int = 120,
    max_output_tokens: int = 4096,
) -> str | None:
    """Return schema-constrained response text, or None on provider failure."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "reasoning": {"effort": reasoning_effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
        "max_output_tokens": max_output_tokens,
        "store": False,
    }
    request = urllib.request.Request(
        f"{OPENAI_BASE_URL.rstrip('/')}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    return _output_text(envelope) if isinstance(envelope, dict) else None
