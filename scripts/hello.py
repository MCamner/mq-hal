#!/usr/bin/env python3
"""mq-hal hello: HAL greeting and quick status screen."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = Path(
    os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
).expanduser()
STATE_PATH = STATE_DIR / "state.json"

sys.path.insert(0, str(Path(__file__).parent))
from session_memory import filter_events, read_events  # noqa: E402

SAMPLE: dict[str, Any] = {
    "active_repo": "mq-hal",
    "version": "0.12.0",
    "memory_brief": (
        "memory: missing-vector-store  mq-agent=ok  repo-signal=ok"
    ),
    "recent_events": [
        {
            "timestamp": "2026-05-29T13:45:00",
            "type": "brief",
            "repo": "mq-hal",
            "status": "healthy",
        },
        {
            "timestamp": "2026-05-29T13:40:00",
            "type": "note",
            "repo": "mq-hal",
            "status": "Release looked good.",
        },
    ],
    "session_summary": {"brief": 1, "note": 1},
}


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return (r.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def _parse_time(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(value)[:16]


def _event_status(event: dict[str, Any]) -> str:
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        return "-"
    if event.get("type") == "doctor_summary":
        s = payload.get("summary", {})
        return str(s.get("status", "-")) if isinstance(s, dict) else "-"
    if event.get("type") == "note":
        return str(payload.get("note", "-"))[:50]
    return str(payload.get("status") or payload.get("message") or "-")


def collect() -> dict[str, Any]:
    state: dict[str, Any] = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    active_repo = str(state.get("active_repo", "-"))

    version = "-"
    try:
        version = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        pass

    halbin = str(BASE_DIR / "bin" / "mq-hal")
    memory_brief = _run([halbin, "memory-status", "--brief"])

    events = read_events()
    recent_raw = list(reversed(events))[:5]
    recent_events = [
        {
            "timestamp": _parse_time(e.get("timestamp")),
            "type": str(e.get("type", "-"))[:14],
            "repo": str(e.get("repo") or "-")[:14],
            "status": _event_status(e)[:50],
        }
        for e in recent_raw
    ]
    session_summary = dict(
        sorted(Counter(str(e.get("type", "unknown")) for e in events).items())
    )

    return {
        "active_repo": active_repo,
        "version": version,
        "memory_brief": memory_brief,
        "recent_events": recent_events,
        "session_summary": session_summary,
    }


def render(data: dict[str, Any]) -> None:
    print("HAL")
    print("===")
    print()
    print(f"Active repo:  {data['active_repo']}")
    print(f"Version:      {data['version']}")
    print()

    if data.get("memory_brief"):
        print(f"Memory:       {data['memory_brief']}")
        print()

    recent = data.get("recent_events", [])
    if recent:
        print("Recent session")
        print("--------------")
        for e in recent:
            print(
                f"  {e['timestamp']:16}  {e['type']:<14}  "
                f"{e['repo']:<14}  {e['status']}"
            )
        print()

    summary = data.get("session_summary", {})
    if isinstance(summary, dict) and summary:
        print("Session summary")
        print("---------------")
        for event_type, count in sorted(summary.items()):
            print(f"  {event_type:<20} {count}")
        print()

    print("Commands")
    print("--------")
    cmds = [
        ("brief", "repo status snapshot"),
        ("doctor-summary", "local health summary"),
        ("release-brief", "release readiness check"),
        ("timeline", "full session history"),
        ("memory-status", "semantic memory state"),
        ("agent-brief", "mq-agent summary"),
        ("stack-status", "full stack overview"),
    ]
    for cmd, desc in cmds:
        print(f"  {cmd:<20}  {desc}")
    print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal hello",
        description="HAL greeting and quick status screen.",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Print sample output without reading local state",
    )
    args = parser.parse_args(argv)

    data = SAMPLE if args.sample else collect()

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
