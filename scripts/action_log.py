#!/usr/bin/env python3
"""mq-hal actions: append-only local ledger of commands HAL ran or refused."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from learn import _redact_simple

ENTRY_SCHEMA = "mq_hal.action.v1"
REPORT_SCHEMA = "mq_hal.actions.v1"
MAX_ENTRIES = 1000
OUTCOMES = ("executed", "cancelled", "refused", "internal", "error")


def ledger_path() -> Path:
    state_dir = Path(
        os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
    ).expanduser()
    return state_dir / "actions.jsonl"


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_simple(value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def record_action(
    *,
    source: str,
    outcome: str,
    exit_code: int | None,
    command: list[str] | None = None,
    cwd: str | None = None,
    confirmation: str = "not_required",
    duration_ms: int | None = None,
    intent: str | None = None,
    repo: str | None = None,
    routing: str | None = None,
    prompt: str | None = None,
) -> None:
    """Append one entry. Never raises: a ledger failure must not block HAL."""
    entry = {
        "schema": ENTRY_SCHEMA,
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": source,
        "intent": intent,
        "repo": repo,
        "routing": routing,
        "prompt": _redact(prompt),
        "command": _redact(list(command)) if command is not None else None,
        "cwd": cwd,
        "confirmation": confirmation,
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
    }
    path = ledger_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_ENTRIES:
            tmp = path.with_suffix(".jsonl.tmp")
            tmp.write_text("\n".join(lines[-MAX_ENTRIES:]) + "\n", encoding="utf-8")
            tmp.replace(path)
    except OSError as exc:
        print(f"WARN: action ledger not written: {exc}", file=sys.stderr)


def load_actions() -> list[dict[str, Any]]:
    path = ledger_path()
    if not path.is_file():
        return []
    actions: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("schema") == ENTRY_SCHEMA:
            actions.append(item)
    return actions


def _command_text(entry: dict[str, Any]) -> str:
    command = entry.get("command")
    if isinstance(command, list) and command:
        return " ".join(str(part) for part in command)
    return "-"


def render(actions: list[dict[str, Any]], total: int) -> None:
    if not actions:
        print("No recorded actions.")
        print(f"Ledger: {ledger_path()}")
        return
    print("Recorded actions")
    print("================")
    print()
    for entry in actions:
        code = entry.get("exit_code")
        code_text = "-" if code is None else str(code)
        label = entry.get("intent") or entry.get("source") or "-"
        print(
            f"{entry.get('ts', '-'):25}  {str(entry.get('outcome', '-')).upper():9}  "
            f"exit {code_text:>3}  {entry.get('source', '-'):8}  {label}"
        )
        print(f"{'':27}repo: {entry.get('repo') or '-'}  command: {_command_text(entry)}")
    print()
    print(f"Showing {len(actions)} of {total}. Ledger: {ledger_path()}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal actions",
        description="Show what mq-hal ran, cancelled or refused (read-only).",
    )
    parser.add_argument("--last", type=int, default=20, help="Number of entries (default 20)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--source", choices=["router", "execute", "open", "fix"])
    parser.add_argument("--outcome", choices=OUTCOMES)
    args = parser.parse_args(argv)

    actions = load_actions()
    if args.repo:
        actions = [a for a in actions if a.get("repo") == args.repo]
    if args.source:
        actions = [a for a in actions if a.get("source") == args.source]
    if args.outcome:
        actions = [a for a in actions if a.get("outcome") == args.outcome]
    total = len(actions)
    shown = actions[-args.last:] if args.last > 0 else []

    if args.json:
        print(json.dumps(
            {
                "schema": REPORT_SCHEMA,
                "ledger": str(ledger_path()),
                "count": len(shown),
                "total": total,
                "actions": shown,
            },
            indent=2,
            ensure_ascii=False,
        ))
        return 0
    render(shown, total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
