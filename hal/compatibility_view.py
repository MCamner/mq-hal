"""Human presentation of mq-agent's stack compatibility report.

mq-agent owns the assessment: findings, codes, severities, release blocking and
the next action. This module shows what that assessment produced.

The boundary invariant:

    Presentation may expose the report and its conclusions; it must not
    derive a new conclusion, remedy, severity, or release decision of its own.

So there is no code-to-severity map and no blocking rule here. Colour keys on
the supplied status or severity and nothing else, and an unfamiliar future
code or status prints verbatim. The exit code is mq-agent's own, passed
through, so a script or mqlaunch reading `mq-hal compatibility` gets the same
verdict as one reading `mq-agent stack compatibility`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from hal.compatibility import read_compatibility  # noqa: E402


STATUS_STYLE: dict[str, str] = {
    "PASS": "\033[32m",
    "SKIPPED": "\033[2m",
    "WARN": "\033[33m",
    "FAIL": "\033[31m",
    "UNAVAILABLE": "\033[35m",
}

_RESET = "\033[0m"
_NAME_WIDTH = 44


def _colour_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _styled(status: str) -> str:
    style = STATUS_STYLE.get(status, "")
    if not style or not _colour_enabled():
        return status
    return f"{style}{status}{_RESET}"


def _list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def render(report: dict[str, Any]) -> None:
    """Show the report. Conclude nothing from it."""
    print(f"{'MQ Stack Compatibility':<{_NAME_WIDTH}} {_styled(str(report.get('status') or '—'))}")

    components = _list(report.get("components"))
    if components:
        print()
        print("Repositories")
        for component in components:
            name = str(component.get("repo") or component.get("name") or "—")
            print(f"  {name:<{_NAME_WIDTH - 2}} {_styled(str(component.get('status') or '—'))}")

    relationships = _list(report.get("relationships"))
    if relationships:
        print()
        print("Relationships")
        for rel in relationships:
            pair = f"{rel.get('producer', '—')} → {rel.get('consumer', '—')}"
            print(f"  {pair:<{_NAME_WIDTH - 2}} {_styled(str(rel.get('status') or '—'))}")
            subject = rel.get("subject")
            detail = rel.get("detail")
            if subject:
                print(f"    {subject}")
            if detail:
                print(f"    {detail}")

    findings = _list(report.get("findings"))
    if findings:
        print()
        print("Findings")
        for finding in findings:
            severity = str(finding.get("severity") or "—")
            repos = finding.get("repos") or [finding.get("repo") or "—"]
            print(f"  {_styled(severity)}  {finding.get('code', '—')}  [{', '.join(map(str, repos))}]")
            if finding.get("message"):
                print(f"    {finding['message']}")

    action = report.get("next_action")
    if action:
        print()
        print("Next action")
        print(f"  {action}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal compatibility",
        description="Show the stack compatibility report produced by mq-agent.",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    result = read_compatibility()
    if not result.ok:
        # No report was obtained. Say only that, on stderr, so the JSON
        # surface stays empty rather than carrying an invented report.
        print(result.error, file=sys.stderr)
        return result.returncode or 1

    if args.json:
        # The producer's own bytes, never re-serialized.
        print(result.raw)
    else:
        render(result.data or {})
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
