"""Transport for mq-agent's stack provenance record.

mq-agent owns provenance semantics. This module only carries the record
across the process boundary; it does not interpret, normalize, or complete
it, and it does not decide anything about the stack.

The boundary invariant:

    Transport may establish whether a provenance record was obtained; it
    may not establish anything about provenance when no record was
    obtained.

So every failure path here returns `data=None`. A missing mq-agent, a
timeout, a crash, unparseable output, or output that is not the expected
record are all mq-hal availability problems. None of them is a provenance
finding, and none of them may be turned into one by inventing a status, a
reason code, or a next action.

When a record is obtained it is handed on exactly as received. Unknown
fields and unknown reason codes are mq-agent's business, not ours.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from hal.stack import find_mq_agent


PROVENANCE_COMMAND = ["mq-agent", "stack", "provenance", "--json"]

# The contract mq-hal declares under compatibility.consumes. Checking it is
# transport's version of confirming the parcel is the one that was ordered;
# it is not a check of the record's contents.
PROVENANCE_SCHEMA = "mq.stack-provenance.v1"


@dataclass(frozen=True)
class ProvenanceResult:
    data: dict[str, Any] | None
    raw: str
    command: list[str]
    returncode: int
    error: str

    @property
    def ok(self) -> bool:
        return self.data is not None and self.returncode == 0


def read_provenance(timeout: int = 20) -> ProvenanceResult:
    """Run mq-agent's provenance command and return the record, or nothing.

    A returned `ProvenanceResult` with `data is None` says only that no
    record was obtained. It never says anything about the provenance of
    the stack, because nothing was observed.
    """
    mq_agent = find_mq_agent()
    if not mq_agent:
        return ProvenanceResult(
            data=None,
            raw="",
            command=PROVENANCE_COMMAND,
            returncode=127,
            error="mq-agent not found",
        )

    command = [mq_agent, *PROVENANCE_COMMAND[1:]]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProvenanceResult(
            data=None,
            raw="",
            command=command,
            returncode=124,
            error="mq-agent stack provenance timed out",
        )
    except OSError as exc:
        return ProvenanceResult(
            data=None,
            raw="",
            command=command,
            returncode=1,
            error=str(exc),
        )

    raw = (result.stdout or "").strip()
    if result.returncode != 0:
        return ProvenanceResult(
            data=None,
            raw=raw,
            command=command,
            returncode=int(result.returncode),
            error=(result.stderr or "").strip() or "mq-agent stack provenance failed",
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ProvenanceResult(
            data=None,
            raw=raw,
            command=command,
            returncode=1,
            error=f"could not parse mq-agent provenance JSON: {exc}",
        )

    if not isinstance(parsed, dict):
        return ProvenanceResult(
            data=None,
            raw=raw,
            command=command,
            returncode=1,
            error="mq-agent provenance JSON was not an object",
        )

    schema = parsed.get("schema")
    if schema != PROVENANCE_SCHEMA:
        return ProvenanceResult(
            data=None,
            raw=raw,
            command=command,
            returncode=1,
            error=(
                f"expected {PROVENANCE_SCHEMA}, got {schema!r} — "
                "this is not a provenance record"
            ),
        )

    return ProvenanceResult(
        data=parsed,
        raw=raw,
        command=command,
        returncode=0,
        error="",
    )
