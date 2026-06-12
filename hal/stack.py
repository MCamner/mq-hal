#!/usr/bin/env python3
"""Operator stack view backed by mq-agent cockpit JSON."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COCKPIT_COMMAND = ["mq-agent", "stack", "cockpit", "--json"]

SAMPLE_COCKPIT: dict[str, Any] = {
    "title": "MQ Stack",
    "components": [
        {"name": "mq-agent", "status": "PASS", "score": 100},
        {"name": "mq-mcp", "status": "PASS", "score": 100},
        {"name": "repo-signal", "status": "PASS", "score": 100},
        {"name": "mqobsidian", "status": "WARN", "score": 70},
        {"name": "brain", "status": "PASS", "score": 90},
    ],
    "overall": {"score": 92, "total": 100, "status": "PASS"},
}


@dataclass(frozen=True)
class CockpitResult:
    data: dict[str, Any] | None
    raw: str
    command: list[str]
    returncode: int
    error: str

    @property
    def ok(self) -> bool:
        return self.data is not None and self.returncode == 0


def find_mq_agent() -> str | None:
    env = os.environ.get("MQ_AGENT_BIN")
    if env:
        path = Path(env).expanduser()
        if path.exists():
            return str(path)

    found = shutil.which("mq-agent")
    if found:
        return found

    for candidate in (
        Path.home() / ".local" / "bin" / "mq-agent",
        Path.home() / "mq-agent" / ".venv" / "bin" / "mq-agent",
    ):
        if candidate.exists():
            return str(candidate)

    return None


def read_cockpit(timeout: int = 20) -> CockpitResult:
    mq_agent = find_mq_agent()
    if not mq_agent:
        return CockpitResult(
            data=None,
            raw="",
            command=COCKPIT_COMMAND,
            returncode=127,
            error="mq-agent not found",
        )

    command = [mq_agent, "stack", "cockpit", "--json"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CockpitResult(
            data=None,
            raw="",
            command=command,
            returncode=124,
            error="mq-agent stack cockpit timed out",
        )
    except OSError as exc:
        return CockpitResult(
            data=None,
            raw="",
            command=command,
            returncode=1,
            error=str(exc),
        )

    raw = (result.stdout or "").strip()
    if result.returncode != 0:
        return CockpitResult(
            data=None,
            raw=raw,
            command=command,
            returncode=int(result.returncode),
            error=(result.stderr or "").strip() or "mq-agent stack cockpit failed",
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return CockpitResult(
            data=None,
            raw=raw,
            command=command,
            returncode=1,
            error=f"could not parse mq-agent cockpit JSON: {exc}",
        )

    if not isinstance(parsed, dict):
        return CockpitResult(
            data=None,
            raw=raw,
            command=command,
            returncode=1,
            error="mq-agent cockpit JSON was not an object",
        )

    return CockpitResult(
        data=parsed,
        raw=raw,
        command=command,
        returncode=0,
        error="",
    )


def _items(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("components", "stack", "services", "checks", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    nested = data.get("stack")
    if isinstance(nested, dict):
        for key in ("components", "services", "checks", "items"):
            value = nested.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _name(item: dict[str, Any]) -> str:
    for key in ("name", "id", "component", "service", "tool"):
        value = item.get(key)
        if value:
            return str(value)
    return "unknown"


def _status(item: dict[str, Any]) -> str:
    for key in ("status", "state", "health", "result"):
        value = item.get(key)
        if value:
            return str(value).upper()

    ok = item.get("ok")
    if isinstance(ok, bool):
        return "PASS" if ok else "FAIL"

    return "UNKNOWN"


def _overall(data: dict[str, Any]) -> str:
    overall = data.get("overall")
    if isinstance(overall, dict):
        score = overall.get("score")
        total = overall.get("total", 100)
        if score is not None:
            return f"{score}/{total}"
        status = overall.get("status")
        if status:
            return str(status)

    for score_key in ("score", "overall_score"):
        score = data.get(score_key)
        if score is not None:
            total = data.get("total", 100)
            return f"{score}/{total}"

    return str(data.get("status") or "unknown")


def render(data: dict[str, Any]) -> None:
    print(str(data.get("title") or "MQ Stack"))
    print()

    items = _items(data)
    if items:
        width = max(len(_name(item)) for item in items)
        for item in items:
            print(f"{_name(item):<{width}}  {_status(item)}")
    else:
        print("No stack items found in mq-agent cockpit JSON.")

    print()
    print("Overall:")
    print(_overall(data))


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))

