#!/usr/bin/env python3
"""Read-only presentation of mq-agent-owned workflow receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != "mq.workflow-receipt.v1":
        raise ValueError("expected mq.workflow-receipt.v1 object")
    for field in ("status", "run_id"):
        if data.get(field) is not None and not isinstance(data[field], str):
            raise ValueError(f"{field} must be a string or null")
    if data.get("ok") is not None and not isinstance(data["ok"], bool):
        raise ValueError("ok must be boolean or null")
    for field in ("repo", "runtime", "completeness", "verification", "recording", "next_action"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            raise ValueError(f"{field} must be an object or null")
    for field in ("steps", "context_sources"):
        if data.get(field) is not None and not isinstance(data[field], list):
            raise ValueError(f"{field} must be an array or null")
    if any(not isinstance(step, dict) for step in data.get("steps") or []):
        raise ValueError("steps must contain objects")
    completeness = data.get("completeness") or {}
    verification = data.get("verification") or {}
    if data.get("ok") is True and (
        data.get("status") != "completed"
        or completeness.get("status") != "complete"
        or verification.get("status") != "passed"
    ):
        raise ValueError("ok=true contradicts incomplete or unverified receipt")
    return data


def display(value: Any) -> str:
    if value is None:
        return "unknown"
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else str(value)


def render(data: dict[str, Any]) -> None:
    print("HAL Workflow Receipt")
    for label, key in (("Run", "run_id"), ("Execution run", "execution_run_id"), ("Fallback", "fallback"), ("Status", "status"), ("OK", "ok")):
        print(f"{label}: {display(data.get(key))}")
    for title, key in (("Repository", "repo"), ("Runtime", "runtime"), ("Completeness", "completeness"), ("Recording (producer)", "recording"), ("Next action", "next_action")):
        print(f"{title}:")
        section = data.get(key) or {}
        if not section:
            print("  unknown")
        for field, value in section.items():
            print(f"  {field}: {display(value)}")
    print(f"Coverage: {display((data.get('completeness') or {}).get('coverage'))}")
    print(f"Verification: {display((data.get('verification') or {}).get('status'))}")
    print("Steps:")
    for step in data.get("steps") or []:
        print("  " + " ".join(f"{key}={display(value)}" for key, value in step.items()))
    print(f"Context sources: {display(data.get('context_sources'))}")
    print("HAL writes: none (no session log or memory); producer recording is shown above.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal workflow-receipt", description="Render mq-agent receipt JSON without execution, verdict recomputation, or log writes.")
    parser.add_argument("path", nargs="?", default="-", help="Receipt JSON path, or - for stdin (default).")
    parser.add_argument("--json", action="store_true", help="Print validated receipt unchanged.")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
        data = validate(json.loads(raw))
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"ERROR: invalid workflow receipt: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
