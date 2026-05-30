#!/usr/bin/env python3
"""mq-hal tools: list available HAL tools from config/tools.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
TOOLS_PATH = BASE_DIR / "config" / "tools.json"
sys.path.insert(0, str(BASE_DIR))

from mq_hal.tools.registry import load_registry, validate_registry  # noqa: E402


def load_tools() -> list[dict[str, Any]]:
    try:
        tools = load_registry(TOOLS_PATH)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: could not load {TOOLS_PATH}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    errors = validate_registry(tools)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    return tools


def render(tools: list[dict[str, Any]]) -> None:
    print("HAL Tools")
    print("=========")
    print()
    print(f"{'NAME':<20}  {'RISK':<12}  {'AI':<3}  DESCRIPTION")
    print(f"{'-' * 20}  {'-' * 12}  {'-' * 3}  {'-' * 40}")
    for tool in tools:
        name = str(tool.get("name", "-"))
        risk = str(tool.get("risk_level", "-"))
        ai = "yes" if tool.get("uses_ai") else "no"
        desc = str(tool.get("description", "-"))
        print(f"{name:<20}  {risk:<12}  {ai:<3}  {desc}")
    print()
    print(f"{len(tools)} tools. See docs/COMMAND_SURFACE.md for full reference.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal tools",
        description="List available HAL tools.",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Validate config/tools.json and exit",
    )
    args = parser.parse_args(argv)

    tools = load_tools()

    if args.check:
        print(f"OK: {len(tools)} tools validated")
        return 0

    if args.json_out:
        print(json.dumps({"tools": tools}, indent=2, ensure_ascii=False))
        return 0

    render(tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
