#!/usr/bin/env python3
"""mq-hal agent-brief: mq-agent availability and memory summary."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]

SAMPLE: dict[str, Any] = {
    "available": True,
    "path": "~/.local/bin/mq-agent",
    "memory": {
        "available": True,
        "status": "missing-vector-store",
        "enabled": False,
        "repo_signal_available": True,
    },
}


def find_mq_agent() -> str | None:
    env = os.environ.get("MQ_AGENT_BIN")
    if env and Path(env).expanduser().exists():
        return str(Path(env).expanduser())
    w = shutil.which("mq-agent")
    if w:
        return w
    for candidate in (
        Path.home() / ".local" / "bin" / "mq-agent",
        Path.home() / "mq-agent" / ".venv" / "bin" / "mq-agent",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def run(cmd: list[str], timeout: int = 20) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.stdout or "").strip(), int(result.returncode)
    except FileNotFoundError:
        return "", 127
    except subprocess.TimeoutExpired:
        return "", 124
    except OSError:
        return "", 1


def collect_memory(bin_path: str) -> dict[str, Any]:
    out, code = run([bin_path, "memory", "status", "--json"])
    if not out or code != 0:
        return {"available": True, "status": "error", "enabled": False,
                "repo_signal_available": None}
    try:
        data = json.loads(out)
        return {
            "available": True,
            "status": str(data.get("status", "unknown")),
            "enabled": bool(data.get("enabled", False)),
            "repo_signal_available": bool(
                data.get("repo_signal_available", False)
            ),
        }
    except json.JSONDecodeError:
        return {"available": True, "status": "parse-error", "enabled": False,
                "repo_signal_available": None}


def collect() -> dict[str, Any]:
    bin_path = find_mq_agent()

    if bin_path is None:
        return {
            "available": False,
            "path": None,
            "memory": {
                "available": False,
                "status": "mq-agent-unavailable",
                "enabled": False,
                "repo_signal_available": None,
            },
        }

    return {
        "available": True,
        "path": bin_path,
        "memory": collect_memory(bin_path),
    }


def render(data: dict[str, Any]) -> None:
    print("HAL Agent Brief")
    print("===============")
    print()

    if not data["available"]:
        print("mq-agent:  not found")
        print()
        print(
            "Install mq-agent and set MQ_AGENT_BIN if needed, "
            "or add it to PATH."
        )
        return

    print(f"mq-agent:  {data['path']}")
    print()

    mem = data["memory"]
    enabled = "yes" if mem["enabled"] else "no"
    rs = mem.get("repo_signal_available")
    rs_str = (
        "available" if rs
        else ("unavailable" if rs is False else "unknown")
    )

    print("Semantic memory")
    print("---------------")
    print(f"status:      {mem['status']}")
    print(f"enabled:     {enabled}")
    print(f"repo-signal: {rs_str}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal agent-brief",
        description="Show mq-agent availability and memory summary.",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Print sample output without calling mq-agent",
    )
    args = parser.parse_args(argv)

    data = SAMPLE if args.sample else collect()

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
