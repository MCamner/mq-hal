"""Transport for mq-agent's stack compatibility report.

mq-agent owns the compatibility assessment: the findings, their codes, the
statuses and the next action. This module only carries the report across the
process boundary; it does not interpret, normalize, or complete it.

The boundary invariant:

    Transport may establish whether a compatibility report was obtained; it
    may not establish anything about compatibility when no report was
    obtained.

One difference from provenance transport matters. `mq-agent stack
compatibility --json` prints a complete report *and* exits 2 for FAIL and 3 for
UNAVAILABLE: the exit code is part of the verdict, not a sign that no report
exists. So a non-zero exit with a parseable report of the right schema is a
report. A non-zero exit without one (mq-agent missing, a crash, an interrupt)
is an mq-hal availability problem and returns `data=None`.

When a report is obtained it is handed on exactly as received, together with
the producer's exit code.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from hal.stack import find_mq_agent


COMPATIBILITY_COMMAND = ["mq-agent", "stack", "compatibility", "--json"]

# The contract mq-hal declares under compatibility.consumes. Checking it is
# transport's version of confirming the parcel is the one that was ordered;
# it is not a check of the report's contents.
COMPATIBILITY_SCHEMA = "mq.stack-compatibility.v1"

# Exit codes mq-agent uses for a report it did produce. Anything else means the
# report was not produced, whatever stdout happens to contain.
_REPORT_EXIT_CODES = frozenset({0, 1, 2, 3})


@dataclass(frozen=True)
class CompatibilityResult:
    data: dict[str, Any] | None
    raw: str
    command: list[str]
    returncode: int
    error: str

    @property
    def ok(self) -> bool:
        return self.data is not None


def read_compatibility(timeout: int = 60) -> CompatibilityResult:
    """Run mq-agent's compatibility command and return the report, or nothing.

    `returncode` is mq-agent's own exit code when a report was obtained. A
    result with `data is None` says only that no report was obtained, never
    anything about the stack.
    """
    mq_agent = find_mq_agent()
    if not mq_agent:
        return CompatibilityResult(
            data=None, raw="", command=COMPATIBILITY_COMMAND, returncode=127,
            error="mq-agent not found",
        )

    command = [mq_agent, *COMPATIBILITY_COMMAND[1:]]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return CompatibilityResult(
            data=None, raw="", command=command, returncode=124,
            error="mq-agent stack compatibility timed out",
        )
    except OSError as exc:
        return CompatibilityResult(
            data=None, raw="", command=command, returncode=1, error=str(exc),
        )

    raw = (result.stdout or "").strip()
    returncode = int(result.returncode)
    if returncode not in _REPORT_EXIT_CODES:
        return CompatibilityResult(
            data=None, raw=raw, command=command, returncode=returncode,
            error=(result.stderr or "").strip() or "mq-agent stack compatibility failed",
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return CompatibilityResult(
            data=None, raw=raw, command=command, returncode=returncode or 1,
            error=f"could not parse mq-agent compatibility JSON: {exc}",
        )

    if not isinstance(parsed, dict):
        return CompatibilityResult(
            data=None, raw=raw, command=command, returncode=returncode or 1,
            error="mq-agent compatibility JSON was not an object",
        )

    schema = parsed.get("schema")
    if schema != COMPATIBILITY_SCHEMA:
        return CompatibilityResult(
            data=None, raw=raw, command=command, returncode=returncode or 1,
            error=(
                f"expected {COMPATIBILITY_SCHEMA}, got {schema!r} — "
                "this is not a compatibility report"
            ),
        )

    return CompatibilityResult(
        data=parsed, raw=raw, command=command, returncode=returncode, error="",
    )
