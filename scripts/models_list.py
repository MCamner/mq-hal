#!/usr/bin/env python3
"""mq-hal models: show available model profiles from config/models.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_PATH = BASE_DIR / "config" / "models.json"


def load_models() -> dict[str, Any]:
    try:
        return json.loads(MODELS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load {MODELS_PATH}: {exc}", file=sys.stderr)
        raise SystemExit(1)


def render(data: dict[str, Any]) -> None:
    profiles = data.get("profiles", {})
    default = data.get("default", "router")

    print("HAL Model Profiles")
    print("==================")
    print()
    print(f"{'PROFILE':<10}  {'MODEL':<28}  {'EFFORT':<8}  USE FOR")
    print(f"{'-' * 10}  {'-' * 28}  {'-' * 8}  {'-' * 30}")
    for name, prof in profiles.items():
        marker = "* " if name == default else "  "
        model = str(prof.get("model", "-"))
        effort = str(prof.get("reasoning_effort", "-"))
        use_for = ", ".join(prof.get("use_for", []))
        print(f"{marker}{name:<8}  {model:<28}  {effort:<8}  {use_for}")
    print()
    print(f"* = default profile  ({len(profiles)} profiles total)")
    print()
    print(
        "To use a specific profile:\n"
        "  mq-hal --model <profile> \"prompt\"\n"
        "  (CLI flag not yet implemented — coming in v0.14.0)"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal models",
        description="Show available model profiles.",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    args = parser.parse_args(argv)

    data = load_models()

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
