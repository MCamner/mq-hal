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
    "path": "~/macos-scripts",
    "branch": "main",
    "status": "clean",
    "changed_files": 0,
    "changed_preview": [],
    "latest_commits": [
        "abc1234 feat: add HAL menu",
        "def5678 docs: update command reference",
    ],
    "latest_tags": ["v0.3.7", "v0.3.6", "v0.3.5"],
    "recommendation": "Repo is clean. Run mqlaunch release-check before release work.",
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


def run(command: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        p = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, timeout=30)
    except FileNotFoundError:
        return 127, "", f"command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(command)}"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def build_status(repo_name: str, repo_path: Path) -> dict[str, Any]:
    _, branch, _ = run(["git", "branch", "--show-current"], repo_path)
    status_code, status_out, status_err = run(["git", "status", "--short"], repo_path)
    _, commits_out, _ = run(["git", "log", "--oneline", "-n", "8"], repo_path)
    _, tags_out, _ = run(["git", "tag", "--sort=-creatordate"], repo_path)

    changed = [x for x in status_out.splitlines() if x.strip()]
    commits = [x for x in commits_out.splitlines() if x.strip()]
    tags = [x for x in tags_out.splitlines() if x.strip()][:8]

    if status_code != 0:
        state = "unknown"
    elif changed:
        state = "dirty"
    else:
        state = "clean"

    if state == "dirty":
        rec = "Review local changes: run git status --short and git diff --stat."
    elif state == "clean":
        rec = "Repo is clean. Run mqlaunch release-check before release work."
    else:
        rec = f"Git status could not be confirmed: {status_err}"

    return {
        "repo": repo_name,
        "path": str(repo_path),
        "branch": branch or "unknown",
        "status": state,
        "changed_files": len(changed),
        "changed_preview": changed[:12],
        "latest_commits": commits,
        "latest_tags": tags,
        "recommendation": rec,
    }


def render(data: dict[str, Any]) -> None:
    print("HAL Repo Status")
    print("===============")
    print()
    print(f"Repo:      {data.get('repo', '-')}")
    print(f"Path:      {data.get('path', '-')}")
    print(f"Branch:    {data.get('branch', '-')}")
    print(f"Status:    {data.get('status', '-')}")
    print(f"Changed:   {data.get('changed_files', 0)} file(s)")
    print()

    changed = data.get("changed_preview", [])
    if isinstance(changed, list) and changed:
        print("Changed preview")
        print("---------------")
        for item in changed:
            print(f"- {item}")
        print()

    commits = data.get("latest_commits", [])
    if isinstance(commits, list) and commits:
        print("Latest commits")
        print("--------------")
        for item in commits:
            print(f"- {item}")
        print()

    tags = data.get("latest_tags", [])
    if isinstance(tags, list) and tags:
        print("Latest tags")
        print("-----------")
        for item in tags:
            print(f"- {item}")
        print()

    print("Recommendation")
    print("--------------")
    print(data.get("recommendation", "-"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal repo-status")
    parser.add_argument("--repo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    if args.sample:
        data: dict[str, Any] = SAMPLE
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data = build_status(repo_name, repo_path)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
