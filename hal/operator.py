#!/usr/bin/env python3
"""Operator actions for routing from HAL findings to local tools."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from hal import dashboard as dashboard_control  # noqa: E402
from hal import release as release_control  # noqa: E402

CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE: dict[str, Any] = {
    "actions": [
        {
            "source": "release",
            "repo": "mq-hal",
            "blocker": "CHANGELOG missing",
            "action": "open",
            "target": "CHANGELOG.md",
            "command": ["mq-hal", "open", "CHANGELOG.md", "--repo", "mq-hal"],
        }
    ]
}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"default_repo": "mq-hal", "repos": {"mq-hal": str(BASE_DIR)}}
    if not isinstance(data, dict):
        return {"default_repo": "mq-hal", "repos": {"mq-hal": str(BASE_DIR)}}
    repos = data.get("repos")
    if not isinstance(repos, dict):
        data["repos"] = {"mq-hal": str(BASE_DIR)}
    return data


def repos() -> dict[str, Path]:
    data = load_config()
    out: dict[str, Path] = {}
    for name, raw in data.get("repos", {}).items():
        out[str(name)] = Path(str(raw)).expanduser().resolve()
    return out


def default_repo_name() -> str:
    data = load_config()
    value = data.get("default_repo")
    if isinstance(value, str) and value:
        return value
    names = list(repos())
    return names[0] if names else "mq-hal"


def resolve_repo(repo: str | None) -> tuple[str, Path]:
    known = repos()
    name = repo or default_repo_name()
    if name not in known:
        name = "mq-hal" if "mq-hal" in known else default_repo_name()
    path = known.get(name, BASE_DIR).resolve()
    return name, path


def is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


def resolve_target(repo_path: Path, target: str) -> Path:
    candidate = (repo_path / (target or ".")).expanduser().resolve()
    if not is_within(repo_path.resolve(), candidate):
        raise ValueError("refusing to open a path outside the repo")
    return candidate


def editor_command(path: Path) -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return [*shlex.split(editor), str(path)]
    if shutil.which("code"):
        return ["code", str(path)]
    if shutil.which("open"):
        return ["open", str(path)]
    return ["nano", str(path)]


def blocker_target(blocker: str) -> str:
    lowered = blocker.lower()
    if "changelog" in lowered:
        return "CHANGELOG.md"
    if "readme" in lowered:
        return "README.md"
    if "version" in lowered:
        return "VERSION"
    if "roadmap" in lowered:
        return "ROADMAP.md"
    if "test" in lowered or "smoke" in lowered:
        return "tests/smoke.sh"
    return "."


def action_for_blocker(repo: str, blocker: str) -> dict[str, Any]:
    target = blocker_target(blocker)
    return {
        "source": "release",
        "repo": repo,
        "blocker": blocker,
        "action": "open",
        "target": target,
        "command": ["mq-hal", "open", target, "--repo", repo],
        "fix_command": ["mqlaunch", "fix", blocker],
    }


def release_actions(sample: bool) -> list[dict[str, Any]]:
    if sample:
        return SAMPLE["actions"]
    data, error, _code = release_control.read_release_check(timeout=8)
    if data is None:
        return [{
            "source": "release",
            "repo": default_repo_name(),
            "blocker": error,
            "action": "inspect",
            "target": ".",
            "command": ["mq-hal", "release"],
            "fix_command": ["mqlaunch", "fix", error],
        }]
    return [
        action_for_blocker(item["repo"], item["blocker"])
        for item in release_control.all_blockers(data)
    ]


def alert_actions(sample: bool) -> list[dict[str, Any]]:
    data = dashboard_control.collect_dashboard(sample=sample)
    actions: list[dict[str, Any]] = []
    for alert in data.get("alerts", []):
        if not isinstance(alert, str):
            continue
        target = blocker_target(alert)
        actions.append({
            "source": "alert",
            "repo": default_repo_name(),
            "blocker": alert,
            "action": "open" if target != "." else "inspect",
            "target": target,
            "command": ["mq-hal", "open", target],
            "fix_command": ["mqlaunch", "fix", alert],
        })
    return actions


def collect_actions(sample: bool = False) -> dict[str, Any]:
    actions = release_actions(sample)
    if not actions:
        actions = alert_actions(sample)
    return {
        "title": "Operator Actions",
        "actions": actions,
        "count": len(actions),
    }


def render_next(data: dict[str, Any]) -> None:
    print("Operator Next")
    print("=============")
    print()
    actions = data.get("actions", [])
    if not actions:
        print("No operator actions found.")
        return
    action = actions[0]
    print("BLOCKER:")
    print(action.get("blocker", "-"))
    print()
    print("Action:")
    target = action.get("target") or "."
    if action.get("action") == "open":
        print(f"open {target}")
    else:
        print("inspect status")
    print()
    print("Route:")
    print(" ".join(shlex.quote(str(part)) for part in action.get("command", [])))


def run_open(target: str, repo: str | None, confirm: bool, json_out: bool) -> int:
    repo_name, repo_path = resolve_repo(repo)
    try:
        path = resolve_target(repo_path, target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    command = editor_command(path)
    payload = {
        "repo": repo_name,
        "repo_path": str(repo_path),
        "target": str(path),
        "command": command,
        "confirmed": confirm,
    }
    if json_out:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("Operator Open")
    print("=============")
    print()
    print(f"repo:    {repo_name}")
    print(f"target:  {path}")
    print(f"command: {' '.join(shlex.quote(part) for part in command)}")
    if not confirm:
        print()
        print("Preview only. Re-run with --confirm to open.")
        return 0
    result = subprocess.run(command, cwd=str(repo_path), check=False)
    return int(result.returncode)


def run_fix(blocker: str | None, sample: bool, confirm: bool, json_out: bool) -> int:
    action = collect_actions(sample=sample).get("actions", [])
    selected = action[0] if action else {}
    text = blocker or str(selected.get("blocker") or "operator action")
    command = ["mqlaunch", "fix", text]
    payload = {"blocker": text, "command": command, "confirmed": confirm}
    if json_out:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("Operator Fix")
    print("============")
    print()
    print("BLOCKER:")
    print(text)
    print()
    print("Route:")
    print(" ".join(shlex.quote(part) for part in command))
    if not confirm:
        print()
        print("Preview only. Re-run with --confirm to route through mqlaunch fix.")
        return 0
    if not shutil.which("mqlaunch"):
        print("ERROR: mqlaunch not found", file=sys.stderr)
        return 127
    result = subprocess.run(command, check=False)
    return int(result.returncode)


def main(argv: list[str], command_name: str = "next") -> int:
    parser = argparse.ArgumentParser(prog=f"mq-hal {command_name}")
    parser.add_argument("--command", choices=["next", "fix", "open"], default=command_name)
    parser.add_argument("target", nargs="?")
    parser.add_argument("--repo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    command_name = args.command

    if command_name == "open":
        target = args.target
        if not target:
            actions = collect_actions(sample=args.sample).get("actions", [])
            target = str(actions[0].get("target", ".")) if actions else "."
            if not args.repo and actions:
                args.repo = str(actions[0].get("repo") or "")
        return run_open(target, args.repo, args.confirm, args.json)

    if command_name == "fix":
        return run_fix(args.target, args.sample, args.confirm, args.json)

    data = collect_actions(sample=args.sample)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_next(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
