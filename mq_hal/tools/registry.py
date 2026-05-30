"""Validation for the mq-hal tool registry."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "name": str,
    "description": str,
    "risk_level": str,
    "requires_confirm": bool,
    "uses_ai": bool,
    "writes_memory": bool,
}


def load_registry(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tools = data.get("tools")
    if not isinstance(tools, list):
        raise ValueError("config/tools.json must contain a tools list")
    return tools


def validate_registry(tools: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, tool in enumerate(tools, start=1):
        if not isinstance(tool, dict):
            errors.append(f"tool #{index} must be an object")
            continue
        name = tool.get("name")
        if isinstance(name, str) and name:
            if name in seen:
                errors.append(f"duplicate tool name: {name}")
            seen.add(name)
        for field, expected_type in REQUIRED_FIELDS.items():
            value = tool.get(field)
            if not isinstance(value, expected_type):
                errors.append(
                    f"tool #{index} {name or '<unnamed>'}: "
                    f"{field} must be {expected_type.__name__}"
                )
        if "mqlaunch_alias" not in tool:
            errors.append(f"tool #{index} {name or '<unnamed>'}: mqlaunch_alias missing")
        elif tool["mqlaunch_alias"] is not None and not isinstance(tool["mqlaunch_alias"], str):
            errors.append(f"tool #{index} {name or '<unnamed>'}: mqlaunch_alias must be string or null")
    return errors
