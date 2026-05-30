#!/usr/bin/env python3
"""mq-hal model-status: check configured Ollama model availability."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from model_profiles import load_model_profiles, model_for_profile

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


SAMPLE_STATUS: dict[str, Any] = {
    "ollama_url": "http://localhost:11434",
    "reachable": True,
    "latency_ms": 12,
    "profiles": {
        "router": {
            "model": "qwen3:4b-instruct",
            "available": True,
            "reasoning_effort": "low",
        },
        "planner": {
            "model": "qwen3:8b",
            "available": True,
            "reasoning_effort": "medium",
        },
        "critic": {
            "model": "qwen3:8b",
            "available": True,
            "reasoning_effort": "high",
        },
        "code": {
            "model": "qwen2.5-coder:7b",
            "available": False,
            "reasoning_effort": "medium",
        },
    },
}


def fetch_ollama_models() -> tuple[bool, int | None, set[str], str | None]:
    url = f"{OLLAMA_URL.rstrip('/')}/api/tags"
    request = urllib.request.Request(url, method="GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return False, None, set(), str(exc)
    except (OSError, json.JSONDecodeError) as exc:
        return False, None, set(), str(exc)

    latency_ms = int((time.perf_counter() - started) * 1000)
    models: set[str] = set()
    for item in body.get("models", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if isinstance(name, str):
            models.add(name)
            models.add(name.split(":", 1)[0])
    return True, latency_ms, models, None


def build_status(sample: bool = False, profile_name: str | None = None) -> dict[str, Any]:
    if sample:
        data = dict(SAMPLE_STATUS)
        if profile_name:
            data["profiles"] = {
                key: value
                for key, value in SAMPLE_STATUS["profiles"].items()
                if key == profile_name
            }
        return data

    profiles_data = load_model_profiles()
    profiles_raw = profiles_data.get("profiles", {})
    profiles = profiles_raw if isinstance(profiles_raw, dict) else {}
    reachable, latency_ms, available_models, error = fetch_ollama_models()

    selected_profiles = profiles
    if profile_name:
        try:
            model_for_profile(
                profile_name,
                default_profile=str(profiles_data.get("default", "router")),
                env_default="",
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        selected_profiles = {
            profile_name: profiles.get(profile_name, {})
        }

    profile_status: dict[str, Any] = {}
    for name, profile in selected_profiles.items():
        if not isinstance(profile, dict):
            continue
        model = str(profile.get("model", ""))
        profile_status[name] = {
            "model": model,
            "available": reachable and model in available_models,
            "reasoning_effort": profile.get("reasoning_effort", "unknown"),
        }

    result: dict[str, Any] = {
        "ollama_url": OLLAMA_URL,
        "reachable": reachable,
        "latency_ms": latency_ms,
        "profiles": profile_status,
    }
    if error:
        result["error"] = error
    return result


def render(data: dict[str, Any]) -> None:
    reachable = "yes" if data.get("reachable") else "no"
    latency = data.get("latency_ms")
    latency_text = f"{latency} ms" if isinstance(latency, int) else "-"

    print("HAL Model Status")
    print("================")
    print()
    print(f"Ollama:  {data.get('ollama_url', '-')}")
    print(f"Reachable: {reachable}")
    print(f"Latency:   {latency_text}")
    if data.get("error"):
        print(f"Error:     {data['error']}")
    print()
    print(f"{'PROFILE':<10}  {'MODEL':<28}  {'AVAILABLE':<9}  EFFORT")
    print(f"{'-' * 10}  {'-' * 28}  {'-' * 9}  {'-' * 8}")
    for name, profile in data.get("profiles", {}).items():
        available = "yes" if profile.get("available") else "no"
        model = str(profile.get("model", "-"))
        effort = str(profile.get("reasoning_effort", "-"))
        print(f"{name:<10}  {model:<28}  {available:<9}  {effort}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal model-status",
        description="Check configured Ollama model availability.",
    )
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--profile", help="Only check one configured profile")
    args = parser.parse_args(argv)

    try:
        data = build_status(sample=args.sample, profile_name=args.profile)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
