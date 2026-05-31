#!/usr/bin/env bash
# Verify every command dispatched in bin/mq-hal is documented in
# docs/COMMAND_SURFACE.md.
#
# Commands are extracted dynamically from the case statement so that
# adding a new case entry without updating COMMAND_SURFACE.md is caught
# automatically at release-check time.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SURFACE="$ROOT/docs/COMMAND_SURFACE.md"
BIN="$ROOT/bin/mq-hal"
FAILED=0

fail() { echo "FAIL: $*" >&2; FAILED=1; }

test -f "$SURFACE" || { echo "FAIL: docs/COMMAND_SURFACE.md not found" >&2; exit 1; }
test -f "$BIN"     || { echo "FAIL: bin/mq-hal not found" >&2; exit 1; }

# Dynamically extract the canonical (first) command name from each case
# pattern in bin/mq-hal.  Patterns look like:
#   brief)
#   stack|stack-status|status-stack)
# The first alternative is the canonical name; aliases are allowed as long
# as they appear in COMMAND_SURFACE.md (which they do, in the Aliases column).
BIN_COMMANDS=()
while IFS= read -r cmd; do
  [[ -n "$cmd" ]] && BIN_COMMANDS+=("$cmd")
done < <(
  grep -E '^\s{2}[a-z][a-z0-9|_-]*\)' "$BIN" \
    | sed 's/^[[:space:]]*//' \
    | sed 's/|.*//' \
    | sed 's/)//'
)

# Every command dispatched in bin/mq-hal must appear in COMMAND_SURFACE.md.
for cmd in "${BIN_COMMANDS[@]}"; do
  grep -q "\`${cmd}\`" "$SURFACE" \
    || fail "${cmd} dispatched in bin/mq-hal but not documented in COMMAND_SURFACE.md"
done

if [[ "$FAILED" -eq 0 ]]; then
  echo "OK: all ${#BIN_COMMANDS[@]} commands in bin/mq-hal are documented in COMMAND_SURFACE.md"
else
  exit 1
fi
