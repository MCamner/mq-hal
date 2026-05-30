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


def load_tools() -> list[dict[str, Any]]:
    try:
        data = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))
        return list(data.get("tools", []))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load {TOOLS_PATH}: {exc}", file=sys.stderr)
        raise SystemExit(1)


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
    args = parser.parse_args(argv)

    tools = load_tools()

    if args.json_out:
        print(json.dumps({"tools": tools}, indent=2, ensure_ascii=False))
        return 0

    render(tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
