#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: stack-status"

TMPBIN="$(mktemp -d)"
trap 'rm -rf "$TMPBIN"' EXIT

cat >"$TMPBIN/mq-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == "stack cockpit --json" ]]; then
  printf '%s\n' '{"title":"MQ Stack","components":[{"name":"mq-agent","status":"PASS"},{"name":"mq-mcp","status":"PASS"},{"name":"repo-signal","status":"PASS"},{"name":"mqobsidian","status":"WARN"},{"name":"brain","status":"PASS"}],"overall":{"score":92,"total":100,"status":"PASS"}}'
  exit 0
fi
echo "unexpected mq-agent args: $*" >&2
exit 2
SH
chmod +x "$TMPBIN/mq-agent"
export PATH="$TMPBIN:$PATH"

echo "[1/8] syntax"
python3 -m py_compile scripts/stack_status.py
python3 -m py_compile hal/stack.py
python3 -m py_compile hal/status.py
python3 -m py_compile hal/doctor.py

echo "[2/8] cockpit text output"
python3 scripts/stack_status.py | grep -q "MQ Stack"
python3 scripts/stack_status.py | grep -q "mq-agent"
python3 scripts/stack_status.py | grep -q "92/100"

echo "[3/8] cockpit json output"
python3 scripts/stack_status.py --json | python3 -m json.tool >/dev/null
python3 scripts/stack_status.py --json | grep -q '"components"'
python3 scripts/stack_status.py --json | grep -q '"mqobsidian"'

echo "[4/8] sample text output"
python3 scripts/stack_status.py --sample | grep -q "MQ Stack"
python3 scripts/stack_status.py --sample | grep -q "repo-signal"
python3 scripts/stack_status.py --sample | grep -q "mq-mcp"

echo "[5/8] sample json output"
python3 scripts/stack_status.py --sample --json | python3 -m json.tool >/dev/null
python3 scripts/stack_status.py --sample --json | grep -q '"components"'

echo "[6/8] legacy fallback still available"
python3 scripts/stack_status.py --legacy --sample | grep -q "MQ Stack"
python3 scripts/stack_status.py --legacy | grep -q "HAL Stack Status"
python3 scripts/stack_status.py --sample | grep -q "repo-signal"

echo "[7/8] bin wrapper routes aliases"
./bin/mq-hal stack --sample | grep -q "MQ Stack"
./bin/mq-hal status --sample | grep -q "MQ Stack"
./bin/mq-hal stack-status --legacy | grep -q "HAL Stack Status"

echo "[8/8] real mq_stack_cockpit.v1 contract"
# The stub above uses the shape hal/stack.py was written against. mq-agent
# actually emits repos[]/repo/gate/overall_gate, so this stub is a trimmed
# copy of live `mq-agent stack cockpit --json` output.
V1BIN="$(mktemp -d)"
trap 'rm -rf "$TMPBIN" "$V1BIN"' EXIT
cat >"$V1BIN/mq-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == "stack cockpit --json" ]]; then
  printf '%s\n' '{"schema":"mq_stack_cockpit.v1","overall_gate":"GO","overall_contract":"READY","brain_export":{"date":"2026-07-23","age_days":14,"status":"stale"},"repos":[{"repo":"mqlaunch","role":"Terminal entrypoint","exists":true,"gate":"GO","contract":"READY"},{"repo":"mq-agent","role":"Orchestrator","exists":true,"gate":"GO","contract":"READY"},{"repo":"mqobsidian","role":"Second brain","exists":true,"gate":"—","contract":"—"}],"checked_at":"2026-08-06T20:00:00Z"}'
  exit 0
fi
echo "unexpected mq-agent args: $*" >&2
exit 2
SH
chmod +x "$V1BIN/mq-agent"

v1_out="$(PATH="$V1BIN:$PATH" python3 scripts/stack_status.py)"
echo "$v1_out" | grep -q "mqlaunch"
echo "$v1_out" | grep -q "mq-agent"
echo "$v1_out" | grep -q "GO"
if echo "$v1_out" | grep -q "No stack items found"; then
  echo "FAIL: cockpit v1 repos[] not rendered" >&2
  exit 1
fi
# placeholder dashes must not reach the operator as a status
if echo "$v1_out" | grep -qE "mqobsidian +—"; then
  echo "FAIL: placeholder dash rendered as a status" >&2
  exit 1
fi
# A GO stack whose only blemish is a stale truth export is a WARN, not
# UNAVAILABLE: brain_export.status="stale" used to normalize to UNAVAILABLE and
# drown out overall_gate entirely.
echo "$v1_out" | grep -q "^Overall:"
echo "$v1_out" | grep -q "GO"
echo "$v1_out" | grep -q "WARN: Stack needs attention"
if echo "$v1_out" | grep -q "UNAVAILABLE"; then
  echo "FAIL: GO stack with a stale export reported as UNAVAILABLE" >&2
  exit 1
fi

echo "OK: stack-status smoke passed"
