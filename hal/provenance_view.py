"""Human presentation of mq-agent's stack provenance record.

mq-agent owns runtime provenance: the observations, the comparisons, the
reason codes, the status and the remediation. Its reducer holds the relation

    reason -> status -> action

explicitly. This module shows what that reducer produced.

The boundary invariant:

    Presentation may expose the record and its conclusions; it must not
    derive a new conclusion, remedy, severity, or process policy of its own.

So there is no reason-to-status map, no reason-to-action map, and no severity
table keyed on reason codes here. Colour keys on the supplied status and
nothing else, and an unfamiliar future status or reason code prints verbatim
rather than crashing or being translated into vocabulary mq-hal already knows.

This lives apart from `hal/provenance.py` on purpose. Transport is held to the
stricter rule that it may not name provenance vocabulary at all, which is what
catches a dormant helper that would turn a failed subprocess into an invented
finding. Presentation has to name that vocabulary to display it. Keeping both
in one file would mean the transport rule could no longer be stated.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from hal.provenance import read_provenance  # noqa: E402


STATUS_STYLE: dict[str, str] = {
    "PASS": "\033[32m",
    "WARN": "\033[33m",
    "FAIL": "\033[31m",
    "UNAVAILABLE": "\033[35m",
}

_NEUTRAL = ""
_RESET = "\033[0m"

_NAME_WIDTH = 44
_LABEL_WIDTH = 12


def _colour_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _styled(status: str) -> str:
    if not _colour_enabled():
        return status
    style = STATUS_STYLE.get(status, _NEUTRAL)
    if not style:
        return status
    return f"{style}{status}{_RESET}"


def _short(commit: Any) -> str:
    if not isinstance(commit, str) or not commit:
        return "—"
    return commit[:7]


def _identity(identity: Any) -> str:
    """One line for an observed-or-not runtime identity.

    Absence and uncertainty are different answers and must not collapse:
    a missing identity was never observed, while an observed identity of
    unknown quality was seen but cannot be trusted to name a commit.
    """
    if identity is None:
        return "not observed"
    if not isinstance(identity, dict):
        return "not observed"
    if identity.get("identity_quality") == "unknown":
        return "identity unknown"
    return _short(identity.get("commit"))


def _probe(component: dict[str, Any]) -> str:
    """One line for the running probe.

    Not asking, asking and reaching nothing, and reaching the endpoint are
    different states. None of them means the component is fine, and none of
    them means it is broken.
    """
    probe = component.get("running_probe")
    if not isinstance(probe, dict) or probe.get("attempted") is not True:
        return "not asked"
    # Report the two booleans the record carries, and nothing beyond them.
    # Reaching an endpoint is not the same as being told an identity: a probe
    # can be reachable while `running` stays absent, and calling that
    # "answered" would be mq-hal concluding something the record does not say.
    reached = "reachable" if probe.get("reachable") is True else "unreachable"
    endpoint = probe.get("endpoint")
    if isinstance(endpoint, str) and endpoint:
        return f"asked — {reached} ({endpoint})"
    return f"asked — {reached}"


def _row(label: str, value: str) -> None:
    print(f"  {label:<{_LABEL_WIDTH}} {value}")


def render(record: dict[str, Any]) -> None:
    """Show the record. Conclude nothing from it."""
    summary = record.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    overall = str(summary.get("status") or "—")
    print(f"{'MQ Runtime Provenance':<{_NAME_WIDTH}} {_styled(overall)}")

    components = record.get("components")
    components = components if isinstance(components, list) else []
    for component in components:
        if not isinstance(component, dict):
            continue
        print()
        name = str(component.get("name") or "—")
        status = str(component.get("status") or "—")
        print(f"{name:<{_NAME_WIDTH}} {_styled(status)}")

        checkout = component.get("checkout")
        checkout = checkout if isinstance(checkout, dict) else {}
        _row("checkout", _short(checkout.get("head")))
        _row("installed", _identity(component.get("installed")))
        _row("running", _identity(component.get("running")))
        _row("probe", _probe(component))

        reasons = component.get("reasons")
        if isinstance(reasons, list) and reasons:
            for index, reason in enumerate(reasons):
                _row("reasons" if index == 0 else "", str(reason))

    action = summary.get("next_action")
    if action:
        print()
        print("Next action")
        print(f"  {action}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal provenance",
        description="Show the runtime provenance record produced by mq-agent.",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    result = read_provenance()
    if not result.ok:
        # No record was obtained. Say only that, and say it on stderr so the
        # JSON surface stays empty rather than carrying an invented record.
        print(result.error, file=sys.stderr)
        return result.returncode or 1

    if args.json:
        # The producer's own bytes. mq-hal has no reason to re-serialize a
        # document it does not own, and re-serializing is how key order,
        # spacing and unknown fields quietly change.
        print(result.raw)
        return 0

    render(result.data or {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
