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

echo "[1/7] syntax"
python3 -m py_compile scripts/stack_status.py
python3 -m py_compile hal/stack.py
python3 -m py_compile hal/status.py
python3 -m py_compile hal/doctor.py

echo "[2/7] cockpit text output"
python3 scripts/stack_status.py | grep -q "MQ Stack"
python3 scripts/stack_status.py | grep -q "mq-agent"
python3 scripts/stack_status.py | grep -q "92/100"

echo "[3/7] cockpit json output"
python3 scripts/stack_status.py --json | python3 -m json.tool >/dev/null
python3 scripts/stack_status.py --json | grep -q '"components"'
python3 scripts/stack_status.py --json | grep -q '"mqobsidian"'

echo "[4/7] sample text output"
python3 scripts/stack_status.py --sample | grep -q "MQ Stack"
python3 scripts/stack_status.py --sample | grep -q "repo-signal"
python3 scripts/stack_status.py --sample | grep -q "mq-mcp"

echo "[5/7] sample json output"
python3 scripts/stack_status.py --sample --json | python3 -m json.tool >/dev/null
python3 scripts/stack_status.py --sample --json | grep -q '"components"'

echo "[6/7] legacy fallback still available"
python3 scripts/stack_status.py --legacy --sample | grep -q "MQ Stack"
python3 scripts/stack_status.py --legacy | grep -q "HAL Stack Status"
python3 scripts/stack_status.py --sample | grep -q "repo-signal"

echo "[7/7] bin wrapper routes aliases"
./bin/mq-hal stack --sample | grep -q "MQ Stack"
./bin/mq-hal status --sample | grep -q "MQ Stack"
./bin/mq-hal stack-status --legacy | grep -q "HAL Stack Status"

echo "OK: stack-status smoke passed"
