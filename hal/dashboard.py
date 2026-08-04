#!/usr/bin/env python3
"""Terminal dashboard for the mq-hal operator layer."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.append(str(BASE_DIR / "scripts"))

from hal.feedback import surface_feedback  # noqa: E402
from hal import brain as brain_control  # noqa: E402
from hal import context as context_control  # noqa: E402
from hal import release as release_control  # noqa: E402
from hal import route as route_control  # noqa: E402
from hal import runtime as runtime_control  # noqa: E402
from hal import stack as stack_control  # noqa: E402
from session_memory import read_events  # noqa: E402


SAMPLE_HISTORY: dict[str, Any] = {
    "events": [
        {"type": "brief", "repo": "mq-hal", "status": "healthy"},
        {"type": "fix_plan", "repo": "mq-hal", "status": "ready"},
        {"type": "note", "repo": "mq-hal", "status": "release looked good"},
    ],
    "summary": {"brief": 1, "fix_plan": 1, "note": 1},
}


def clear_screen(enabled: bool) -> None:
    if enabled and sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def status_rank(status: str) -> int:
    value = status.upper()
    if value in {"PASS", "OK", "READY", "RUNNING", "YES"}:
        return 0
    if value in {"WARN", "WARNING", "UNKNOWN", "NEEDS_REVIEW"}:
        return 1
    return 2


def worst_status(statuses: list[str], good: str = "PASS") -> str:
    if not statuses:
        return "UNKNOWN"
    worst = max(statuses, key=status_rank)
    if status_rank(worst) == 0:
        return good
    if status_rank(worst) == 1:
        return "WARN"
    return "FAIL"


def stack_data(sample: bool) -> dict[str, Any]:
    if sample:
        return surface_feedback(
            stack_control.SAMPLE_COCKPIT, surface="Stack", command="mq-hal stack"
        )
    result = stack_control.read_cockpit(timeout=8)
    if result.data is not None:
        return surface_feedback(result.data, surface="Stack", command="mq-hal stack")
    return surface_feedback({
        "title": "MQ Stack",
        "components": [{"name": "mq-agent", "status": "WARN", "detail": result.error}],
        "overall": {"status": "WARN", "score": 0, "total": 100},
    }, surface="Stack", command="mq-hal stack", status="UNAVAILABLE",
       evidence=[result.error])


def release_data(sample: bool) -> dict[str, Any]:
    if sample:
        return surface_feedback(
            release_control.SAMPLE, surface="Release", command="mq-hal release blockers"
        )
    data, error, code = release_control.read_release_check(timeout=8)
    if data is not None:
        return surface_feedback(data, surface="Release", command="mq-hal release blockers")
    return surface_feedback({
        "title": "Release Control Center",
        "repos": [],
        "overall": {"ready": False, "score": 0, "blockers": 1},
        "error": error,
        "returncode": code,
    }, surface="Release", command="mq-hal release blockers", status="UNAVAILABLE",
       evidence=[error])


def brain_data(sample: bool) -> dict[str, Any]:
    return surface_feedback(
        brain_control.SAMPLE, surface="Brain", command="mq-hal brain health"
    ) if sample else brain_control.collect()


def runtime_data(sample: bool) -> dict[str, Any]:
    return surface_feedback(
        runtime_control.SAMPLE_RUNTIME, surface="Runtime", command="mq-hal runtime services"
    ) if sample else runtime_control.collect_runtime()


def context_data(sample: bool) -> dict[str, Any]:
    if sample:
        return surface_feedback(
            context_control.SAMPLE, surface="Context", command="mq-hal context status"
        )
    # Keep the refresh loop cheap: skip the token-budget subprocess here. The
    # `mq-hal context budget` command runs it on demand.
    return context_control.collect(context_control.resolve_root(), run_budget=False)


def route_data(sample: bool) -> dict[str, Any]:
    if sample:
        return surface_feedback(
            route_control.SAMPLE_STATUS, surface="Model Routing", command="mq-hal route"
        )
    return route_control.collect_status()


def history_data(sample: bool) -> dict[str, Any]:
    if sample:
        return SAMPLE_HISTORY
    events = read_events()
    recent = events[-5:]
    summary = dict(Counter(str(event.get("type", "unknown")) for event in events))
    return {"events": recent, "summary": summary}


def collect_dashboard(sample: bool = False) -> dict[str, Any]:
    stack = stack_data(sample)
    release = release_data(sample)
    brain = brain_data(sample)
    runtime = runtime_data(sample)
    context = context_data(sample)
    route = route_data(sample)
    history = history_data(sample)
    alerts = build_alerts(stack, release, brain, runtime, context, route)
    return surface_feedback({
        "title": "HAL Operator Dashboard",
        "stack": stack,
        "release": release,
        "brain": brain,
        "runtime": runtime,
        "context": context,
        "route": route,
        "history": history,
        "alerts": alerts,
    }, surface="Dashboard", command="mq-hal next",
       status="WARN" if alerts else "PASS", evidence=[f"{len(alerts)} active alerts"])


def stack_summary(data: dict[str, Any]) -> tuple[str, str]:
    items = stack_control._items(data)
    statuses = [stack_control._status(item) for item in items]
    status = worst_status(statuses, good="PASS")
    overall = stack_control._overall(data)
    return status, overall


def release_summary(data: dict[str, Any]) -> tuple[str, str]:
    blockers = release_control.all_blockers(data)
    overall = data.get("overall")
    score = "-"
    if isinstance(overall, dict):
        score = str(overall.get("score", "-"))
    return ("WARN" if blockers else "PASS"), f"score={score} blockers={len(blockers)}"


def brain_summary(data: dict[str, Any]) -> tuple[str, str]:
    status = str(data.get("status", "unknown")).upper()
    folders = data.get("folders", {})
    count = 0
    if isinstance(folders, dict):
        count = sum(int(meta.get("count", 0)) for meta in folders.values() if isinstance(meta, dict))
    return ("PASS" if status == "OK" else "WARN"), f"{count} files"


def runtime_summary(data: dict[str, Any]) -> tuple[str, str]:
    overall = data.get("overall", {})
    if isinstance(overall, dict):
        status = str(overall.get("status", "UNKNOWN"))
        return status, (
            f"{overall.get('running', 0)} running, "
            f"{overall.get('warn', 0)} warn, {overall.get('down', 0)} down"
        )
    return "UNKNOWN", "-"


def history_summary(data: dict[str, Any]) -> tuple[str, str]:
    events = data.get("events", [])
    summary = data.get("summary", {})
    total = len(events) if isinstance(events, list) else 0
    kinds = len(summary) if isinstance(summary, dict) else 0
    return "PASS", f"{total} recent, {kinds} types"


def context_summary(data: dict[str, Any]) -> tuple[str, str]:
    status = str(data.get("status", "UNKNOWN")).upper()
    budget = data.get("token_budget", {})
    budget_status = str(budget.get("status", "UNKNOWN")).lower() if isinstance(budget, dict) else "unknown"
    pack = "found" if data.get("latest_task_pack") else "missing"
    return status, f"budget={budget_status} pack={pack}"


def route_summary(data: dict[str, Any]) -> tuple[str, str]:
    return str(data.get("status", "WARN")), (
        f"mode={data.get('mode', '-')} verified={data.get('metrics', {}).get('verified', 0)}"
    )


def build_alerts(
    stack: dict[str, Any],
    release: dict[str, Any],
    brain: dict[str, Any],
    runtime: dict[str, Any],
    context: dict[str, Any],
    route: dict[str, Any],
) -> list[str]:
    alerts: list[str] = []
    for name, status, detail in dashboard_rows(
        stack, release, brain, runtime, context, route, {"events": [], "summary": {}}
    ):
        if status_rank(status) > 0:
            alerts.append(f"{name}: {status} {detail}")
    blockers = release_control.all_blockers(release)
    for blocker in blockers[:5]:
        alerts.append(f"Release blocker: {blocker['repo']} {blocker['blocker']}")
    return alerts


def dashboard_rows(
    stack: dict[str, Any],
    release: dict[str, Any],
    brain: dict[str, Any],
    runtime: dict[str, Any],
    context: dict[str, Any],
    route: dict[str, Any],
    history: dict[str, Any],
) -> list[tuple[str, str, str]]:
    stack_status, stack_detail = stack_summary(stack)
    release_status, release_detail = release_summary(release)
    brain_status, brain_detail = brain_summary(brain)
    runtime_status, runtime_detail = runtime_summary(runtime)
    history_status, history_detail = history_summary(history)
    context_status, context_detail = context_summary(context)
    route_status, route_detail = route_summary(route)
    return [
        ("Stack", stack_status, stack_detail),
        ("Brain", brain_status, brain_detail),
        ("Release", release_status, release_detail),
        ("Runtime", runtime_status, runtime_detail),
        ("History", history_status, history_detail),
        ("Context", context_status, context_detail),
        ("Routing", route_status, route_detail),
    ]


def render_home(data: dict[str, Any], feedback_status: str = "ready") -> None:
    rows = dashboard_rows(
        data["stack"],
        data["release"],
        data["brain"],
        data["runtime"],
        data["context"],
        data["route"],
        data["history"],
    )
    print("+------------------------------+")
    print("| HAL Operator Dashboard       |")
    print("+------------------------------+")
    print()
    for index, (name, status, detail) in enumerate(rows, start=1):
        print(f"{index} {name:<8} {status:<7} {detail}")
    print(f"A Alerts   {len(data.get('alerts', []))}")
    print()
    print("Keys: 1 Stack  2 Brain  3 Release  4 Runtime  5 History  6 Context  7 Routing")
    print("      a Alerts  r Refresh  q Exit")
    print()
    print(f"Status: {feedback_status}")


def render_stack(data: dict[str, Any]) -> None:
    stack_control.render(data)


def render_brain(data: dict[str, Any]) -> None:
    brain_control.render_summary(data)


def render_release(data: dict[str, Any]) -> None:
    release_control.render_summary(data)


def render_runtime(data: dict[str, Any]) -> None:
    runtime_control.render_runtime(data, details=True)


def render_context(data: dict[str, Any]) -> None:
    context_control.render_status(data)


def render_route(data: dict[str, Any]) -> None:
    route_control.render_status(data)


def render_history(data: dict[str, Any]) -> None:
    print("History")
    print("=======")
    print()
    events = data.get("events", [])
    if not isinstance(events, list) or not events:
        print("No recent history.")
        return
    for event in events[-10:]:
        event_type = str(event.get("type", "-"))[:16]
        repo = str(event.get("repo", "-"))[:16]
        payload = event.get("payload", {})
        payload_status = payload.get("status", "-") if isinstance(payload, dict) else "-"
        status = str(event.get("status") or payload_status)[:50]
        print(f"{event_type:<16} {repo:<16} {status}")


def render_alerts(data: dict[str, Any]) -> None:
    print("Alerts")
    print("======")
    print()
    alerts = data.get("alerts", [])
    if not alerts:
        print("No alerts.")
        return
    for alert in alerts:
        print(f"- {alert}")


def render_panel(data: dict[str, Any], key: str, feedback: str = "") -> None:
    if key == "1":
        render_stack(data["stack"])
    elif key == "2":
        render_brain(data["brain"])
    elif key == "3":
        render_release(data["release"])
    elif key == "4":
        render_runtime(data["runtime"])
    elif key == "5":
        render_history(data["history"])
    elif key == "6":
        render_context(data["context"])
    elif key == "7":
        render_route(data["route"])
    elif key.lower() == "a":
        render_alerts(data)
    else:
        render_home(data, feedback or "ready")


def run_loop(sample: bool, once: bool, no_clear: bool) -> int:
    selected = "home"
    feedback = ""
    while True:
        data = collect_dashboard(sample=sample)
        clear_screen(not no_clear)
        current_feedback = feedback
        feedback = ""
        render_panel(data, selected, current_feedback)
        if selected != "home":
            print()
            print("Keys: b Back  r Refresh  q Exit")
        if current_feedback and selected != "home":
            print()
            print(f"Status: {current_feedback}")
        if once:
            return 0
        print()
        try:
            choice = input("mq-hal dashboard> ").strip() or "home"
        except EOFError:
            print()
            return 0
        if choice.lower() in {"q", "quit", "exit"}:
            print("Status: Dashboard closed.")
            return 0
        if choice.lower() in {"r", "refresh"}:
            selected = "home"
            feedback = "Dashboard refreshed."
        elif choice.lower() in {"b", "back"}:
            selected = "home"
            feedback = "Back to dashboard."
        elif choice in {"1", "2", "3", "4", "5", "6", "7"} or choice.lower() == "a":
            selected = choice
            panel_names = {
                "1": "Stack",
                "2": "Brain",
                "3": "Release",
                "4": "Runtime",
                "5": "History",
                "6": "Context",
                "7": "Routing",
                "a": "Alerts",
            }
            feedback = f"Opened {panel_names[choice.lower()]}."
        else:
            selected = "home"
            feedback = f"Unknown choice {choice!r}. Use 1-7, a, b, r, or q."


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal dashboard",
        description="Open the HAL operator dashboard.",
    )
    parser.add_argument("--json", action="store_true", help="Print dashboard JSON")
    parser.add_argument("--sample", action="store_true", help="Use sample data")
    parser.add_argument("--once", action="store_true", help="Render once and exit")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal")
    args = parser.parse_args(argv)

    if args.json:
        print(json.dumps(collect_dashboard(sample=args.sample), indent=2, ensure_ascii=False))
        return 0

    return run_loop(sample=args.sample, once=args.once, no_clear=args.no_clear)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
