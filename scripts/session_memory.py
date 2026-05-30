#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))).expanduser()
SESSION_PATH = STATE_DIR / "session.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def append_event(
    event_type: str,
    payload: dict[str, Any],
    repo: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    ensure_state_dir()

    event: dict[str, Any] = {
        "timestamp": now_iso(),
        "type": event_type,
        "repo": repo,
        "source": source,
        "payload": payload,
    }

    with SESSION_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def read_events() -> list[dict[str, Any]]:
    if not SESSION_PATH.exists():
        return []

    events: list[dict[str, Any]] = []

    with SESSION_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)

    return events


def filter_events(
    events: list[dict[str, Any]],
    event_type: str | None = None,
    repo: str | None = None,
) -> list[dict[str, Any]]:
    result = events

    if event_type:
        result = [e for e in result if e.get("type") == event_type]

    if repo:
        result = [e for e in result if e.get("repo") == repo]

    return result


def summarize_event(event: dict[str, Any]) -> str:
    timestamp = event.get("timestamp", "unknown-time")
    event_type = event.get("type", "unknown")
    repo = event.get("repo") or "-"
    payload = event.get("payload", {})

    if not isinstance(payload, dict):
        payload = {}

    if event_type == "doctor_summary":
        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            status = summary.get("status", "unknown")
            text = summary.get("summary", "")
            return f"{timestamp}  {event_type:16} repo={repo:14} status={status} — {text}"

    if event_type == "fix_plan":
        plan = payload.get("plan", {})
        if isinstance(plan, dict):
            status = plan.get("status", "unknown")
            text = plan.get("plan_summary", "")
            return f"{timestamp}  {event_type:16} repo={repo:14} status={status} — {text}"

    if event_type == "note":
        note = payload.get("note", "")
        return f"{timestamp}  {event_type:16} repo={repo:14} {note}"

    title = payload.get("title") or payload.get("message") or ""
    return f"{timestamp}  {event_type:16} repo={repo:14} {title}"


def render_events(events: list[dict[str, Any]], limit: int) -> None:
    if not events:
        print("HAL Session Memory")
        print("==================")
        print()
        print("No session memory found.")
        print(f"Path: {SESSION_PATH}")
        return

    selected = events[-limit:]

    print("HAL Session Memory")
    print("==================")
    print()
    print(f"Path:  {SESSION_PATH}")
    print(f"Items: {len(events)} total, showing {len(selected)}")
    print()

    for event in selected:
        print(summarize_event(event))

    # Summary by type
    from collections import Counter
    counts = Counter(str(e.get("type", "unknown")) for e in events)
    if counts:
        print()
        print("Summary")
        print("-------")
        for etype, count in sorted(counts.items()):
            print(f"  {etype:<20}  {count}")


def render_last(event: dict[str, Any] | None, as_json: bool) -> None:
    if event is None:
        if as_json:
            print(json.dumps({"event": None}, indent=2, ensure_ascii=False))
        else:
            print("No matching session memory found.")
        return

    if as_json:
        print(json.dumps(event, indent=2, ensure_ascii=False))
        return

    print("HAL Last Memory")
    print("===============")
    print()
    print(summarize_event(event))
    print()

    payload = event.get("payload", {})
    if isinstance(payload, dict):
        print("Payload")
        print("-------")
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def remember(note: str, repo: str | None, tag: str | None, as_json: bool) -> int:
    payload: dict[str, Any] = {"note": note}

    if tag:
        payload["tag"] = tag

    event = append_event("note", payload=payload, repo=repo, source="manual")

    if as_json:
        print(json.dumps(event, indent=2, ensure_ascii=False))
    else:
        print("Saved note to HAL Session Memory.")
        print(f"Path: {SESSION_PATH}")

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal session",
        description="Local HAL session memory.",
    )

    sub = parser.add_subparsers(dest="command")

    p_session = sub.add_parser("session", help="Show recent memory")
    p_session.add_argument("--limit", type=int, default=20)
    p_session.add_argument("--type", dest="event_type")
    p_session.add_argument("--repo")
    p_session.add_argument("--json", action="store_true")

    p_last = sub.add_parser("last", help="Show latest matching memory item")
    p_last.add_argument("--type", dest="event_type")
    p_last.add_argument("--repo")
    p_last.add_argument("--json", action="store_true")

    p_remember = sub.add_parser("remember", help="Save a manual note")
    p_remember.add_argument("note", nargs="+")
    p_remember.add_argument("--repo")
    p_remember.add_argument("--tag")
    p_remember.add_argument("--json", action="store_true")

    sub.add_parser("path", help="Print memory file path")

    args = parser.parse_args(argv)

    if args.command == "path":
        print(SESSION_PATH)
        return 0

    if args.command == "remember":
        return remember(" ".join(args.note), repo=args.repo, tag=args.tag, as_json=args.json)

    events = read_events()

    if args.command == "last":
        filtered = filter_events(events, event_type=args.event_type, repo=args.repo)
        render_last(filtered[-1] if filtered else None, as_json=args.json)
        return 0

    # "session" or bare call
    event_type = getattr(args, "event_type", None)
    repo = getattr(args, "repo", None)
    limit = getattr(args, "limit", 20)
    as_json = getattr(args, "json", False)

    filtered = filter_events(events, event_type=event_type, repo=repo)

    if as_json:
        print(json.dumps(filtered[-limit:], indent=2, ensure_ascii=False))
    else:
        render_events(filtered, limit=limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
