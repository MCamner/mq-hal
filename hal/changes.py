#!/usr/bin/env python3
"""Compare two HAL checks: what is new, resolved, persisting, or unverified."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from hal.feedback import (  # noqa: E402
    attach_feedback,
    make_next_action,
    normalize_status,
)
from hal import release as release_control  # noqa: E402
from hal import stack as stack_control  # noqa: E402

SCHEMA = "mq_hal.changes.v1"
SNAPSHOT_SCHEMA = "mq_hal.changes_snapshot.v1"
STATE_DIR = Path(
    os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
).expanduser()
KEEP_SNAPSHOTS = 20

PROBLEMS = {"WARN", "UNAVAILABLE", "FAIL"}
RANKS = {"PASS": 0, "SKIPPED": 1, "WARN": 2, "UNAVAILABLE": 3, "FAIL": 4}

SURFACE_SOURCES = {
    "stack": "mq-agent stack cockpit",
    "release": "mq-agent stack release-check",
    "brain": "mq-hal brain",
    "runtime": "mq-hal runtime",
    "context": "mq-hal context",
    "route": "mq-agent route status",
}
# Read-only follow-up per check prefix. Never executed by this command.
NEXT_COMMANDS = {
    "stack": "mq-hal stack",
    "release": "mq-hal release blockers",
    "brain": "mq-hal brain health",
    "runtime": "mq-hal runtime services",
    "context": "mq-hal context status",
    "route": "mq-hal route",
}

SAMPLE_PREVIOUS: dict[str, Any] = {
    "schema": SNAPSHOT_SCHEMA,
    "taken_at": "2026-06-11T08:00:00+00:00",
    "source": "sample",
    "checks": [
        {"id": "stack:mq-mcp:status", "status": "FAIL", "detail": "status=FAIL",
         "source": "mq-agent stack cockpit"},
        {"id": "runtime:GitHub:auth", "status": "PASS", "detail": "authenticated",
         "source": "mq-hal runtime"},
        {"id": "stack:mqobsidian:status", "status": "WARN", "detail": "status=WARN",
         "source": "mq-agent stack cockpit"},
    ],
}


def _check(check_id: str, status: Any, detail: Any, source: str) -> dict[str, str]:
    return {
        "id": check_id,
        "status": normalize_status(status),
        "detail": str(detail or "").strip(),
        "source": source,
    }


def extract_checks(dashboard: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten dashboard payloads into checks keyed by stable IDs."""
    checks: list[dict[str, str]] = []
    for surface, source in SURFACE_SOURCES.items():
        data = dashboard.get(surface)
        if not isinstance(data, dict):
            continue
        feedback = data.get("feedback")
        what = feedback.get("what_happened") if isinstance(feedback, dict) else ""
        status = normalize_status(data.get("status"))
        checks.append(_check(f"surface:{surface}", status, what, source))
        # An unavailable surface carries placeholder items; recording them
        # would turn missing data into fake per-component statuses.
        if status == "UNAVAILABLE":
            continue
        if surface == "stack":
            checks.extend(_stack_checks(data, source))
        elif surface == "release":
            checks.extend(_release_checks(data, source))
        elif surface == "runtime":
            checks.extend(_runtime_checks(data, source))
    return checks


def _stack_checks(data: dict[str, Any], source: str) -> list[dict[str, str]]:
    out = []
    for item in stack_control._items(data):
        name = stack_control._name(item)
        for key in ("gate", "contract", "status"):
            value = stack_control._clean(item.get(key))
            if value:
                out.append(_check(f"stack:{name}:{key}", value, f"{key}={value}", source))
    return out


def _release_checks(data: dict[str, Any], source: str) -> list[dict[str, str]]:
    out = []
    for item in release_control.repos(data):
        name = release_control.repo_name(item)
        blockers = release_control.blockers(item)
        warnings = item.get("warnings") if isinstance(item.get("warnings"), list) else []
        if blockers:
            status, detail = "FAIL", "; ".join(blockers)
        elif warnings:
            status, detail = "WARN", "; ".join(str(w) for w in warnings)
        else:
            status, detail = "PASS", "no blockers"
        out.append(_check(f"release:{name}", status, detail, source))
        for gate in release_control.gates(item):
            gate_name = gate.get("name") or gate.get("gate")
            if gate_name:
                out.append(_check(
                    f"release:{name}:gate:{gate_name}", gate.get("status"),
                    gate.get("detail", ""), source,
                ))
    return out


def _runtime_checks(data: dict[str, Any], source: str) -> list[dict[str, str]]:
    out = []
    services = data.get("services")
    for service in services if isinstance(services, list) else []:
        if not isinstance(service, dict) or not service.get("name"):
            continue
        name = service["name"]
        out.append(_check(f"runtime:{name}", service.get("status"), service.get("detail"), source))
        checks = service.get("checks")
        for check in checks if isinstance(checks, list) else []:
            if isinstance(check, dict) and check.get("name"):
                out.append(_check(
                    f"runtime:{name}:{check['name']}", check.get("status"),
                    check.get("detail"), source,
                ))
    return out


def make_snapshot(checks: list[dict[str, str]], source: str) -> dict[str, Any]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "checks": sorted(checks, key=lambda item: item["id"]),
    }


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read snapshot {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError(f"{path} is not a {SNAPSHOT_SCHEMA} snapshot")
    checks = data.get("checks")
    if not isinstance(checks, list) or not all(
        isinstance(item, dict) and isinstance(item.get("id"), str) for item in checks
    ):
        raise ValueError(f"{path} has malformed checks")
    return data


def snapshot_dir() -> Path:
    return STATE_DIR / "changes"


def latest_snapshot_path() -> Path | None:
    files = sorted(snapshot_dir().glob("snapshot-*.json"))
    return files[-1] if files else None


def save_snapshot(snapshot: dict[str, Any]) -> Path:
    directory = snapshot_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"snapshot-{stamp}.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for old in sorted(directory.glob("snapshot-*.json"))[:-KEEP_SNAPSHOTS]:
        old.unlink()
    return path


def _row(current: dict[str, Any], previous: dict[str, Any] | None, **extra: Any) -> dict[str, Any]:
    return {
        "id": current["id"],
        "status": normalize_status(current.get("status")),
        "previous_status": normalize_status(previous.get("status")) if previous else None,
        "detail": str(current.get("detail") or ""),
        "source": str(current.get("source") or ""),
        **extra,
    }


def compare(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Classify each check ID. Absent or skipped data never counts as resolved."""
    before = {item["id"]: item for item in previous.get("checks", [])}
    after = {item["id"]: item for item in current.get("checks", [])}
    result: dict[str, list[dict[str, Any]]] = {
        "new": [], "resolved": [], "persisting": [], "unverified": [],
    }
    for check_id in sorted(set(before) | set(after)):
        prev, cur = before.get(check_id), after.get(check_id)
        prev_status = normalize_status(prev.get("status")) if prev else None
        prev_problem = prev_status in PROBLEMS
        cur_status = normalize_status(cur.get("status")) if cur else None

        if cur is None or cur_status == "SKIPPED":
            if prev is not None and prev_problem:
                reason = "missing from current check" if cur is None else "skipped in current check"
                row = _row(prev, prev, reason=reason)
                row["status"] = cur_status or "UNAVAILABLE"
                result["unverified"].append(row)
            continue

        if cur_status in PROBLEMS:
            if prev_problem and RANKS[cur_status] <= RANKS.get(prev_status or "", 0):
                result["persisting"].append(_row(cur, prev))
            else:
                result["new"].append(_row(cur, prev))
        elif prev_problem:
            result["resolved"].append(_row(cur, prev))
    return result


def _next_command(check_id: str) -> str:
    parts = check_id.split(":")
    prefix = parts[1] if parts[0] == "surface" and len(parts) > 1 else parts[0]
    return NEXT_COMMANDS.get(prefix, "mq-hal dashboard")


def build_report(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    meta = lambda snap: {"taken_at": snap.get("taken_at"), "source": snap.get("source")}  # noqa: E731
    if previous is None:
        payload: dict[str, Any] = {
            "schema": SCHEMA, "previous": None, "current": meta(current),
            "new": [], "resolved": [], "persisting": [], "unverified": [],
        }
        return attach_feedback(
            payload, status="SKIPPED",
            what="No previous snapshot; baseline recorded",
            why="Changes can only be reported once two checks exist",
            evidence=[f"{len(current.get('checks', []))} checks in baseline"],
        )

    diff = compare(previous, current)
    payload = {"schema": SCHEMA, "previous": meta(previous), "current": meta(current), **diff}
    counts = {key: len(value) for key, value in diff.items()}
    evidence = [f"{key}={value}" for key, value in counts.items()]
    evidence.append(f"previous={previous.get('taken_at')} current={current.get('taken_at')}")

    action = None
    if diff["new"]:
        worst = max(diff["new"], key=lambda item: RANKS[item["status"]])
        status = worst["status"]
        action = make_next_action(
            text=f"Inspect {worst['id']}", command=_next_command(worst["id"]),
            safety="read-only", requires_confirmation=False,
        )
    elif diff["unverified"] or diff["persisting"]:
        status = "WARN"
        pool = diff["unverified"] or diff["persisting"]
        field = "previous_status" if diff["unverified"] else "status"
        target = max(pool, key=lambda item: RANKS.get(item[field] or "", 0))["id"]
        action = make_next_action(
            text=f"Re-check {target}", command=_next_command(target),
            safety="read-only", requires_confirmation=False,
        )
    else:
        status = "PASS"

    return attach_feedback(
        payload, status=status,
        what=(
            f"{counts['new']} new, {counts['resolved']} resolved, "
            f"{counts['persisting']} persisting, {counts['unverified']} unverified"
        ),
        why=(
            "New problems appeared since the previous check" if diff["new"]
            else "Missing data is not treated as a fix" if diff["unverified"]
            else "Known problems remain open" if diff["persisting"]
            else "Nothing degraded since the previous check"
        ),
        evidence=evidence,
        next_action=action,
    )


def render(report: dict[str, Any]) -> None:
    print("HAL Changes")
    print("===========")
    for label in ("previous", "current"):
        snap = report.get(label)
        if snap:
            print(f"{label.capitalize() + ':':<10}{snap.get('taken_at')}  ({snap.get('source')})")
        else:
            print(f"{label.capitalize() + ':':<10}none")
    print()

    sections = (
        ("new", "NEW"),
        ("resolved", "RESOLVED"),
        ("persisting", "PERSISTING"),
        ("unverified", "UNVERIFIED (no current data, not counted as resolved)"),
    )
    for key, title in sections:
        rows = report.get(key) or []
        if not rows:
            continue
        print(title)
        for row in rows:
            change = f"{row['previous_status'] or 'NONE'} -> {row['status']}"
            detail = row.get("reason") or row.get("detail") or ""
            line = f"{row['status']:<5} {row['id']}  {change}"
            if detail:
                line += f"  {detail}"
            print(f"{line}  [{row['source']}]")
        print()

    feedback = report["feedback"]
    print(f"{feedback['status']}: {feedback['what_happened']}")
    action = feedback.get("next_action")
    if action:
        print()
        print("Next check:")
        print(action["command"])


def collect_current(sample: bool) -> dict[str, Any]:
    from hal import dashboard as dashboard_control

    data = dashboard_control.collect_dashboard(sample=sample)
    return make_snapshot(extract_checks(data), "sample" if sample else "mq-hal dashboard")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal changes",
        description="Show what is new, resolved, or still failing since the previous check.",
    )
    parser.add_argument("--since", default="last",
                        help="'last' (latest saved snapshot) or a snapshot file path")
    parser.add_argument("--current", help="Use a snapshot file instead of running checks")
    parser.add_argument("--no-save", action="store_true", help="Do not save the current snapshot")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.sample:
            previous: dict[str, Any] | None = SAMPLE_PREVIOUS
            current = collect_current(sample=True)
        else:
            current = (load_snapshot(Path(args.current).expanduser()) if args.current
                       else collect_current(sample=False))
            if args.since == "last":
                last = latest_snapshot_path()
                previous = load_snapshot(last) if last else None
            else:
                previous = load_snapshot(Path(args.since).expanduser())
    except ValueError as exc:
        print(f"mq-hal changes: {exc}", file=sys.stderr)
        return 2

    report = build_report(previous, current)
    if not args.sample and not args.no_save:
        save_snapshot(current)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        render(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
