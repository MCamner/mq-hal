#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from session_memory import SESSION_PATH, filter_events, read_events  # noqa: E402


def parse_time(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value[:16]


def event_status(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    payload = event.get("payload", {})

    if not isinstance(payload, dict):
        return "-"

    if event_type == "doctor_summary":
        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            return str(summary.get("status", "-"))

    if event_type == "fix_plan":
        plan = payload.get("plan", {})
        if isinstance(plan, dict):
            return str(plan.get("status", "-"))

    if event_type == "note":
        note = payload.get("note")
        if isinstance(note, str):
            return note[:44]

    return str(payload.get("status") or payload.get("message") or "-")


def event_detail(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    payload = event.get("payload", {})

    if not isinstance(payload, dict):
        return ""

    if event_type == "doctor_summary":
        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            return str(summary.get("summary", ""))[:80]

    if event_type == "fix_plan":
        plan = payload.get("plan", {})
        if isinstance(plan, dict):
            return str(plan.get("plan_summary", ""))[:80]

    if event_type == "note":
        return str(payload.get("note", ""))[:80]

    return ""


def compact_type(value: Any) -> str:
    return str(value or "-")[:16]


def compact_repo(value: Any) -> str:
    return str(value or "-")[:16]


def parse_time_short(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%H:%M")
    except ValueError:
        return value[:5]


def render_timeline(
    events: list[dict[str, Any]],
    limit: int,
    details: bool = False,
    compact: bool = False,
) -> None:
    selected = events[-limit:]

    print("HAL Timeline")
    print("============")
    print()
    print(f"Path:  {SESSION_PATH}")
    print(f"Items: {len(events)} total, showing {len(selected)}")
    print()

    if not selected:
        print("No timeline events found.")
        return

    if compact:
        print(f"{'TIME':5}  {'TYPE':14}  REPO")
        print(f"{'-' * 5}  {'-' * 14}  {'-' * 14}")
        for event in selected:
            time_text = parse_time_short(event.get("timestamp"))
            type_text = compact_type(event.get("type"))
            repo_text = compact_repo(event.get("repo"))
            print(f"{time_text:5}  {type_text:14}  {repo_text}")
        return

    print(f"{'TIME':16}  {'TYPE':16}  {'REPO':16}  STATUS")
    print(f"{'-' * 16}  {'-' * 16}  {'-' * 16}  {'-' * 40}")

    for event in selected:
        time_text = parse_time(event.get("timestamp"))
        type_text = compact_type(event.get("type"))
        repo_text = compact_repo(event.get("repo"))
        status_text = event_status(event)

        print(f"{time_text:16}  {type_text:16}  {repo_text:16}  {status_text}")

        if details:
            detail = event_detail(event)
            if detail:
                print(
                    f"{'':16}  {'':16}  {'':16}  ↳ {detail}"
                )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal timeline",
        description="Show HAL Session Memory as a compact timeline.",
    )

    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--type", dest="event_type")
    parser.add_argument("--repo")
    parser.add_argument("--details", action="store_true",
                        help="Show payload detail per event")
    parser.add_argument("--compact", action="store_true",
                        help="Short format: time, type, repo only")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    events = read_events()
    events = filter_events(events, event_type=args.event_type, repo=args.repo)

    if args.json:
        print(json.dumps(events[-args.limit:], indent=2, ensure_ascii=False))
        return 0

    render_timeline(
        events,
        limit=args.limit,
        details=args.details,
        compact=args.compact,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
