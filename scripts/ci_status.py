#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE = {
    "repo": "macos-scripts",
    "status": "green",
    "runs": [
        {"workflow": "Tests", "status": "completed", "conclusion": "success", "created_at": "", "title": ""},
        {"workflow": "Validate", "status": "completed", "conclusion": "success", "created_at": "", "title": ""},
    ],
    "recommendation": "CI is green.",
}


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"default_repo": "macos-scripts", "repos": {"macos-scripts": "~/macos-scripts"}}
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("repos"), dict):
        die("config/repos.json must contain a repos object")
    return data


def resolve_repo(repo: str | None) -> tuple[str, Path]:
    config = load_config()
    repos = config["repos"]
    repo_name = repo or config.get("default_repo") or next(iter(repos))
    if repo_name not in repos:
        die(f"unknown repo '{repo_name}'. Known repos: {', '.join(sorted(repos))}", 2)
    repo_path = Path(str(repos[repo_name])).expanduser().resolve()
    if not repo_path.exists():
        die(f"repo '{repo_name}' does not exist at {repo_path}", 2)
    return str(repo_name), repo_path


def run_cmd(command: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        p = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, timeout=40)
    except FileNotFoundError:
        return 127, "", f"command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(command)}"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def build_ci(repo_name: str, repo_path: Path, limit: int) -> dict[str, Any]:
    command = [
        "gh", "run", "list",
        "--limit", str(limit),
        "--json", "status,conclusion,workflowName,displayTitle,createdAt",
    ]

    code, out, err = run_cmd(command, repo_path)

    if code != 0:
        return {
            "repo": repo_name,
            "status": "unknown",
            "runs": [],
            "recommendation": f"Could not read GitHub Actions: {err or 'gh failed'}",
        }

    try:
        raw = json.loads(out)
    except json.JSONDecodeError:
        return {
            "repo": repo_name,
            "status": "unknown",
            "runs": [],
            "recommendation": "Could not parse gh run list JSON.",
        }

    runs: list[dict[str, Any]] = []
    has_failure = False
    has_running = False

    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        workflow = str(item.get("workflowName") or "workflow")
        status = str(item.get("status") or "unknown")
        conclusion = str(item.get("conclusion") or "unknown")
        runs.append({
            "workflow": workflow,
            "status": status,
            "conclusion": conclusion,
            "created_at": str(item.get("createdAt") or ""),
            "title": str(item.get("displayTitle") or ""),
        })
        if conclusion in {"failure", "cancelled", "timed_out"}:
            has_failure = True
        if status in {"in_progress", "queued", "waiting"}:
            has_running = True

    if has_failure:
        overall = "red"
        rec = "CI has failures. Run gh run view --log-failed."
    elif has_running:
        overall = "running"
        rec = "CI is still running. Run gh run watch."
    else:
        overall = "green"
        rec = "CI is green."

    return {
        "repo": repo_name,
        "status": overall,
        "runs": runs,
        "recommendation": rec,
    }


def render(data: dict[str, Any]) -> None:
    print("HAL CI Status")
    print("=============")
    print()
    print(f"Repo:   {data.get('repo', '-')}")
    print(f"Status: {data.get('status', '-')}")
    print()

    runs = data.get("runs", [])
    if isinstance(runs, list) and runs:
        print("Recent runs")
        print("-----------")
        for item in runs:
            if not isinstance(item, dict):
                continue
            print(f"- {item.get('workflow', '-')}: {item.get('status', '-')} / {item.get('conclusion', '-')}")
        print()

    print("Recommendation")
    print("--------------")
    print(data.get("recommendation", "-"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal ci")
    parser.add_argument("--repo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    if args.sample:
        data: dict[str, Any] = SAMPLE
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data = build_ci(repo_name, repo_path, limit=args.limit)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
