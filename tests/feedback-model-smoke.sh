#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: feedback model"

python3 - <<'PY'
import json
import subprocess
from hal.feedback import (
    FeedbackError,
    attach_feedback,
    execution_feedback,
    make_next_action,
    normalize_status,
    validate_feedback,
)

allowed = {"PASS", "WARN", "FAIL", "SKIPPED", "UNAVAILABLE"}
assert {normalize_status(value) for value in (
    "OK", "RUNNING", "DOWN", "UNKNOWN", "MISS", "READY", "WARN"
)} <= allowed

healthy = attach_feedback(
    {"status": "RUNNING"},
    what="Runtime checks passed",
    why="Required services responded",
    evidence=["4 probes completed"],
)
assert healthy["status"] == "PASS"
assert healthy["feedback"]["next_action"] is None
validate_feedback(healthy["feedback"])

action = make_next_action(
    text="Start Ollama",
    command="ollama serve",
    safety="local-process",
    requires_confirmation=False,
)
degraded = attach_feedback(
    {"status": "missing"},
    what="Ollama is unavailable",
    why="Local model routing cannot run",
    evidence=["ollama binary not found"],
    next_action=action,
)
assert degraded["status"] == "UNAVAILABLE"
assert degraded["feedback"]["next_action"]["command"] == "ollama serve"

try:
    make_next_action(
        text="Delete data", command="rm -rf data", safety="destructive",
        requires_confirmation=False,
    )
except FeedbackError:
    pass
else:
    raise AssertionError("destructive action without confirmation was accepted")

assert execution_feedback(130, "Operator action")["status"] == "SKIPPED"
assert execution_feedback(9, "Operator action")["status"] == "FAIL"

try:
    validate_feedback({"schema": "mq.feedback.v1", "status": "MAYBE"})
except FeedbackError:
    pass
else:
    raise AssertionError("invalid feedback JSON was accepted")

schema = json.load(open("schemas/feedback.schema.json", encoding="utf-8"))
assert set(schema["properties"]["status"]["enum"]) == allowed

commands = [
    ["./bin/mq-hal", "stack", "--sample", "--json"],
    ["./bin/mq-hal", "release", "--sample", "--json"],
    ["./bin/mq-hal", "runtime", "--sample", "--json"],
    ["./bin/mq-hal", "brain", "--sample", "--json"],
    ["./bin/mq-hal", "context", "--sample", "--json"],
    ["./bin/mq-hal", "dashboard", "--sample", "--json"],
    ["./bin/mq-hal", "next", "--sample", "--json"],
    ["./bin/mq-hal", "open", "CHANGELOG.md", "--repo", "mq-hal", "--json"],
    ["./bin/mq-hal", "fix", "test blocker", "--json"],
]
for command in commands:
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    payload = json.loads(result.stdout)
    feedback = payload["feedback"]
    validate_feedback(feedback)
    assert feedback["status"] in allowed, (command, feedback)

runtime_json = json.loads(subprocess.run(
    ["./bin/mq-hal", "runtime", "--sample", "--json"],
    text=True, capture_output=True, check=True,
).stdout)
runtime_human = subprocess.run(
    ["./bin/mq-hal", "runtime", "--sample"],
    text=True, capture_output=True, check=True,
).stdout
assert f"{runtime_json['feedback']['status']}:" in runtime_human
PY

echo "OK: feedback model smoke passed"
