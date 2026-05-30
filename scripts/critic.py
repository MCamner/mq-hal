#!/usr/bin/env python3
"""mq-hal critic: review a plan.json for safety and completeness."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE_PLAN: dict[str, Any] = {
    "goal": "Fix release-check in macos-scripts",
    "affected_repos": ["macos-scripts"],
    "affected_files": ["scripts/release-check.sh"],
    "risk": "low",
    "steps": [
        {
            "id": 1,
            "description": "Review current release-check.sh",
            "safe_command": "cat scripts/release-check.sh",
            "requires_confirm": False,
        },
        {
            "id": 2,
            "description": "Run release-check to see failures",
            "safe_command": "bash scripts/release-check.sh",
            "requires_confirm": False,
        },
        {
            "id": 3,
            "description": "Apply the identified fix",
            "safe_command": None,
            "requires_confirm": True,
        },
    ],
    "validation": [
        "bash scripts/release-check.sh passes without errors",
        "CI is green after the change",
    ],
    "rollback_plan": "git restore scripts/release-check.sh",
}

# Patterns that must not appear in safe_command values
_DANGEROUS = re.compile(
    r"rm\s+-[rRf]"
    r"|rm\s+--recursive"
    r"|--force"
    r"|git\s+reset\s+--hard"
    r"|git\s+clean"
    r"|git\s+push\s+-f"
    r"|\bsudo\b"
    r"|\bpkill\b"
    r"|\bkillall\b"
    r"|kill\s+-9"
    r"|chmod\s+-R\s+777"
    r"|chown\s+-R"
    r"|\|\s*(ba)?sh\b"
    r"|security\s+delete",
    re.IGNORECASE,
)

_TEST_KEYWORDS = re.compile(
    r"\b(test|smoke|pytest|jest|spec|assert|verify|check|ci|pass|validate)\b",
    re.IGNORECASE,
)


@dataclass
class Finding:
    level: str   # "pass" | "warn" | "fail"
    check: str
    message: str


def _known_repos() -> set[str]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return set(data.get("repos", {}).keys())
    except (OSError, json.JSONDecodeError):
        return set()


def run_checks(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    risk = str(plan.get("risk", "unknown"))
    steps: list[dict[str, Any]] = plan.get("steps", [])
    validation: list[str] = plan.get("validation", [])
    affected_repos: list[str] = plan.get("affected_repos", [])
    affected_files: list[str] = plan.get("affected_files", [])
    rollback = plan.get("rollback_plan")
    known = _known_repos()

    # 1. Rollback plan
    if rollback:
        findings.append(Finding("pass", "rollback",
                                "rollback plan is present"))
    elif risk in ("medium", "high"):
        findings.append(Finding("fail", "rollback",
                                f"no rollback plan (required for risk: {risk})"))
    else:
        findings.append(Finding("warn", "rollback",
                                "no rollback plan"))

    # 2. Validation steps
    if validation:
        findings.append(Finding("pass", "validation",
                                f"{len(validation)} validation step(s) defined"))
    else:
        findings.append(Finding("warn", "validation",
                                "no validation steps — add checks to verify success"))

    # 3. High/medium risk steps require confirmation
    unconfirmed = [
        s for s in steps
        if s.get("requires_confirm") is not True
        and s.get("safe_command")
        and risk in ("medium", "high")
    ]
    if unconfirmed:
        findings.append(Finding(
            "warn", "confirmation",
            f"{len(unconfirmed)} modifying step(s) without requires_confirm "
            f"(plan risk: {risk})",
        ))
    else:
        findings.append(Finding("pass", "confirmation",
                                "confirmation flags look correct"))

    # 4. Dangerous commands
    dangerous = []
    for step in steps:
        cmd = step.get("safe_command") or ""
        if cmd and _DANGEROUS.search(cmd):
            dangerous.append(f"step {step.get('id', '?')}: {cmd[:60]}")
    if dangerous:
        findings.append(Finding("fail", "dangerous-commands",
                                "dangerous command(s) detected: "
                                + "; ".join(dangerous)))
    else:
        findings.append(Finding("pass", "dangerous-commands",
                                "no dangerous commands detected"))

    # 5. Affected repos are known
    if known:
        unknown_repos = [r for r in affected_repos if r not in known]
        if unknown_repos:
            findings.append(Finding(
                "warn", "known-repos",
                f"unknown repo(s): {', '.join(unknown_repos)} "
                f"(not in config/repos.json)",
            ))
        else:
            findings.append(Finding("pass", "known-repos",
                                    "all affected repos are configured"))

    # 6. Over-broad changes
    if len(affected_files) > 10:
        findings.append(Finding(
            "warn", "scope",
            f"{len(affected_files)} affected files — consider splitting "
            f"into smaller plans",
        ))
    else:
        findings.append(Finding("pass", "scope",
                                f"scope looks reasonable "
                                f"({len(affected_files)} file(s))"))

    # 7. Missing steps for non-trivial risk
    if not steps and risk not in ("unknown", "low"):
        findings.append(Finding(
            "warn", "steps",
            f"plan has no steps (risk: {risk})",
        ))
    elif steps:
        findings.append(Finding("pass", "steps",
                                f"{len(steps)} step(s) defined"))

    # 8. Missing tests — no test-related content for medium/high risk
    all_text = " ".join(validation) + " ".join(
        str(s.get("description", "")) + str(s.get("safe_command") or "")
        for s in steps
    )
    if risk in ("medium", "high") and not _TEST_KEYWORDS.search(all_text):
        findings.append(Finding(
            "warn", "missing-tests",
            f"no test or verify commands visible (risk: {risk})",
        ))
    else:
        findings.append(Finding("pass", "missing-tests",
                                "test/validation content present"))

    return findings


def verdict(findings: list[Finding]) -> str:
    levels = {f.level for f in findings}
    if "fail" in levels:
        return "FAIL"
    if "warn" in levels:
        return "REVIEW"
    return "PASS"


def render(
    plan: dict[str, Any],
    findings: list[Finding],
    plan_file: str,
) -> None:
    v = verdict(findings)
    fail_n = sum(1 for f in findings if f.level == "fail")
    warn_n = sum(1 for f in findings if f.level == "warn")

    print("HAL Critic")
    print("==========")
    print()
    print(f"Plan:   {plan_file}")
    print(f"Goal:   {plan.get('goal', '-')}")
    print(f"Risk:   {plan.get('risk', '-')}")
    print()
    print("Checks")
    print("------")

    icons = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    for f in findings:
        tag = f"[{icons[f.level]:<4}]"
        print(f"{tag} {f.check}: {f.message}")

    print()
    summary = ""
    if fail_n:
        summary += f"  {fail_n} failure(s)"
    if warn_n:
        summary += f"  {warn_n} warning(s)"
    print(f"Verdict: {v}{summary}")
    print()

    if v != "FAIL":
        print("Next:  mq-hal execute plan.json --confirm")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal critic",
        description="Review a plan.json for safety and completeness.",
    )
    parser.add_argument("plan_file", nargs="?", default="-",
                        help="Path to plan JSON file (default: stdin)")
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Critique a built-in sample plan",
    )
    args = parser.parse_args(argv)

    if args.sample:
        plan = SAMPLE_PLAN
        plan_label = "<sample>"
    elif args.plan_file == "-":
        try:
            plan = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON on stdin: {exc}", file=sys.stderr)
            return 1
        plan_label = "<stdin>"
    else:
        path = Path(args.plan_file)
        if not path.exists():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 1
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
            return 1
        plan_label = str(path)

    if not isinstance(plan, dict):
        print("ERROR: plan must be a JSON object", file=sys.stderr)
        return 1

    findings = run_checks(plan)
    v = verdict(findings)

    if args.json_out:
        fail_n = sum(1 for f in findings if f.level == "fail")
        warn_n = sum(1 for f in findings if f.level == "warn")
        print(json.dumps({
            "plan_file": plan_label,
            "goal": plan.get("goal", ""),
            "risk": plan.get("risk", "unknown"),
            "verdict": v.lower(),
            "findings": [
                {"level": f.level, "check": f.check, "message": f.message}
                for f in findings
            ],
            "fail_count": fail_n,
            "warn_count": warn_n,
        }, indent=2, ensure_ascii=False))
        return 0

    render(plan, findings, plan_label)
    return 1 if v == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
