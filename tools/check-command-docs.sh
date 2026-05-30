#!/usr/bin/env bash
# Verify every canonical mq-hal command is documented in
# docs/COMMAND_SURFACE.md and dispatched in bin/mq-hal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SURFACE="$ROOT/docs/COMMAND_SURFACE.md"
BIN="$ROOT/bin/mq-hal"
FAILED=0

fail() { echo "FAIL: $*" >&2; FAILED=1; }

test -f "$SURFACE" || { echo "FAIL: docs/COMMAND_SURFACE.md not found" >&2; exit 1; }
test -f "$BIN"     || { echo "FAIL: bin/mq-hal not found" >&2; exit 1; }

COMMANDS=(
  brief
  audit
  stack-status
  release-brief
  repo-status
  ci
  doctor-summary
  fix-doctor
  session
  last
  remember
  timeline
  memory-path
  memory-status
  index
  search
  ask-repo
  repo-map
  agent-brief
  hello
  tools
  models
  model-status
  model-test
  plan
  critic
  execute
)

for cmd in "${COMMANDS[@]}"; do
  grep -q "\`${cmd}\`" "$SURFACE" \
    || fail "${cmd} not in docs/COMMAND_SURFACE.md"
  grep -q "${cmd}" "$BIN" \
    || fail "${cmd} not dispatched in bin/mq-hal"
done

if [[ "$FAILED" -eq 0 ]]; then
  echo "OK: all ${#COMMANDS[@]} commands documented and dispatched"
else
  exit 1
fi
