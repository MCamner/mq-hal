#!/usr/bin/env python3
"""Check HAL's local release gate against named CI checks without running them."""
from __future__ import annotations

import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI_ONLY = {
    "markdownlint.yml": "CI-only: Node markdownlint action; local READY does not certify Markdown style.",
    "release.yml": "CI-only: publishes tags after preflight; not a PR release assertion.",
}
STEPS = {
    "tests.yml": ["Checkout", "Show Python version", "Release check (dry-run)",
                  "Check skills consistency"],
    "gate-parity.yml": ["Checkout", "Validate gate parity", "Test parity failures",
                        "Run release gate"],
}
CI_COMMANDS = {
    "tests.yml": ["./release-check.sh --dry-run", "./scripts/check-skills.sh"],
    "gate-parity.yml": ["python3 scripts/check-gate-parity.py", "--self-test",
                        "./release-check.sh --json"],
}
LOCAL_COMMANDS = {
    "skills": "bash scripts/check-skills.sh",
    "parity": "python3 scripts/check-gate-parity.py",
    "smoke": "_smoke smoke.sh",
    "docs": "./tools/check-command-docs.sh",
}


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    actual_files = {p.name for p in workflow_dir.glob("*.yml")} | {p.name for p in workflow_dir.glob("*.yaml")}
    expected_files = set(STEPS) | set(CI_ONLY)
    for name in sorted(actual_files - expected_files):
        errors.append(f"workflow not declared: {name}")
    for name in sorted(expected_files - actual_files):
        errors.append(f"declared workflow absent: {name}")
    for name, reason in CI_ONLY.items():
        if not reason.startswith("CI-only:") or len(reason) < 30:
            errors.append(f"CI-only reason missing: {name}")
    for name, expected_steps in STEPS.items():
        path = workflow_dir / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        steps = re.findall(r"^\s*- name:\s*(.+?)\s*$", text, re.M)
        if Counter(steps) != Counter(expected_steps):
            errors.append(f"CI steps changed: {name}: {steps!r}")
        for cmd in CI_COMMANDS[name]:
            if cmd not in text:
                errors.append(f"CI command missing: {name}: {cmd}")
    gate = root / "release-check.sh"
    if not gate.is_file():
        errors.append("release-check.sh absent")
    else:
        content = gate.read_text(encoding="utf-8")
        for label, cmd in LOCAL_COMMANDS.items():
            if cmd not in content:
                errors.append(f"local {label} check missing: {cmd}")
    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = root / ".github" / "workflows"
        directory.mkdir(parents=True)
        gate = root / "release-check.sh"
        gate.write_text("\n".join(LOCAL_COMMANDS.values()))
        for name, steps in STEPS.items():
            (directory / name).write_text("\n".join(f"      - name: {step}" for step in steps)
                                          + "\n" + "\n".join(CI_COMMANDS[name]))
        for name in CI_ONLY:
            (directory / name).write_text("# CI-only\n")
        assert not verify(root), verify(root)
        original = gate.read_text()
        gate.write_text(original.replace(LOCAL_COMMANDS["skills"], ""))
        assert any("local skills" in x for x in verify(root))
        gate.write_text(original)
        workflow = directory / "tests.yml"
        original = workflow.read_text()
        workflow.write_text(original.replace("      - name: Check skills consistency", ""))
        assert any("CI steps changed" in x for x in verify(root))
        workflow.write_text(original.replace("./scripts/check-skills.sh", ""))
        assert any("CI command missing" in x for x in verify(root))
        workflow.write_text(original)
        (directory / "unknown.yml").write_text("on: push\n")
        assert any("workflow not declared" in x for x in verify(root))
    print("PASS: positive gate and four deliberate failures")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        raise SystemExit(self_test())
    if len(sys.argv) > 1:
        raise SystemExit("usage: check-gate-parity.py [--self-test]")
    failures = verify(ROOT)
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        raise SystemExit(1)
    print("PASS: HAL release gate parity and documented CI-only workflows")
