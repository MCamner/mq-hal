#!/usr/bin/env python3
"""mq-hal brief — quick status snapshot of a repo."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from session_memory import filter_events, read_events  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE: dict[str, Any] = {
    "repo": "macos-scripts",
    "version": "0.3.9",
    "git": {
        "branch": "main",
        "dirty": False,
        "changed_files": [],
        "recent_commits": ["abc1234 feat: add HAL Release Brief bridge"],
        "latest_tag": "v0.3.9",
    },
    "doctor": {"health": "Healthy", "ok": 12, "warn": 0, "fail": 0},
    "ci": {
        "available": True,
        "runs": [
            {"name": "Tests", "conclusion": "success"},
        ],
    },
    "release": {"available": True, "tag": "v0.3.9", "name": "Release 0.3.9", "published_at": "2026-05-17"},
    "last_note": "Ready for v0.3.9 release.",
    "last_doctor_status": "Healthy",
    "memory_brief": "memory: missing-vector-store  mq-agent=ok  repo-signal=ok",
}


# ---------------------------------------------------------------------------
# Config helpers (same pattern as doctor_summary.py)
# ---------------------------------------------------------------------------

def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"default_repo": "macos-scripts", "repos": {"macos-scripts": "~/macos-scripts"}}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"default_repo": "macos-scripts", "repos": {}}


def resolve_repo(repo_name: str | None) -> tuple[str, Path]:
    config = load_config()
    repos = config.get("repos", {})
    name = repo_name or str(config.get("default_repo") or "macos-scripts")
    if name not in repos:
        known = ", ".join(sorted(str(k) for k in repos))
        print(f"ERROR: unknown repo '{name}'. Known: {known}", file=sys.stderr)
        raise SystemExit(2)
    path = Path(str(repos[name])).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: repo '{name}' not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    return name, path


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
        )
        return (result.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def collect_git(repo_path: Path) -> dict[str, Any]:
    branch = _run(["git", "branch", "--show-current"], cwd=repo_path) or "unknown"
    porcelain = _run(["git", "status", "--porcelain"], cwd=repo_path)
    dirty = bool(porcelain)
    changed_files = [l.strip() for l in porcelain.splitlines() if l.strip()][:8]
    recent = _run(["git", "log", "--oneline", "-5"], cwd=repo_path)
    recent_commits = [l.strip() for l in recent.splitlines() if l.strip()]
    latest_tag = _run(["git", "describe", "--tags", "--abbrev=0"], cwd=repo_path) or "-"
    return {
        "branch": branch,
        "dirty": dirty,
        "changed_files": changed_files,
        "recent_commits": recent_commits,
        "latest_tag": latest_tag,
    }


def collect_doctor(repo_path: Path) -> dict[str, Any]:
    commands = [
        ["mqlaunch", "doctor", "--json"],
        [str(repo_path / "terminal" / "launchers" / "mqlaunch.sh"), "doctor", "--json"],
        [str(repo_path / "tools" / "scripts" / "doctor.sh"), "--json"],
    ]
    for cmd in commands:
        out = _run(cmd, cwd=repo_path, timeout=60)
        if not out:
            continue
        # extract first JSON object
        for i, ch in enumerate(out):
            if ch in "{[":
                try:
                    data = json.loads(out[i:])
                    summary_counts = data.get("summary", {})
                    status_text = data.get("status", "unknown")
                    ok = summary_counts.get("ok", 0)
                    warn = summary_counts.get("warn", 0)
                    fail = summary_counts.get("fail", 0)
                    if fail > 0:
                        health = "Fail"
                    elif warn > 0:
                        health = "Warning"
                    elif status_text in ("ok", "healthy") or (ok > 0 and warn == 0 and fail == 0):
                        health = "Healthy"
                    else:
                        health = status_text.capitalize()
                    return {"health": health, "ok": ok, "warn": warn, "fail": fail}
                except (json.JSONDecodeError, AttributeError):
                    continue
    return {"health": "unavailable", "ok": 0, "warn": 0, "fail": 0}


def collect_ci(repo_path: Path) -> dict[str, Any]:
    out = _run(
        ["gh", "run", "list", "--limit", "5",
         "--json", "name,status,conclusion,databaseId"],
        cwd=repo_path, timeout=20,
    )
    if not out:
        return {"available": False, "runs": []}
    try:
        runs = json.loads(out)
        simplified = []
        for r in runs:
            conclusion = r.get("conclusion") or r.get("status") or "unknown"
            simplified.append({"name": r.get("name", "?"), "conclusion": conclusion})
        return {"available": True, "runs": simplified}
    except (json.JSONDecodeError, AttributeError):
        return {"available": False, "runs": []}


def collect_release(repo_path: Path) -> dict[str, Any]:
    out = _run(
        ["gh", "release", "view", "--json", "tagName,publishedAt,name"],
        cwd=repo_path, timeout=15,
    )
    if not out:
        return {"available": False}
    try:
        data = json.loads(out)
        return {
            "available": True,
            "tag": data.get("tagName", "-"),
            "name": data.get("name", "-"),
            "published_at": (data.get("publishedAt") or "")[:10],
        }
    except (json.JSONDecodeError, AttributeError):
        return {"available": False}


def collect_version(repo_path: Path) -> str:
    for candidate in [repo_path / "VERSION", repo_path / "version.txt"]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return "-"


def collect_memory_brief() -> str:
    halbin = str(BASE_DIR / "bin" / "mq-hal")
    return _run([halbin, "memory-status", "--brief"], timeout=15)


def collect_last_note(repo_name: str) -> str:
    events = read_events()
    notes = filter_events(events, event_type="note", repo=repo_name)
    if not notes:
        notes = filter_events(events, event_type="note")
    if notes:
        payload = notes[-1].get("payload", {})
        if isinstance(payload, dict):
            return str(payload.get("note", ""))
        if isinstance(payload, str):
            return payload
    return "-"


def collect_last_doctor_status(repo_name: str) -> str:
    events = read_events()
    docs = filter_events(events, event_type="doctor_summary", repo=repo_name)
    if not docs:
        return "-"
    payload = docs[-1].get("payload", {})
    if not isinstance(payload, dict):
        return "-"
    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        return str(summary.get("status", "-"))
    return "-"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

_CONCLUSION_ICON = {
    "success": "green",
    "failure": "FAIL",
    "cancelled": "cancelled",
    "skipped": "skipped",
    "in_progress": "running",
    "queued": "queued",
    "neutral": "neutral",
}


def render_text(data: dict[str, Any]) -> None:
    repo_name = data["repo"]
    git = data["git"]
    doctor = data["doctor"]
    ci = data["ci"]
    release = data["release"]

    print("HAL Brief")
    print("=========")
    print()
    print(f"Repo:    {repo_name}")
    print(f"Version: {data['version']}")
    print()

    # Git
    dirty_label = "dirty" if git["dirty"] else "clean"
    print(f"Git:     {git['branch']} · {dirty_label}")
    if git["dirty"] and git["changed_files"]:
        for f in git["changed_files"][:4]:
            print(f"         {f}")
    print(f"Tag:     {git['latest_tag']}")
    print()

    # Doctor
    d_counts = f"{doctor['ok']} ok"
    if doctor["warn"]:
        d_counts += f", {doctor['warn']} warn"
    if doctor["fail"]:
        d_counts += f", {doctor['fail']} fail"
    print(f"Doctor:  {doctor['health']}  ({d_counts})")
    last_doc = data.get("last_doctor_status")
    if last_doc and last_doc != "-" and last_doc != doctor["health"]:
        print(f"         Last saved: {last_doc}")
    print()

    # CI
    if ci["available"] and ci["runs"]:
        print("CI")
        for run in ci["runs"][:5]:
            icon = _CONCLUSION_ICON.get(run["conclusion"], run["conclusion"])
            print(f"  {icon:<12}  {run['name']}")
        print()
    elif not ci["available"]:
        print("CI:      unavailable (gh not configured or no remote)")
        print()

    # Release
    if release["available"]:
        print(f"Release: {release['tag']}  ({release['published_at']})")
    else:
        print("Release: no release found")
    print()

    # Memory
    memory_brief = data.get("memory_brief", "")
    if memory_brief:
        print(f"Memory:  {memory_brief}")
        print()

    # Last note
    note = data.get("last_note", "-")
    if note and note != "-":
        print(f"Note:    {note}")
        print()

    # Next step
    if doctor["fail"] > 0:
        next_step = "Run mqlaunch doctor and fix failing checks before release."
    elif doctor["warn"] > 0:
        next_step = "Review warnings: mqlaunch doctor --json | jq ."
    elif git["dirty"]:
        next_step = "Commit or stash working tree changes before release."
    else:
        next_step = "System looks healthy. Run mqlaunch release-check when ready."

    print("Next step")
    print("---------")
    print(next_step)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal brief",
        description="Quick status snapshot: git, doctor, CI, release, last note.",
    )
    parser.add_argument("--repo", help="Configured repo name. Defaults to config default_repo.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--sample", action="store_true", help="Print sample output without touching the repo.")
    parser.add_argument("--no-memory", action="store_true", help="Do not save to session memory.")
    args = parser.parse_args(argv)

    if args.sample:
        data: dict[str, Any] = SAMPLE
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data = {
            "repo": repo_name,
            "version": collect_version(repo_path),
            "git": collect_git(repo_path),
            "doctor": collect_doctor(repo_path),
            "ci": collect_ci(repo_path),
            "release": collect_release(repo_path),
            "last_note": collect_last_note(repo_name),
            "last_doctor_status": collect_last_doctor_status(repo_name),
            "memory_brief": collect_memory_brief(),
        }

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render_text(data)

    if not args.sample and not args.no_memory and os.environ.get("MQ_HAL_DISABLE_MEMORY") != "1":
        from session_memory import append_event
        append_event(
            "brief",
            payload={
                "repo": repo_name,
                "doctor_health": data["doctor"]["health"],
                "git_dirty": data["git"]["dirty"],
                "version": data["version"],
                "release_tag": data["release"].get("tag", "-"),
            },
            repo=repo_name,
            source="deterministic",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
