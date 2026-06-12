#!/usr/bin/env python3
"""Read-only release control center for mq-hal."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MQ_AGENT_RELEASE_COMMAND = ["mq-agent", "stack", "release-check", "--json"]

SAMPLE: dict[str, Any] = {
    "title": "Release Control Center",
    "repos": [
        {
            "repo": "mq-hal",
            "version": "1.4.0",
            "ready": True,
            "score": 95,
            "blockers": [],
            "gates": [
                {"name": "VERSION", "status": "PASS"},
                {"name": "CHANGELOG", "status": "PASS"},
                {"name": "smoke", "status": "PASS"},
            ],
        },
        {
            "repo": "mqobsidian",
            "version": "0.3.0",
            "ready": False,
            "score": 72,
            "blockers": ["CHANGELOG missing"],
            "gates": [
                {"name": "VERSION", "status": "PASS"},
                {"name": "CHANGELOG", "status": "FAIL"},
            ],
        },
    ],
    "overall": {"ready": False, "score": 84, "blockers": 1},
}


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


def read_release_check(timeout: int = 30) -> tuple[dict[str, Any] | None, str, int]:
    mq_agent = find_mq_agent()
    if not mq_agent:
        return None, "mq-agent not found", 127
    command = [mq_agent, "stack", "release-check", "--json"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "mq-agent stack release-check timed out", 124
    except OSError as exc:
        return None, str(exc), 1

    if result.returncode != 0:
        error = (result.stderr or "").strip() or "mq-agent stack release-check failed"
        return None, error, int(result.returncode)

    try:
        parsed = json.loads((result.stdout or "").strip())
    except json.JSONDecodeError as exc:
        return None, f"could not parse mq-agent release JSON: {exc}", 1

    if not isinstance(parsed, dict):
        return None, "mq-agent release JSON was not an object", 1
    return parsed, "", 0


def repos(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("repos", "repositories", "items", "releases"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    stack = data.get("stack")
    if isinstance(stack, dict):
        for key in ("repos", "repositories", "items", "releases"):
            value = stack.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if any(key in data for key in ("repo", "version", "ready", "blockers", "gates")):
        return [data]
    return []


def repo_name(item: dict[str, Any]) -> str:
    for key in ("repo", "name", "repository", "id"):
        value = item.get(key)
        if value:
            return str(value)
    return "unknown"


def version(item: dict[str, Any]) -> str:
    for key in ("version", "target_version", "release_version"):
        value = item.get(key)
        if value:
            return str(value)
    tag = item.get("target_tag")
    return str(tag).lstrip("v") if tag else "-"


def ready(item: dict[str, Any]) -> str:
    value = item.get("ready")
    if isinstance(value, bool):
        return "yes" if value else "no"
    overall = str(item.get("overall") or item.get("status") or "").lower()
    if overall in {"ready", "pass", "ok"}:
        return "yes"
    if overall in {"blocked", "fail", "not_ready", "needs_review"}:
        return "no"
    return str(item.get("ready") or item.get("status") or "unknown")


def score(item: dict[str, Any]) -> str:
    for key in ("score", "release_score"):
        value = item.get(key)
        if value is not None:
            total = item.get("total", 100)
            return f"{value}/{total}"
    return "-"


def gates(item: dict[str, Any]) -> list[dict[str, Any]]:
    value = item.get("gates") or item.get("checks")
    if isinstance(value, list):
        return [gate for gate in value if isinstance(gate, dict)]
    return []


def blockers(item: dict[str, Any]) -> list[str]:
    value = item.get("blockers")
    if isinstance(value, list):
        return [str(blocker) for blocker in value]
    found: list[str] = []
    for gate in gates(item):
        status = str(gate.get("status") or "").lower()
        if status in {"fail", "failed", "block", "blocked"}:
            name = str(gate.get("name") or gate.get("gate") or "gate")
            message = str(gate.get("message") or "").strip()
            found.append(f"{name}: {message}" if message else name)
    return found


def all_blockers(data: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in repos(data):
        for blocker in blockers(item):
            out.append({"repo": repo_name(item), "blocker": blocker})
    return out


def render_summary(data: dict[str, Any]) -> None:
    print("Release Control Center")
    print("======================")
    print()
    print(f"{'Repo':<18} {'Version':<10} {'Ready':<8} {'Score':<8} Blockers")
    print("-" * 62)
    for item in repos(data):
        blocker_count = len(blockers(item))
        print(
            f"{repo_name(item):<18} {version(item):<10} "
            f"{ready(item):<8} {score(item):<8} {blocker_count}"
        )
    print()
    overall = data.get("overall")
    if isinstance(overall, dict):
        score_value = overall.get("score", "-")
        ready_value = overall.get("ready", "unknown")
        blockers_value = overall.get("blockers", len(all_blockers(data)))
        print(f"Overall: ready={ready_value} score={score_value}/100 blockers={blockers_value}")
    else:
        print(f"Overall blockers: {len(all_blockers(data))}")


def render_gates(data: dict[str, Any]) -> None:
    print("Release Gates")
    print("=============")
    print()
    for item in repos(data):
        print(repo_name(item))
        print("-" * len(repo_name(item)))
        repo_gates = gates(item)
        if not repo_gates:
            print("No gates reported.")
        for gate in repo_gates:
            name = gate.get("name") or gate.get("gate") or "-"
            status = str(gate.get("status") or "unknown").upper()
            message = gate.get("message") or ""
            suffix = f" — {message}" if message else ""
            print(f"[{status:<5}] {name}{suffix}")
        print()


def render_blockers(data: dict[str, Any]) -> None:
    print("Release Blockers")
    print("================")
    print()
    found = all_blockers(data)
    if not found:
        print("No blockers reported.")
        return
    for item in found:
        print(f"{item['repo']}: {item['blocker']}")


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal release",
        description="Read-only release control center from mq-agent release JSON.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")

    sub = parser.add_subparsers(dest="command")
    p_gates = sub.add_parser("gates", help="Show release gates")
    p_gates.add_argument("--json", action="store_true")
    p_gates.add_argument("--sample", action="store_true")

    p_blockers = sub.add_parser("blockers", help="Show release blockers")
    p_blockers.add_argument("--json", action="store_true")
    p_blockers.add_argument("--sample", action="store_true")

    args = parser.parse_args(argv)
    sample = bool(getattr(args, "sample", False))

    if sample:
        data = SAMPLE
    else:
        data, error, code = read_release_check()
        if data is None:
            if args.json:
                print_json(
                    {
                        "status": "warn",
                        "source": "mq-agent stack release-check --json",
                        "error": error,
                        "returncode": code,
                    }
                )
            else:
                print("Release Control Center")
                print("======================")
                print()
                print(f"WARN: {error}")
                print()
                print("Expected input: mq-agent stack release-check --json")
            return 1

    if args.json:
        print_json(data)
        return 0

    if args.command == "gates":
        render_gates(data)
    elif args.command == "blockers":
        render_blockers(data)
    else:
        render_summary(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
