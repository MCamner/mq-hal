#!/usr/bin/env python3
"""mq-hal env-status: HAL environment variables and tool availability report."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]

# HAL-relevant environment variables.
# (name, default, sensitive)
_HAL_VARS: list[tuple[str, str, bool]] = [
    ("OLLAMA_URL",          "http://localhost:11434", False),
    ("OLLAMA_MODEL",        "qwen3:4b-instruct",      False),
    ("MQ_HAL_STATE_DIR",    "~/.mq-hal",              False),
    ("MQ_HAL_CONFIG_PATH",  "(not set)",              False),
    ("EDITOR",              "(not set)",              False),
    ("VISUAL",              "(not set)",              False),
]

# Vars that should never have their values printed.
_SENSITIVE_PATTERNS = re.compile(
    r"(API_KEY|SECRET|TOKEN|PASSWORD|BEARER|PRIVATE)",
    re.IGNORECASE,
)

# Tools to check: (binary, label, required)
_TOOLS: list[tuple[str, str, bool]] = [
    ("python3",          "Python 3",          True),
    ("git",              "git",               True),
    ("ollama",           "Ollama",            False),
    ("rg",               "ripgrep",           False),
    ("gh",               "GitHub CLI",        False),
    ("mqlaunch",         "mqlaunch",          False),
    ("repo-signal",      "repo-signal",       False),
    ("mq-agent",         "mq-agent",          False),
    ("mq-image-analyze", "mq-image-analyze",  False),
    ("code",             "VS Code (code)",    False),
]


def _env_value(name: str, default: str, sensitive: bool) -> tuple[str, str]:
    """Return (raw_value, display_value)."""
    raw = os.environ.get(name, "")
    if not raw:
        return "", default

    if sensitive or _SENSITIVE_PATTERNS.search(name):
        return raw, "[REDACTED]"

    return raw, raw


def check_env() -> list[dict[str, Any]]:
    results = []
    for name, default, sensitive in _HAL_VARS:
        raw, display = _env_value(name, default, sensitive)
        results.append({
            "name": name,
            "set": bool(raw),
            "value": display,
            "default": default,
            "is_default": not raw,
        })
    return results


def check_tools() -> list[dict[str, Any]]:
    results = []
    for binary, label, required in _TOOLS:
        path = shutil.which(binary)
        results.append({
            "binary": binary,
            "label": label,
            "required": required,
            "available": bool(path),
            "path": path or "",
        })
    return results


def build_recommendations(
    env: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []

    tools_by_binary = {t["binary"]: t for t in tools}

    if not tools_by_binary.get("ollama", {}).get("available"):
        recs.append({
            "level": "warn",
            "component": "Ollama",
            "message": (
                "Ollama not found. AI routing is unavailable. "
                "Deterministic fallback is active. "
                "Fix: install Ollama from https://ollama.com and run "
                "`ollama pull qwen3:4b-instruct`."
            ),
        })

    if not tools_by_binary.get("rg", {}).get("available"):
        recs.append({
            "level": "info",
            "component": "ripgrep",
            "message": (
                "ripgrep (rg) not found. The `grep_repo` intent will "
                "fail if routed. Fix: `brew install ripgrep`."
            ),
        })

    if not tools_by_binary.get("gh", {}).get("available"):
        recs.append({
            "level": "info",
            "component": "GitHub CLI",
            "message": (
                "gh CLI not found. GitHub release tag check in "
                "release-check.sh will be skipped. "
                "Fix: `brew install gh && gh auth login`."
            ),
        })

    if not tools_by_binary.get("mqlaunch", {}).get("available"):
        recs.append({
            "level": "info",
            "component": "mqlaunch",
            "message": (
                "mqlaunch not found. The `run_mqlaunch` intent will "
                "fail if routed."
            ),
        })

    missing_required = [
        t for t in tools if t["required"] and not t["available"]
    ]
    for t in missing_required:
        recs.append({
            "level": "error",
            "component": t["label"],
            "message": f"{t['label']} ({t['binary']}) is required but not found.",
        })

    if not recs:
        recs.append({
            "level": "ok",
            "component": "all",
            "message": "No degraded components detected.",
        })

    return recs


def render_text(
    env: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    recs: list[dict[str, str]],
) -> None:
    print("HAL Environment Status")
    print("======================")
    print()

    print("Environment variables")
    print("---------------------")
    for e in env:
        tag = "  SET" if e["set"] else "  ---"
        note = "" if e["set"] else f"  (default: {e['default']})"
        print(f"{tag}  {e['name']:24} {e['value']}{note}")
    print()

    print("Tool availability")
    print("-----------------")
    for t in tools:
        mark = " ok " if t["available"] else "MISS"
        req = " (required)" if t["required"] and not t["available"] else ""
        path = f"  {t['path']}" if t["available"] else ""
        print(f"  [{mark}]  {t['label']:20}{req}{path}")
    print()

    print("Recommendations")
    print("---------------")
    icons = {"ok": "✓", "info": "i", "warn": "!", "error": "✗"}
    for r in recs:
        icon = icons.get(r["level"], "?")
        print(f"  [{icon}] {r['component']}: {r['message']}")
    print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal env-status",
        description="Show HAL environment variables and tool availability.",
    )
    parser.add_argument(
        "--json", action="store_true", help="JSON output"
    )
    parser.add_argument(
        "--no-recommendations", action="store_true",
        help="Skip degraded-mode recommendations",
    )
    args = parser.parse_args(argv)

    env = check_env()
    tools = check_tools()
    recs = [] if args.no_recommendations else build_recommendations(env, tools)

    if args.json:
        print(json.dumps({
            "env": env,
            "tools": tools,
            "recommendations": recs,
        }, indent=2, ensure_ascii=False))
        return 0

    render_text(env, tools, recs)

    # Non-zero exit if any required tool is missing.
    if any(t["required"] and not t["available"] for t in tools):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
