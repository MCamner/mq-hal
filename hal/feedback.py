"""Shared, advisory operator feedback contract for mq-hal surfaces."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA = "mq.feedback.v1"
STATUSES = {"PASS", "WARN", "FAIL", "SKIPPED", "UNAVAILABLE"}
SAFETY_CLASSES = {"read-only", "local-process", "local-write", "destructive"}

STATUS_ALIASES = {
    "OK": "PASS",
    "READY": "PASS",
    "RUNNING": "PASS",
    "YES": "PASS",
    "WARNING": "WARN",
    "NEEDS_REVIEW": "WARN",
    "ERROR": "FAIL",
    "FAILED": "FAIL",
    "DOWN": "FAIL",
    "CANCELLED": "SKIPPED",
    "CANCELED": "SKIPPED",
    "UNKNOWN": "UNAVAILABLE",
    "MISSING": "UNAVAILABLE",
    "MISS": "UNAVAILABLE",
}


class FeedbackError(ValueError):
    """Raised when feedback violates the shared contract."""


def normalize_status(value: Any) -> str:
    status = str(value or "UNAVAILABLE").strip().upper()
    status = STATUS_ALIASES.get(status, status)
    return status if status in STATUSES else "UNAVAILABLE"


def normalize_statuses(value: Any) -> Any:
    """Copy a payload and normalize fields explicitly named ``status``."""
    if isinstance(value, dict):
        return {
            key: normalize_status(item) if key == "status" else normalize_statuses(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_statuses(item) for item in value]
    return deepcopy(value)


def make_next_action(
    *, text: str, command: str, safety: str,
    requires_confirmation: bool,
) -> dict[str, Any]:
    action = {
        "text": text.strip(),
        "command": command.strip(),
        "safety": safety,
        "requires_confirmation": bool(requires_confirmation),
    }
    if not action["text"] or not action["command"]:
        raise FeedbackError("next_action text and command must not be empty")
    if safety not in SAFETY_CLASSES:
        raise FeedbackError(f"unknown safety class: {safety}")
    if safety in {"local-write", "destructive"} and not requires_confirmation:
        raise FeedbackError(f"{safety} actions require confirmation")
    return action


def make_feedback(
    *, status: Any, what: str, why: str, evidence: list[str],
    next_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feedback = {
        "schema": SCHEMA,
        "status": normalize_status(status),
        "what_happened": what.strip(),
        "why_it_matters": why.strip(),
        "evidence": [str(item).strip() for item in evidence if str(item).strip()],
        "next_action": next_action,
    }
    validate_feedback(feedback)
    return feedback


def validate_feedback(feedback: dict[str, Any]) -> None:
    required = {
        "schema", "status", "what_happened", "why_it_matters", "evidence",
        "next_action",
    }
    if set(feedback) != required or feedback.get("schema") != SCHEMA:
        raise FeedbackError("malformed feedback object")
    if feedback.get("status") not in STATUSES:
        raise FeedbackError("invalid feedback status")
    if not feedback.get("what_happened") or not feedback.get("why_it_matters"):
        raise FeedbackError("feedback explanation must not be empty")
    evidence = feedback.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x for x in evidence):
        raise FeedbackError("feedback evidence must be a non-empty string array")
    action = feedback.get("next_action")
    if action is None:
        return
    if not isinstance(action, dict):
        raise FeedbackError("next_action must be an object or null")
    expected = {"text", "command", "safety", "requires_confirmation"}
    if set(action) != expected:
        raise FeedbackError("malformed next_action")
    make_next_action(**action)


def attach_feedback(
    payload: dict[str, Any], *, what: str, why: str, evidence: list[str],
    next_action: dict[str, Any] | None = None, status: Any | None = None,
) -> dict[str, Any]:
    normalized = normalize_statuses(payload)
    resolved = normalize_status(status if status is not None else normalized.get("status"))
    normalized["status"] = resolved
    normalized["feedback"] = make_feedback(
        status=resolved,
        what=what,
        why=why,
        evidence=evidence,
        next_action=next_action if resolved != "PASS" else None,
    )
    return normalized


def payload_status(payload: dict[str, Any]) -> str:
    """Return the worst normalized status found in a payload."""
    ranks = {"PASS": 0, "SKIPPED": 1, "WARN": 2, "UNAVAILABLE": 3, "FAIL": 4}
    found: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "status":
                    found.append(normalize_status(item))
                elif key != "feedback":
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return max(found, key=lambda item: ranks[item]) if found else "PASS"


def surface_feedback(
    payload: dict[str, Any], *, surface: str, command: str,
    status: Any | None = None, evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize a control-center payload and add advisory feedback."""
    resolved = normalize_status(status) if status is not None else payload_status(payload)
    action = None
    if resolved != "PASS":
        action = make_next_action(
            text=f"Inspect {surface} details",
            command=command,
            safety="read-only",
            requires_confirmation=False,
        )
    return attach_feedback(
        payload,
        status=resolved,
        what=(f"{surface} is healthy" if resolved == "PASS" else f"{surface} needs attention"),
        why=(
            "No operator intervention is required"
            if resolved == "PASS"
            else "A degraded or failed dependency can limit the operator view"
        ),
        evidence=evidence or [f"normalized status: {resolved}"],
        next_action=action,
    )


def execution_feedback(returncode: int, operation: str) -> dict[str, Any]:
    if returncode == 0:
        return make_feedback(
            status="PASS", what=f"{operation} completed",
            why="The delegated command exited successfully",
            evidence=["exit status 0"],
        )
    if returncode == 130:
        return make_feedback(
            status="SKIPPED", what=f"{operation} was cancelled",
            why="The operator declined or interrupted the action",
            evidence=["exit status 130"],
        )
    return make_feedback(
        status="FAIL", what=f"{operation} failed",
        why="The delegated command returned a non-zero exit status",
        evidence=[f"exit status {returncode}"],
    )


def render_feedback(feedback: dict[str, Any]) -> None:
    validate_feedback(feedback)
    print(f"{feedback['status']}: {feedback['what_happened']}")
    print(f"Why: {feedback['why_it_matters']}")
    print("Evidence: " + "; ".join(feedback["evidence"]))
    action = feedback["next_action"]
    if action:
        print(f"Next: {action['text']}")
        print(f"Command: {action['command']}")
        print(f"Safety: {action['safety']}")
        print("Confirmation: " + ("required" if action["requires_confirmation"] else "not required"))
