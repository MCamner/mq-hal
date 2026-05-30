#!/usr/bin/env python3
"""mq-hal model-test: run a tiny structured Ollama generation test."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from model_profiles import model_for_profile

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

TEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "message": {"type": "string"},
    },
    "required": ["status", "message"],
    "additionalProperties": False,
}

SAMPLE_RESULT: dict[str, Any] = {
    "profile": "router",
    "model": "qwen3:4b-instruct",
    "ok": True,
    "latency_ms": 35,
    "response": {"status": "ok", "message": "ready"},
}


def call_model(profile: str) -> dict[str, Any]:
    model, selected = model_for_profile(
        profile,
        default_profile="router",
        env_default="qwen3:4b-instruct",
    )
    payload = {
        "model": model,
        "system": "Return only JSON matching the requested schema.",
        "prompt": "Return status ok and message ready.",
        "format": TEST_SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {
            "profile": selected,
            "model": model,
            "ok": False,
            "latency_ms": None,
            "error": str(exc),
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "profile": selected,
            "model": model,
            "ok": False,
            "latency_ms": None,
            "error": str(exc),
        }

    latency_ms = int((time.perf_counter() - started) * 1000)
    raw = envelope.get("response")
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError:
        parsed = None
    ok = (
        isinstance(parsed, dict)
        and parsed.get("status") == "ok"
        and isinstance(parsed.get("message"), str)
    )
    result: dict[str, Any] = {
        "profile": selected,
        "model": model,
        "ok": ok,
        "latency_ms": latency_ms,
        "response": parsed,
    }
    if not ok:
        result["error"] = "model response did not match schema"
    return result


def render(result: dict[str, Any]) -> None:
    print("HAL Model Test")
    print("==============")
    print()
    print(f"Profile: {result.get('profile', '-')}")
    print(f"Model:   {result.get('model', '-')}")
    print(f"OK:      {'yes' if result.get('ok') else 'no'}")
    latency = result.get("latency_ms")
    print(f"Latency: {latency} ms" if isinstance(latency, int) else "Latency: -")
    if result.get("error"):
        print(f"Error:   {result['error']}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal model-test",
        description="Run a tiny structured generation test against Ollama.",
    )
    parser.add_argument("--profile", default="router")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = dict(SAMPLE_RESULT) if args.sample else call_model(args.profile)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json_out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
