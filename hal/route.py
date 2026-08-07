#!/usr/bin/env python3
"""Read-only operator surface for mq-agent model routing."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    from hal.feedback import attach_feedback, make_next_action, render_feedback
except ModuleNotFoundError:  # run as a script: hal/ is on sys.path, the package is not
    from feedback import (  # type: ignore[no-redef, import-not-found]
        attach_feedback,
        make_next_action,
        render_feedback,
    )

SCHEMA = "mq_hal.model_route.v1"
DECISION_SCHEMA = "mq.model-route-decision.v1"
REPORT_SCHEMA = "mq.model-route-report.v1"
HISTORY_SCHEMA = "mq.model-route-history.v1"
HISTORY_LIMIT = 20
STATUSES = {"PASS", "WARN", "FAIL", "SKIPPED", "UNAVAILABLE"}
MODE_MAP = {
    "local-shadow": "SHADOW",
    "cloud-required": "CLOUD_REQUIRED",
    "approved-local": "APPROVED_LOCAL",
}
PROBE_TASK = "Inspect current MQ model routing status"
STATUS_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "model_route_status.schema.json"

SAMPLE_STATUS: dict[str, Any] = {
    "schema": SCHEMA, "title": "MQ Model Routing", "status": "PASS",
    "router": "PASS", "mode": "SHADOW", "ollama": "PASS",
    "local_model": "qwen3:4b-instruct", "authoritative_agent": "codex",
    "decision": {"recommended_route": "local-shadow"},
    "metrics": {
        "total_records": 38, "valid_outcomes": 38, "attempted": 38,
        "verified": 38, "accepted_by_agent": 29,
        "accepted_by_operator": 0, "escalated": 9,
    },
    "escalation_reasons": [],
}


def agent_binary() -> str | None:
    override = os.environ.get("MQ_AGENT_BIN", "").strip()
    if override:
        return override if Path(override).is_file() else None
    discovered = shutil.which("mq-agent")
    if discovered:
        return discovered
    local = Path.home() / "mq-agent" / ".venv" / "bin" / "mq-agent"
    return str(local) if local.is_file() else None


def run_agent(
    args: list[str], timeout: int = 20, *, allow_nonzero_json: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    binary = agent_binary()
    if binary is None:
        return None, "mq-agent-unavailable"
    try:
        result = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=timeout,
            check=False, shell=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
        return None, "mq-agent-unavailable"
    if result.returncode != 0 and not allow_nonzero_json:
        return None, "mq-agent-failed"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "mq-agent-invalid-json"
    return (payload, None) if isinstance(payload, dict) else (None, "mq-agent-invalid-output")


def inspect_decision(task: str, agent: str = "codex") -> tuple[dict[str, Any] | None, str | None]:
    decision, error = run_agent(["route", "inspect", task, "--agent", agent, "--json"])
    if error:
        return None, error
    if decision is None or decision.get("schema") != DECISION_SCHEMA:
        return None, "decision-contract-invalid"
    return decision, None


def report_data() -> tuple[dict[str, Any] | None, str | None]:
    report, error = run_agent(["route", "report", "--json"])
    if error:
        return None, error
    if report is None or report.get("schema") != REPORT_SCHEMA:
        return None, "report-contract-invalid"
    return report, None


def ollama_status(local_model: str | None) -> tuple[str, str | None]:
    runtime, error = run_agent(
        ["models", "doctor", "--no-smoke", "--json"], allow_nonzero_json=True,
    )
    if error or runtime is None:
        return "UNAVAILABLE", error or "ollama-runtime-invalid"
    installed = runtime.get("installed_models", [])
    items = runtime.get("items", [])
    available = any(
        isinstance(item, dict)
        and item.get("check") == "ollama-version"
        and item.get("status") == "PASS"
        for item in items if isinstance(items, list)
    )
    model_ready = local_model is None or local_model in installed
    return ("PASS", None) if available and model_ready else ("WARN", "ollama-or-model-unavailable")


def empty_metrics() -> dict[str, int]:
    return {
        "total_records": 0, "valid_outcomes": 0, "attempted": 0,
        "verified": 0, "accepted_by_agent": 0,
        "accepted_by_operator": 0, "escalated": 0,
    }


def metrics_from_report(report: dict[str, Any]) -> dict[str, int]:
    return {
        key: int(report.get(key, 0))
        for key in empty_metrics()
    }


def validate_status(payload: dict[str, Any]) -> None:
    """Validate the closed top-level status contract using its JSON Schema."""
    schema = json.loads(STATUS_SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema["properties"]
    required = set(schema["required"])
    if not required <= set(payload):
        raise ValueError("model route status missing required fields")
    if schema.get("additionalProperties") is False and set(payload) - set(properties):
        raise ValueError("model route status contains unknown fields")
    for key, rules in properties.items():
        if key not in payload:
            continue
        if "const" in rules and payload[key] != rules["const"]:
            raise ValueError(f"model route status invalid {key}")
        if "enum" in rules and payload[key] not in rules["enum"]:
            raise ValueError(f"model route status invalid {key}")


def validated_status(payload: dict[str, Any]) -> dict[str, Any]:
    validate_status(payload)
    return payload


def collect_status() -> dict[str, Any]:
    decision, decision_error = inspect_decision(PROBE_TASK)
    report, report_error = report_data()
    errors = [item for item in (decision_error, report_error) if item]
    if errors:
        payload = {
            "schema": SCHEMA, "title": "MQ Model Routing", "status": "WARN",
            "router": "UNAVAILABLE", "mode": "UNAVAILABLE", "ollama": "UNAVAILABLE",
            "local_model": None, "authoritative_agent": None, "decision": decision,
            "metrics": metrics_from_report(report) if report else empty_metrics(),
            "escalation_reasons": errors,
        }
        return validated_status(attach_feedback(
            payload, status="WARN", what="Model routing is unavailable",
            why="HAL cannot display authoritative routing state without valid mq-agent JSON",
            evidence=errors,
            next_action=make_next_action(
                text="Check mq-agent routing", command="mq-agent route inspect \"<task>\" --json",
                safety="read-only", requires_confirmation=False,
            ),
        ))
    assert decision is not None and report is not None
    route = str(decision.get("recommended_route", ""))
    local_model = decision.get("local_model")
    runtime_status, runtime_error = ollama_status(str(local_model) if local_model else None)
    overall_status = "PASS" if runtime_status == "PASS" else "WARN"
    payload = {
        "schema": SCHEMA, "title": "MQ Model Routing", "status": overall_status,
        "router": "PASS", "mode": MODE_MAP.get(route, "UNAVAILABLE"),
        "ollama": runtime_status,
        "local_model": local_model,
        "authoritative_agent": decision.get("authoritative_agent"),
        "decision": decision, "metrics": metrics_from_report(report),
        "escalation_reasons": (
            list(decision.get("escalation_conditions", []))
            + ([str(runtime_error)] if runtime_error else [])
        ),
    }
    return validated_status(attach_feedback(
        payload, status=overall_status,
        what="Model routing state loaded" if overall_status == "PASS" else "Model routing is degraded",
        why="HAL received valid decision and report contracts from mq-agent",
        evidence=[DECISION_SCHEMA, REPORT_SCHEMA, f"ollama: {runtime_status}"],
        next_action=None if overall_status == "PASS" else make_next_action(
            text="Inspect Ollama runtime", command="mq-agent models doctor --no-smoke --json",
            safety="read-only", requires_confirmation=False,
        ),
    ))


def collect_inspect(task: str, agent: str) -> dict[str, Any]:
    decision, error = inspect_decision(task, agent)
    status = "PASS" if decision else "WARN"
    payload = {
        "schema": "mq_hal.model_route_inspect.v1", "status": status,
        "task": task, "decision": decision, "error": error,
    }
    return attach_feedback(
        payload, status=status,
        what="Routing decision loaded" if decision else "Routing decision unavailable",
        why="The decision remains owned by mq-agent",
        evidence=[decision.get("decision_id", "") if decision else str(error)],
        next_action=None if decision else make_next_action(
            text="Check mq-agent routing", command=f"mq-agent route inspect {json.dumps(task)} --json",
            safety="read-only", requires_confirmation=False,
        ),
    )


def collect_accuracy() -> dict[str, Any]:
    report, error = report_data()
    if report is None:
        return attach_feedback(
            {"schema": "mq_hal.model_route_accuracy.v1", "status": "WARN",
             "verified_outcomes": 0, "by_task_class": {}, "error": error},
            status="WARN", what="Routing accuracy is unavailable",
            why="Only mq-agent verified outcomes may contribute to accuracy",
            evidence=[str(error)], next_action=make_next_action(
                text="Inspect routing report", command="mq-agent route report --json",
                safety="read-only", requires_confirmation=False,
            ),
        )
    classes: dict[str, Any] = {}
    raw_classes = report.get("by_task_class", {})
    if isinstance(raw_classes, dict):
        for name, values in raw_classes.items():
            if not isinstance(values, dict):
                continue
            verified = int(values.get("verified", 0))
            accepted = int(values.get("accepted_by_agent", 0))
            classes[str(name)] = {
                "verified": verified,
                "accepted_by_agent": accepted,
                "escalated": int(values.get("escalated", 0)),
                "acceptance_rate": round(accepted / verified, 4) if verified else None,
            }
    return attach_feedback(
        {"schema": "mq_hal.model_route_accuracy.v1", "status": "PASS",
         "verified_outcomes": int(report.get("verified", 0)), "by_task_class": classes,
         "error": None},
        status="PASS", what="Verified routing evidence loaded",
        why="Rates use verified outcomes only", evidence=[REPORT_SCHEMA],
    )


def history_schema(decision_id: str | None) -> str:
    return "mq_hal.model_route_explain.v1" if decision_id else "mq_hal.model_route_history.v1"


def history_data(decision_id: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    args = ["route", "history", "--limit", str(HISTORY_LIMIT)]
    if decision_id:
        args.extend(["--decision-id", decision_id])
    history, error = run_agent([*args, "--json"])
    if error:
        return None, error
    if history is None or history.get("schema") != HISTORY_SCHEMA:
        return None, "history-contract-invalid"
    if not isinstance(history.get("entries"), list):
        return None, "history-contract-invalid"
    return history, None


def unavailable_history(decision_id: str | None = None, error: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": history_schema(decision_id),
        "status": "WARN", "history": [],
        "reason": "verified-routing-history-unavailable",
    }
    if decision_id:
        payload["decision_id"] = decision_id
    return attach_feedback(
        payload, status="WARN", what="Verified routing history is unavailable",
        why="HAL does not read or create mq-agent history directly",
        evidence=[error or "mq-agent did not return the routing history contract"],
        next_action=make_next_action(
            text="Inspect routing history", command="mq-agent route history --json",
            safety="read-only", requires_confirmation=False,
        ),
    )


def collect_history(decision_id: str | None = None) -> dict[str, Any]:
    history, error = history_data(decision_id)
    if history is None:
        return unavailable_history(decision_id, error)
    entries = history["entries"]
    status = "PASS" if entries else "WARN"
    payload: dict[str, Any] = {
        "schema": history_schema(decision_id),
        "status": status, "history": entries,
        "matched": int(history.get("matched", len(entries))),
        "returned": int(history.get("returned", len(entries))),
    }
    if decision_id:
        payload["decision_id"] = decision_id
    if not entries:
        payload["reason"] = (
            "routing-decision-not-found" if decision_id else "no-verified-routing-history"
        )
        return attach_feedback(
            payload, status="WARN",
            what="No routing decision matches" if decision_id else "No routing outcomes recorded",
            why="HAL shows only outcomes mq-agent has recorded",
            evidence=[HISTORY_SCHEMA, f"source: {history.get('source', '-')}"],
            next_action=make_next_action(
                text="Run an advisory shadow route",
                command="mq-agent route shadow \"<task>\" --json",
                safety="local-write", requires_confirmation=True,
            ),
        )
    return attach_feedback(
        payload, status=status,
        what="Routing history loaded",
        why="Outcomes stay owned and recorded by mq-agent",
        evidence=[HISTORY_SCHEMA, f"{payload['returned']} of {payload['matched']} outcomes"],
    )


def render_status(data: dict[str, Any]) -> None:
    print("MQ Model Routing")
    print("================")
    print(f"Router:              {data['router']}")
    print(f"Mode:                {data['mode']}")
    print(f"Ollama:              {data['ollama']}")
    print(f"Local model:         {data['local_model'] or '-'}")
    print(f"Authoritative agent: {data['authoritative_agent'] or '-'}")
    metrics = data["metrics"]
    print(f"Verified outcomes:   {metrics['verified']}")
    print(f"Local accepted:      {metrics['accepted_by_agent']}")
    print(f"Escalated:           {metrics['escalated']}")
    print()
    render_feedback(data["feedback"])


def render_inspect(data: dict[str, Any]) -> None:
    decision = data.get("decision")
    if isinstance(decision, dict):
        print(f"Decision: {decision.get('decision_id', '-')}")
        print(f"Task class: {decision.get('task_class', '-')}")
        print(f"Risk: {decision.get('risk', '-')}")
        print(f"Route: {decision.get('recommended_route', '-')}")
        print("Reasons: " + ", ".join(decision.get("reason_codes", [])))
        print("Escalate: " + ", ".join(decision.get("escalation_conditions", [])))
    render_feedback(data["feedback"])


def render_history(data: dict[str, Any]) -> None:
    for entry in data["history"]:
        verification = entry.get("verification", {})
        print(f"{entry.get('recorded_at', '-')}  {entry.get('decision_id', '-')}")
        print(f"  run:          {entry.get('run_id', '-')}")
        print(f"  task class:   {entry.get('task_class', '-')}")
        print(f"  route:        {entry.get('selected_route', '-')}")
        print(
            "  stages:       "
            f"attempted={_flag(entry.get('attempted'))} "
            f"answered={_flag(entry.get('model_output_received'))} "
            f"schema-valid={_flag(entry.get('schema_valid'))} "
            f"verified={_flag(verification.get('status') == 'PASS')}"
        )
        print(f"  verification: {verification.get('status', '-')}")
        print(f"  escalation:   {entry.get('escalation_reason') or '-'}")
        print()
    print(f"Showing {data['returned']} of {data['matched']} outcomes")
    print()


def _flag(value: Any) -> str:
    return "yes" if value else "no"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal route", description="Read-only model routing control room")
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "inspect", "history", "accuracy", "explain"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "inspect":
        if not args.value:
            parser.error("inspect requires a task")
        data = collect_inspect(args.value, args.agent)
    elif args.command == "accuracy":
        data = collect_accuracy()
    elif args.command == "history":
        data = collect_history()
    elif args.command == "explain":
        if not args.value:
            parser.error("explain requires a decision id")
        data = collect_history(args.value)
    else:
        data = collect_status()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.command == "inspect":
        render_inspect(data)
    elif args.command in {"history", "explain", "accuracy"}:
        print(data["schema"])
        if args.command == "accuracy":
            print(f"Verified outcomes: {data['verified_outcomes']}")
            for name, values in data["by_task_class"].items():
                print(f"{name}: verified={values['verified']} acceptance={values['acceptance_rate']}")
        elif data["history"]:
            render_history(data)
        render_feedback(data["feedback"])
    else:
        render_status(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
