#!/usr/bin/env python3
"""mq-hal execute: run a validated plan step by step."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

# Shell metacharacters that must not appear in safe_command
_SHELL_OPS = re.compile(r"[|;&`<>$]|\$\(|\|\|")


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {"repos": {}}


def resolve_repo_path(
    affected_repos: list[str],
    config: dict[str, Any],
) -> Path:
    repos = config.get("repos", {})
    for name in affected_repos:
        if name in repos:
            p = Path(str(repos[name])).expanduser().resolve()
            if p.exists():
                return p
    return Path.cwd()


def run_critic(plan: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Run critic checks inline. Returns (verdict, findings)."""
    # Import critic from same directory
    sys.path.insert(0, str(Path(__file__).parent))
    import critic as _critic  # noqa: PLC0415
    findings_raw = _critic.run_checks(plan)
    v = _critic.verdict(findings_raw)
    findings = [
        {"level": f.level, "check": f.check, "message": f.message}
        for f in findings_raw
    ]
    return v, findings


def validate_command(cmd: str) -> str | None:
    """Return error message if command is unsafe, else None."""
    if not cmd or not cmd.strip():
        return "empty command"
    if _SHELL_OPS.search(cmd):
        return f"shell operator detected in command: {cmd!r}"
    try:
        parts = shlex.split(cmd)
    except ValueError as exc:
        return f"could not parse command: {exc}"
    if not parts:
        return "empty command after parsing"
    return None


def confirm_step(step: dict[str, Any], repo_path: Path) -> bool:
    desc = step.get("description", "")
    cmd = step.get("safe_command", "")
    step_id = step.get("id", "?")
    print(f"  Step {step_id}: {desc}")
    if cmd:
        print(f"  $ {cmd}")
    print(f"  cwd: {repo_path}")
    print()
    answer = input("  Run this step? [y/N] ").strip().lower()
    return answer in {"y", "yes", "j", "ja"}


def run_step(
    step: dict[str, Any],
    repo_path: Path,
    auto_confirm: bool = False,
) -> tuple[bool, int]:
    """
    Returns (skipped, exit_code).
    skipped=True means no command was run.
    """
    desc = step.get("description", "")
    cmd = step.get("safe_command")
    requires = step.get("requires_confirm", False)

    if not cmd:
        print(f"  ↳ manual step — no command defined, skipped")
        return True, 0

    err = validate_command(cmd)
    if err:
        step_id = step.get("id", "?")
        print(f"  ERROR: refusing to run step {step_id}: {err}",
              file=sys.stderr)
        return False, 2

    if requires or auto_confirm:
        if not confirm_step(step, repo_path):
            print("  Cancelled.")
            return True, 0

    try:
        parts = shlex.split(cmd)
        result = subprocess.run(parts, cwd=str(repo_path))
        return False, result.returncode
    except FileNotFoundError:
        print(f"  ERROR: command not found: {shlex.split(cmd)[0]}",
              file=sys.stderr)
        return False, 127
    except OSError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return False, 1


def render_preflight(verdict: str, findings: list[dict[str, Any]]) -> None:
    icons = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    for f in findings:
        tag = f"[{icons.get(f['level'], '????'):4}]"
        print(f"  {tag} {f['check']}: {f['message']}")
    print(f"  Verdict: {verdict}")
    print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal execute",
        description="Execute a validated plan step by step.",
    )
    parser.add_argument(
        "plan_file",
        help="Path to plan JSON file",
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Confirm and execute. Without this flag, shows a dry-run preview.",
    )
    parser.add_argument(
        "--skip-critic", action="store_true",
        help="Skip pre-flight critic check (not recommended).",
    )
    args = parser.parse_args(argv)

    path = Path(args.plan_file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(plan, dict):
        print("ERROR: plan must be a JSON object", file=sys.stderr)
        return 1

    config = load_config()
    affected_repos_raw = plan.get("affected_repos", [])
    affected_repos = [
        str(repo) for repo in affected_repos_raw
    ] if isinstance(affected_repos_raw, list) else []
    repo_path = resolve_repo_path(affected_repos, config)
    steps_raw = plan.get("steps", [])
    if not isinstance(steps_raw, list):
        print("ERROR: plan.steps must be a list", file=sys.stderr)
        return 1
    steps = []
    for index, step in enumerate(steps_raw, start=1):
        if not isinstance(step, dict):
            print(f"ERROR: plan step {index} must be an object",
                  file=sys.stderr)
            return 1
        steps.append(step)

    print("HAL Execute")
    print("===========")
    print()
    print(f"Plan:  {path}")
    print(f"Goal:  {plan.get('goal', '-')}")
    print(f"Risk:  {plan.get('risk', '-')}")
    print(f"Repo:  {repo_path}")
    print()

    # Pre-flight critic check
    if not args.skip_critic:
        print("Pre-flight critic check")
        print("-----------------------")
        try:
            verdict, findings = run_critic(plan)
        except Exception as exc:
            print(f"  WARN: critic check failed: {exc}", file=sys.stderr)
            verdict, findings = "REVIEW", []
        render_preflight(verdict, findings)

        if verdict == "FAIL":
            print(
                "ERROR: critic returned FAIL — refusing to execute.\n"
                "Fix the plan or run mq-hal critic for details.",
                file=sys.stderr,
            )
            return 1

    if not args.confirm:
        # Dry-run preview
        print("Steps (dry run — add --confirm to execute)")
        print("-------------------------------------------")
        for step in steps:
            cmd = step.get("safe_command")
            conf = " ⚠ requires confirmation" if step.get(
                "requires_confirm"
            ) else ""
            step_id = step.get("id", "?")
            print(f"  {step_id}. {step.get('description', '-')}{conf}")
            if cmd:
                print(f"     $ {cmd}")
            else:
                print("     (manual step)")
        print()
        rollback = plan.get("rollback_plan")
        if rollback:
            print(f"Rollback: {rollback}")
            print()
        print(f"Run:  mq-hal execute {path} --confirm")
        return 0

    # Execute
    print(f"Executing {len(steps)} step(s) in {repo_path}")
    print()
    total = len(steps)
    ran = 0
    skipped = 0
    failed = 0

    for i, step in enumerate(steps, start=1):
        desc = step.get("description", "-")
        print(f"[{i}/{total}] {desc}")
        was_skipped, code = run_step(
            step,
            repo_path,
            auto_confirm=False,
        )
        if was_skipped:
            skipped += 1
            print()
            continue
        ran += 1
        if code == 0:
            print(f"  [exit {code}] OK")
        else:
            print(f"  [exit {code}] FAILED")
            failed += 1
            print()
            print(
                f"Stopping after step {i} (exit {code}).\n"
                f"Rollback: {plan.get('rollback_plan') or '(none defined)'}",
                file=sys.stderr,
            )
            break
        print()

    print(
        f"Done. {ran} run, {skipped} skipped, {failed} failed "
        f"({total} total)."
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
