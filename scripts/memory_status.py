#!/usr/bin/env python3
"""mq-hal memory-status: show mq-agent semantic memory state."""
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
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE: dict[str, Any] = {
    "available": True,
    "status": "missing-vector-store",
    "enabled": False,
    "vector_store_id": None,
    "repo_signal_available": True,
    "repo_path": "~/macos-scripts",
    "mq_agent_path": "~/.local/bin/mq-agent",
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


def collect(repo_path: str = ".") -> dict[str, Any]:
    bin_path = find_mq_agent()

    if bin_path is None:
        return {
            "available": False,
            "status": "mq-agent-unavailable",
            "enabled": False,
            "vector_store_id": None,
            "repo_signal_available": None,
            "repo_path": repo_path,
            "mq_agent_path": None,
        }

    out, code = run([bin_path, "memory", "status", "--json", repo_path])

    if not out or code != 0:
        return {
            "available": True,
            "status": "error",
            "enabled": False,
            "vector_store_id": None,
            "repo_signal_available": None,
            "repo_path": repo_path,
            "mq_agent_path": bin_path,
        }

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {
            "available": True,
            "status": "parse-error",
            "enabled": False,
            "vector_store_id": None,
            "repo_signal_available": None,
            "repo_path": repo_path,
            "mq_agent_path": bin_path,
        }

    return {
        "available": True,
        "status": str(data.get("status", "unknown")),
        "enabled": bool(data.get("enabled", False)),
        "vector_store_id": data.get("vector_store_id"),
        "repo_signal_available": bool(
            data.get("repo_signal_available", False)
        ),
        "repo_path": str(data.get("repo_path", repo_path)),
        "mq_agent_path": bin_path,
    }


def brief_line(data: dict[str, Any]) -> str:
    status = data["status"]
    agent = "mq-agent=ok" if data["available"] else "mq-agent=missing"
    rs = data.get("repo_signal_available")
    if rs is None:
        rs_str = "repo-signal=unknown"
    else:
        rs_str = "repo-signal=ok" if rs else "repo-signal=missing"
    return f"memory: {status}  {agent}  {rs_str}"


def render(data: dict[str, Any]) -> None:
    print("Memory Status")
    print("=============")
    print()

    if not data["available"]:
        print("mq-agent:    not found")
        print()
        print(
            "Install mq-agent or set MQ_AGENT_BIN to enable "
            "semantic memory status."
        )
        return

    enabled = "yes" if data["enabled"] else "no"
    vs = data["vector_store_id"] or "(not set — export OPENAI_VECTOR_STORE_ID)"
    rs = data.get("repo_signal_available")
    rs_str = "available" if rs else ("unavailable" if rs is False else "unknown")

    print(f"mq-agent:     {data['mq_agent_path']}")
    print(f"status:       {data['status']}")
    print(f"enabled:      {enabled}")
    print(f"vector store: {vs}")
    print(f"repo-signal:  {rs_str}")
    print(f"repo:         {data['repo_path']}")


def resolve_repo_path(repo_name: str | None) -> str:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        repos = config.get("repos", {})
        name = repo_name or str(config.get("default_repo") or "")
        if name in repos:
            return str(Path(str(repos[name])).expanduser().resolve())
    except (OSError, json.JSONDecodeError):
        pass
    return "."


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal memory-status",
        description="Show mq-agent semantic memory state.",
    )
    parser.add_argument("--repo", help="Repo name from config")
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--brief", action="store_true",
        help="One-line summary for embedding in other commands",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Print sample output without calling mq-agent",
    )
    args = parser.parse_args(argv)

    repo_path = resolve_repo_path(args.repo)
    data = SAMPLE if args.sample else collect(repo_path)

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if args.brief:
        print(brief_line(data))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
