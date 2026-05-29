#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"
DOCTOR_SUMMARY_SCRIPT = BASE_DIR / "scripts" / "doctor_summary.py"

SAMPLE: dict[str, Any] = {
    "repo": "macos-scripts",
    "path": "~/macos-scripts",
    "timestamp": "2026-05-17T13:40:00+02:00",
    "version": "0.3.9",
    "target_tag": "v0.3.9",
    "overall": "ready",
    "branch": "main",
    "changed_files": 0,
    "changed_preview": [],
    "latest_tags": ["v0.3.9", "v0.3.8", "v0.3.7"],
    "checks": [
        {"name": "VERSION", "status": "ok", "message": "VERSION exists: 0.3.9"},
        {"name": "CHANGELOG", "status": "ok", "message": "CHANGELOG contains 0.3.9"},
        {"name": "README badge", "status": "ok", "message": "README appears to reference 0.3.9"},
        {"name": "Git tree", "status": "ok", "message": "Working tree is clean"},
        {"name": "CI", "status": "ok", "message": "Recent GitHub Actions look green"},
        {"name": "Latest release", "status": "ok", "message": "Latest release matches target tag: v0.3.9"},
        {"name": "Doctor", "status": "ok", "message": "Doctor status: healthy"},
        {"name": "Release check", "status": "ok", "message": "release-check passed"},
    ],
    "recommendation": "Repo appears ready. If this is intended, tag and publish v0.3.9 manually.",
    "memory_brief": "memory: missing-vector-store  mq-agent=ok  repo-signal=ok",
    "safe_commands": [
        "git status --short",
        "git diff --stat",
        "gh run list --limit 5",
        "mqlaunch release-check",
        "gh release view",
        "git tag --list v0.3.9",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "default_repo": "macos-scripts",
            "repos": {
                "macos-scripts": "~/macos-scripts",
                "mq-hal": "~/mq-hal",
            },
        }
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid config JSON: {exc}")
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


def run(command: list[str], cwd: Path, timeout: int = 60) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            command, cwd=str(cwd), text=True, capture_output=True,
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "", f"command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(command)}"
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def collect_memory_brief() -> str:
    halbin = BASE_DIR / "bin" / "mq-hal"
    code, out, _ = run([str(halbin), "memory-status", "--brief"],
                       cwd=BASE_DIR, timeout=15)
    return out if code == 0 else ""


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def check_version(repo_path: Path) -> tuple[str, dict[str, str]]:
    version = read_text(repo_path / "VERSION").strip()
    if not version:
        return "", {"name": "VERSION", "status": "warn", "message": "VERSION file missing or empty"}
    return version, {"name": "VERSION", "status": "ok", "message": f"VERSION exists: {version}"}


def check_changelog(repo_path: Path, version: str) -> dict[str, str]:
    changelog = read_text(repo_path / "CHANGELOG.md")
    if not changelog:
        return {"name": "CHANGELOG", "status": "warn", "message": "CHANGELOG.md missing or empty"}
    if version and (f"## [{version}]" in changelog or f"## {version}" in changelog):
        return {"name": "CHANGELOG", "status": "ok", "message": f"CHANGELOG contains {version}"}
    return {
        "name": "CHANGELOG",
        "status": "warn",
        "message": f"CHANGELOG does not clearly contain {version or 'current VERSION'}",
    }


def check_readme_badge(repo_path: Path, version: str) -> dict[str, str]:
    readme = read_text(repo_path / "README.md")
    if not readme:
        return {"name": "README badge", "status": "warn", "message": "README.md missing or empty"}
    if version and version in readme:
        return {"name": "README badge", "status": "ok", "message": f"README appears to reference {version}"}
    return {
        "name": "README badge",
        "status": "warn",
        "message": f"README does not appear to reference {version or 'current VERSION'}",
    }


def check_git(repo_path: Path) -> dict[str, Any]:
    code, out, _ = run(["git", "status", "--short"], repo_path)
    branch_code, branch, _ = run(["git", "branch", "--show-current"], repo_path)
    tag_code, tags_out, _ = run(["git", "tag", "--sort=-creatordate"], repo_path)

    changed = [line for line in out.splitlines() if line.strip()]
    latest_tags = [line for line in tags_out.splitlines() if line.strip()][:5]

    if code != 0:
        return {
            "name": "Git tree", "status": "warn",
            "message": "Could not read git status",
            "branch": branch if branch_code == 0 else "unknown",
            "changed_files": 0, "changed_preview": [], "latest_tags": [],
        }

    return {
        "name": "Git tree",
        "status": "warn" if changed else "ok",
        "message": f"Working tree has {len(changed)} changed file(s)" if changed else "Working tree is clean",
        "branch": branch if branch_code == 0 and branch else "unknown",
        "changed_files": len(changed),
        "changed_preview": changed[:10],
        "latest_tags": latest_tags if tag_code == 0 else [],
    }


def check_ci(repo_path: Path, skip_gh: bool) -> dict[str, Any]:
    if skip_gh:
        return {"name": "CI", "status": "skip", "message": "GitHub CLI checks skipped", "runs": []}

    code, out, err = run(
        ["gh", "run", "list", "--limit", "5", "--json",
         "status,conclusion,workflowName,displayTitle,createdAt"],
        repo_path,
    )

    if code != 0:
        return {"name": "CI", "status": "warn", "message": err or "Could not read GitHub Actions", "runs": []}

    try:
        raw = json.loads(out)
    except json.JSONDecodeError:
        return {"name": "CI", "status": "warn", "message": "Could not parse gh run list JSON", "runs": []}

    runs: list[str] = []
    has_failure = False
    has_running = False

    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        workflow = str(item.get("workflowName") or "workflow")
        status = str(item.get("status") or "unknown")
        conclusion = str(item.get("conclusion") or "unknown")
        runs.append(f"{workflow}: {status} / {conclusion}")
        if conclusion in {"failure", "cancelled", "timed_out"}:
            has_failure = True
        if status in {"in_progress", "queued", "waiting"}:
            has_running = True

    if has_failure:
        return {"name": "CI", "status": "fail", "message": "Recent GitHub Actions include failures", "runs": runs}
    if has_running:
        return {"name": "CI", "status": "warn", "message": "GitHub Actions are still running", "runs": runs}
    return {"name": "CI", "status": "ok", "message": "Recent GitHub Actions look green", "runs": runs}


def check_latest_release(repo_path: Path, target_tag: str, skip_gh: bool) -> dict[str, str]:
    if skip_gh:
        return {"name": "Latest release", "status": "skip", "message": "GitHub CLI release check skipped"}

    code, out, err = run(
        ["gh", "release", "view", "--json", "tagName,name,publishedAt,isLatest"],
        repo_path,
    )

    if code != 0:
        return {"name": "Latest release", "status": "warn", "message": err or "Could not read latest GitHub release"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"name": "Latest release", "status": "warn", "message": "Could not parse gh release JSON"}

    tag = str(data.get("tagName") or "unknown")
    name = str(data.get("name") or "")

    if target_tag and tag == target_tag:
        return {"name": "Latest release", "status": "ok", "message": f"Latest release matches target tag: {tag}"}
    return {"name": "Latest release", "status": "warn", "message": f"Latest release is {tag} {name}".strip()}


def check_doctor(repo_name: str, repo_path: Path, skip_doctor: bool) -> dict[str, str]:
    if skip_doctor:
        return {"name": "Doctor", "status": "skip", "message": "Doctor summary skipped"}

    code, out, err = run(
        [sys.executable, str(DOCTOR_SUMMARY_SCRIPT),
         "--repo", repo_name, "--json", "--no-ai", "--no-memory"],
        repo_path,
        timeout=120,
    )

    if code != 0:
        return {"name": "Doctor", "status": "warn", "message": err or "Doctor summary failed"}

    try:
        envelope = json.loads(out)
    except json.JSONDecodeError:
        return {"name": "Doctor", "status": "warn", "message": "Could not parse doctor summary JSON"}

    summary = envelope.get("summary", {})
    if not isinstance(summary, dict):
        return {"name": "Doctor", "status": "warn", "message": "Doctor summary missing summary object"}

    doctor_status = str(summary.get("status") or "unknown")
    lower = doctor_status.lower()
    status = "warn" if any(t in lower for t in ["fail", "attention", "warning", "warn"]) else "ok"
    return {"name": "Doctor", "status": status, "message": f"Doctor status: {doctor_status}"}


def check_release_check(repo_path: Path, skip_release_check: bool) -> dict[str, str]:
    if skip_release_check:
        return {"name": "Release check", "status": "skip", "message": "release-check skipped"}

    candidates = [
        ["mqlaunch", "release-check"],
        [str(repo_path / "terminal" / "release" / "mq-release-check.sh")],
    ]

    for command in candidates:
        if command[0].endswith(".sh") and not Path(command[0]).exists():
            continue
        code, out, err = run(command, repo_path, timeout=180)
        combined = "\n".join(x for x in [out, err] if x).strip()
        if code == 0:
            return {"name": "Release check", "status": "ok", "message": "release-check passed"}
        if code in {1, 2}:
            return {"name": "Release check", "status": "warn",
                    "message": combined[:600] or f"release-check exited {code}"}

    return {"name": "Release check", "status": "skip",
            "message": "No release-check command available for this repo"}


def overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = [str(c.get("status") or "") for c in checks]
    if "fail" in statuses:
        return "blocked"
    if "warn" in statuses:
        return "needs_review"
    return "ready"


def build_recommendation(overall: str, checks: list[dict[str, Any]], target_tag: str) -> str:
    if overall == "blocked":
        return "Release is blocked. Fix failing checks before tagging or publishing."
    warn_names = [str(c.get("name")) for c in checks if c.get("status") == "warn"]
    if warn_names:
        return "Review warnings before release: " + ", ".join(warn_names)
    return f"Repo appears ready. If this is intended, tag and publish {target_tag} manually."


def build_safe_commands(target_tag: str) -> list[str]:
    commands = [
        "git status --short",
        "git diff --stat",
        "gh run list --limit 5",
        "mqlaunch release-check",
        "gh release view",
    ]
    if target_tag:
        commands.append(f"git tag --list {target_tag}")
    return commands


def build_release_brief(
    repo_name: str,
    repo_path: Path,
    skip_gh: bool,
    skip_doctor: bool,
    skip_release_check: bool,
) -> dict[str, Any]:
    version, version_check = check_version(repo_path)
    target_tag = f"v{version}" if version else ""

    checks: list[dict[str, Any]] = [
        version_check,
        check_changelog(repo_path, version),
        check_readme_badge(repo_path, version),
    ]

    git_check = check_git(repo_path)
    checks.append(git_check)
    checks.append(check_ci(repo_path, skip_gh=skip_gh))
    checks.append(check_latest_release(repo_path, target_tag, skip_gh=skip_gh))
    checks.append(check_doctor(repo_name, repo_path, skip_doctor=skip_doctor))
    checks.append(check_release_check(repo_path, skip_release_check=skip_release_check))

    overall = overall_status(checks)

    return {
        "repo": repo_name,
        "path": str(repo_path),
        "timestamp": now_iso(),
        "version": version,
        "target_tag": target_tag,
        "overall": overall,
        "branch": git_check.get("branch", "unknown"),
        "changed_files": git_check.get("changed_files", 0),
        "changed_preview": git_check.get("changed_preview", []),
        "latest_tags": git_check.get("latest_tags", []),
        "checks": checks,
        "recommendation": build_recommendation(overall, checks, target_tag),
        "safe_commands": build_safe_commands(target_tag),
    }


def render(data: dict[str, Any]) -> None:
    print("HAL Release Brief")
    print("=================")
    print()
    print(f"Repo:       {data.get('repo', '-')}")
    print(f"Path:       {data.get('path', '-')}")
    print(f"Version:    {data.get('version', '-')}")
    print(f"Target tag: {data.get('target_tag', '-')}")
    print(f"Branch:     {data.get('branch', '-')}")
    print(f"Overall:    {data.get('overall', '-')}")
    print()

    print("Checks")
    print("------")
    for check in data.get("checks", []):
        if not isinstance(check, dict):
            continue
        print(f"- [{str(check.get('status', '?')).upper():4}] {check.get('name', '-')}: {check.get('message', '-')}")
    print()

    changed = data.get("changed_preview", [])
    if isinstance(changed, list) and changed:
        print("Changed preview")
        print("---------------")
        for item in changed:
            print(f"- {item}")
        print()

    tags = data.get("latest_tags", [])
    if isinstance(tags, list) and tags:
        print("Latest tags")
        print("-----------")
        for item in tags[:5]:
            print(f"- {item}")
        print()

    memory_brief = data.get("memory_brief", "")
    if memory_brief:
        print("Memory")
        print("------")
        print(memory_brief)
        print()

    print("Recommendation")
    print("--------------")
    print(data.get("recommendation", "-"))
    print()

    commands = data.get("safe_commands", [])
    if isinstance(commands, list) and commands:
        print("Safe commands")
        print("-------------")
        for cmd in commands:
            print(cmd)
        print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal release-brief",
        description="Read-only release readiness brief.",
    )
    parser.add_argument("--repo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--skip-gh", action="store_true")
    parser.add_argument("--skip-doctor", action="store_true")
    parser.add_argument("--skip-release-check", action="store_true")
    parser.add_argument("--no-memory", action="store_true")
    args = parser.parse_args(argv)

    if args.sample:
        data: dict[str, Any] = SAMPLE
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data = build_release_brief(
            repo_name,
            repo_path,
            skip_gh=args.skip_gh,
            skip_doctor=args.skip_doctor,
            skip_release_check=args.skip_release_check,
        )
        data["memory_brief"] = collect_memory_brief()

    if not args.sample and not args.no_memory and os.environ.get("MQ_HAL_DISABLE_MEMORY") != "1":
        from session_memory import append_event
        append_event(
            "release_brief",
            payload={
                "repo": str(data.get("repo") or ""),
                "overall": str(data.get("overall") or ""),
                "version": str(data.get("version") or ""),
            },
            repo=str(data.get("repo") or ""),
            source="deterministic",
        )

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
