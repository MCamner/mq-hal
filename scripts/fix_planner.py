#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from session_memory import append_event  # noqa: E402
from model_profiles import profile_for_name  # noqa: E402
from openai_client import generate_structured  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
DOCTOR_SUMMARY_SCRIPT = BASE_DIR / "scripts" / "doctor_summary.py"
PROMPT_PATH = BASE_DIR / "prompts" / "fix-planner.txt"

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "plan_summary": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string"},
                    "title": {"type": "string"},
                    "reason": {"type": "string"},
                    "safe_commands": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["priority", "title", "reason", "safe_commands"],
                "additionalProperties": False,
            },
        },
        "safe_commands": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["status", "plan_summary", "actions", "safe_commands"],
    "additionalProperties": False,
}

BLOCKED_TOKENS = [
    " rm ",
    "rm -",
    "sudo rm",
    "git reset --hard",
    "git clean",
    "push --force",
    "push -f",
    "chmod -r",
    "chown -r",
    "kill -9",
    "pkill",
    "security delete",
    "op item delete",
]

ALLOWED_PREFIXES = [
    "git status",
    "git diff",
    "git log",
    "git branch",
    "git remote",
    "gh run list",
    "gh run view",
    "gh run watch",
    "gh release view",
    "mqlaunch doctor",
    "mqlaunch selftest",
    "mqlaunch release-check",
    "mqlaunch hal doctor",
    "mqlaunch hal fix-doctor",
    "python3 -m py_compile",
    "bash -n",
    "shellcheck",
    "jq",
    "cat ",
    "sed -n",
    "grep ",
    "find ",
    "ls ",
    "pwd",
]


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def is_safe_command(command: str) -> bool:
    normalized = " " + command.strip().lower() + " "
    if not command.strip():
        return False
    if any(token in normalized for token in BLOCKED_TOKENS):
        return False
    return any(command.strip().startswith(prefix) for prefix in ALLOWED_PREFIXES)


def clean_commands(commands: list[Any]) -> list[str]:
    cleaned: list[str] = []
    for item in commands:
        cmd = str(item).strip()
        if is_safe_command(cmd) and cmd not in cleaned:
            cleaned.append(cmd)
    return cleaned


def prompt_text() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "Create a safe fix plan from a doctor summary. Do not execute commands."


def run_doctor_summary(repo: str | None, sample: bool = False) -> dict[str, Any]:
    command = [sys.executable, str(DOCTOR_SUMMARY_SCRIPT), "--json", "--no-ai", "--no-memory"]
    if repo:
        command.extend(["--repo", repo])
    if sample:
        command.append("--sample")

    try:
        completed = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            text=True,
            capture_output=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        die("doctor summary timed out")

    if completed.returncode != 0:
        detail = (completed.stdout or "") + (completed.stderr or "")
        die(f"doctor summary failed:\n{detail}")

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        die(f"doctor summary returned invalid JSON: {exc}\n{completed.stdout[:1000]}")

    if not isinstance(parsed, dict):
        die("doctor summary did not return a JSON object")

    return parsed


def fallback_plan(summary_envelope: dict[str, Any]) -> dict[str, Any]:
    summary = summary_envelope.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    findings = summary.get("key_findings", [])
    if not isinstance(findings, list):
        findings = []

    text = "\n".join(str(item).lower() for item in findings)
    actions: list[dict[str, Any]] = []

    if any(token in text for token in ["dirty", "uncommitted", "working tree", "modified"]):
        actions.append({
            "priority": "high",
            "title": "Granska ändringar i git-trädet",
            "reason": "Doctor Summary antyder opushade eller ocommittade ändringar.",
            "safe_commands": ["git status --short", "git diff --stat", "git diff"],
        })

    if any(token in text for token in ["missing", "not found", "saknas", "command not found"]):
        actions.append({
            "priority": "high",
            "title": "Identifiera saknade verktyg eller filer",
            "reason": "Doctor Summary antyder att något saknas eller inte hittas.",
            "safe_commands": ["mqlaunch doctor --json | jq ."],
        })

    has_failure = any(
        token in text for token in [": failed", ": error", ": timeout", "status: fail"]
    ) or any(
        line.strip().startswith(("fail", "error", "timeout"))
        for line in text.splitlines()
        if not line.lstrip().startswith("no ")
    )
    if has_failure:
        actions.append({
            "priority": "high",
            "title": "Isolera felande kontroll",
            "reason": "Doctor Summary innehåller felmarkörer.",
            "safe_commands": ["mqlaunch doctor --json | jq .", "mqlaunch selftest"],
        })

    if not actions:
        actions.append({
            "priority": "normal",
            "title": "Verifiera att kedjan fortfarande är grön",
            "reason": "Inga tydliga fel hittades i sammanfattningen.",
            "safe_commands": [
                "mqlaunch hal doctor --no-ai",
                "mqlaunch selftest",
                "mqlaunch release-check",
            ],
        })

    all_commands: list[str] = []
    for action in actions:
        action["safe_commands"] = clean_commands(action.get("safe_commands", []))
        all_commands.extend(action["safe_commands"])

    return {
        "status": "Fix plan ready",
        "plan_summary": "Säker åtgärdsplan skapad från HAL Doctor Summary. Inga kommandon körs automatiskt.",
        "actions": actions,
        "safe_commands": clean_commands(all_commands),
    }


def call_model_plan(summary_envelope: dict[str, Any]) -> dict[str, Any] | None:
    try:
        profile = profile_for_name("planner", default_profile="planner")
    except ValueError:
        return None
    raw = generate_structured(
        model=profile["model"],
        reasoning_effort=profile["reasoning_effort"],
        instructions=prompt_text(),
        input_text=json.dumps(summary_envelope, indent=2, ensure_ascii=False),
        schema=PLAN_SCHEMA,
        schema_name="mq_hal_fix_plan",
    )
    if not isinstance(raw, str) or not raw.strip():
        return None

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(plan, dict):
        return None

    actions = plan.get("actions", [])
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                action["safe_commands"] = clean_commands(action.get("safe_commands", []))

    plan["safe_commands"] = clean_commands(plan.get("safe_commands", []))

    if not plan["safe_commands"]:
        plan["safe_commands"] = fallback_plan(summary_envelope)["safe_commands"]

    return plan


def render_plan(plan: dict[str, Any], used_ai: bool, summary_envelope: dict[str, Any]) -> None:
    source = "OpenAI" if used_ai else "deterministic fallback"

    print("HAL Fix Planner")
    print("===============")
    print()
    print(f"Source: {source}")
    print(f"Repo:   {summary_envelope.get('repo', 'unknown')}")
    print()
    print(f"Status: {plan.get('status', 'Unknown')}")
    print()
    print("Plan")
    print("----")
    print(plan.get("plan_summary", "No plan summary available."))
    print()

    actions = plan.get("actions", [])
    if isinstance(actions, list) and actions:
        print("Actions")
        print("-------")
        for i, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                continue
            print(f"{i}. {action.get('title', 'Untitled')}")
            print(f"   Priority: {action.get('priority', 'normal')}")
            print(f"   Reason:   {action.get('reason', '')}")
            commands = action.get("safe_commands", [])
            if isinstance(commands, list) and commands:
                print("   Commands:")
                for cmd in commands:
                    print(f"     {cmd}")
            print()

    commands = plan.get("safe_commands", [])
    if isinstance(commands, list) and commands:
        print("Copy-paste checklist")
        print("--------------------")
        for cmd in commands:
            print(f"  {cmd}")
        print()

    print("Nothing was executed.")
    print("Review commands before running them.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal fix-doctor",
        description="Create a safe fix plan from HAL Doctor Summary.",
    )
    parser.add_argument("--repo", help="Configured repo name")
    parser.add_argument("--json", action="store_true", help="Print machine-readable plan JSON")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic fallback only")
    parser.add_argument("--sample", action="store_true", help="Use embedded sample doctor JSON (CI/smoke tests)")
    parser.add_argument("--no-memory", action="store_true", help="Do not save result to HAL Session Memory.")

    args = parser.parse_args(argv)

    summary_envelope = run_doctor_summary(args.repo, sample=args.sample)
    ai_plan = None if args.no_ai else call_model_plan(summary_envelope)
    plan = ai_plan or fallback_plan(summary_envelope)
    used_ai = ai_plan is not None

    envelope = {
        "used_ai": used_ai,
        "summary": summary_envelope,
        "plan": plan,
    }

    repo_name: str | None = None
    if isinstance(summary_envelope, dict):
        repo_value = summary_envelope.get("repo")
        if isinstance(repo_value, str):
            repo_name = repo_value

    if not args.sample and not args.no_memory and os.environ.get("MQ_HAL_DISABLE_MEMORY") != "1":
        append_event(
            "fix_plan",
            payload=envelope,
            repo=repo_name,
            source="openai" if used_ai else "deterministic",
        )

    if args.json:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
        return 0

    render_plan(plan, used_ai, summary_envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
