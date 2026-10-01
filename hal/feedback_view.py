#!/usr/bin/env python3
"""Read-only presentation of mq-agent Feedback Engine records.

mq-agent owns feedback evidence, deltas, verdicts and candidates. HAL transports
and renders those records; it does not recalculate or normalize their semantics.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _agent_binary() -> str | None:
    override = os.environ.get("MQ_AGENT_BIN", "").strip()
    if override:
        return override if Path(override).is_file() else None
    found = shutil.which("mq-agent")
    if found:
        return found
    local = Path.home() / "mq-agent" / ".venv" / "bin" / "mq-agent"
    return str(local) if local.is_file() else None


def _run(args: list[str], timeout: int = 30) -> tuple[dict[str, Any] | None, str, int]:
    binary = _agent_binary()
    if binary is None:
        return None, "mq-agent unavailable", 1
    try:
        result = subprocess.run(
            [binary, "feedback", *args, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
        return None, "mq-agent feedback unavailable", 1
    if result.returncode != 0:
        return None, "mq-agent feedback command failed", result.returncode
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "mq-agent returned invalid JSON", 1
    if not isinstance(payload, dict):
        return None, "mq-agent returned invalid feedback payload", 1
    return payload, result.stdout, 0


def _value(value: Any) -> str:
    return "unavailable" if value is None else str(value)


def _render_status(data: dict[str, Any]) -> None:
    print("MQ Feedback Engine")
    print("==================")
    print(f"Health:           {_value(data.get('health'))}")
    print(f"Experiments:      {_value(data.get('valid_records'))}")
    print(f"Comparisons:      {_value(data.get('comparison_records'))}")
    print(f"Candidate events: {_value(data.get('candidate_events'))}")
    print(f"Invalid records:  {_value(data.get('invalid_records'))}")
    print(f"Newest:           {_value(data.get('newest_recorded_at'))}")
    for reason in data.get("degraded_reasons", []):
        print(f"Reason:           {reason}")


def _render_comparison(record: dict[str, Any]) -> None:
    print(f"Verdict: {record.get('verdict', 'unavailable')}")
    print(f"Comparison: {record.get('comparison_id', 'unavailable')}")
    refs = record.get("evidence_refs")
    if isinstance(refs, list):
        print(f"Evidence refs: {len(refs)}")
    metrics = record.get("metrics")
    if isinstance(metrics, dict):
        print("Deltas:")
        for name, metric in metrics.items():
            if not isinstance(metric, dict):
                continue
            print(
                f"  {name}: delta={_value(metric.get('delta'))} "
                f"direction={_value(metric.get('direction'))} "
                f"material={_value(metric.get('material'))}"
            )


def _render_report(data: dict[str, Any]) -> None:
    print("MQ Feedback Report")
    print("==================")
    print(f"Health:      {_value(data.get('health'))}")
    print(f"Experiments: {_value(data.get('matched_records'))}")
    comparison = data.get("comparison")
    if isinstance(comparison, dict):
        print(f"Comparisons: {_value(comparison.get('records'))}")
        # Producer vocabulary is displayed verbatim. Unknown future verdicts
        # remain neutral text instead of being mapped to a HAL judgement.
        print(f"Verdict:     {_value(comparison.get('reason'))}")
    metrics = data.get("metrics")
    if isinstance(metrics, dict):
        print("Latest deltas:")
        for name, metric in metrics.items():
            if isinstance(metric, dict) and metric.get("status") == "measured":
                print(f"  {name}: {_value(metric.get('value'))}")


def _render_inspect(data: dict[str, Any]) -> None:
    print(f"Feedback run: {data.get('feedback_run_id', 'unavailable')}")
    comparison = data.get("comparison")
    if isinstance(comparison, dict) and isinstance(comparison.get("record"), dict):
        _render_comparison(comparison["record"])
    elif isinstance(comparison, dict):
        print(f"Comparison: {comparison.get('status', 'unavailable')} ({comparison.get('reason', '-')})")
    candidate = data.get("candidate")
    if isinstance(candidate, dict) and isinstance(candidate.get("record"), dict):
        record = candidate["record"]
        candidate_id = str(record.get("candidate_id", "unavailable"))
        print(f"Candidate: {candidate_id}")
        print(f"Candidate state: {record.get('state', 'unavailable')}")
        print(f"Next review action: mq-agent feedback candidate {candidate_id}")
    elif isinstance(candidate, dict):
        print(f"Candidate: {candidate.get('status', 'unavailable')} ({candidate.get('reason', '-')})")


def _render_candidates(data: dict[str, Any]) -> None:
    candidates = data.get("candidates", [])
    print(f"Candidates: {data.get('count', len(candidates) if isinstance(candidates, list) else 0)}")
    if not isinstance(candidates, list):
        return
    for item in candidates:
        if not isinstance(item, dict):
            continue
        cid = item.get("candidate_id", "unavailable")
        print(
            f"{cid}  state={item.get('state', 'unavailable')} "
            f"task={item.get('task_class', 'unavailable')} "
            f"proposed={item.get('proposed_strategy', 'unavailable')}"
        )
        print(f"  review: mq-agent feedback candidate {cid}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal feedback",
        description="Read-only view of mq-agent Feedback Engine evidence.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=["status", "report", "inspect", "compare", "candidates"],
    )
    parser.add_argument("value", nargs="?")
    parser.add_argument("--task-class")
    parser.add_argument("--since")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    call: list[str] = [args.command]
    if args.command in {"inspect", "compare"}:
        if not args.value:
            parser.error(f"{args.command} requires a feedback run id")
        call.append(args.value)
    if args.command == "report":
        if args.task_class:
            call.extend(["--task-class", args.task_class])
        if args.since:
            call.extend(["--since", args.since])

    data, raw, rc = _run(call)
    if data is None:
        print(raw, file=sys.stderr)
        return rc or 1
    if args.json:
        # Preserve mq-agent's machine contract byte-for-byte.
        print(raw, end="" if raw.endswith("\n") else "\n")
        return 0

    if args.command == "status":
        _render_status(data)
    elif args.command == "report":
        _render_report(data)
    elif args.command == "inspect":
        _render_inspect(data)
    elif args.command == "compare":
        _render_comparison(data)
    else:
        _render_candidates(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
