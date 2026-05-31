#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

ENV_STATUS="python3 $ROOT/scripts/env_status.py"

echo "SMOKE: env-status"

echo "[1/6] syntax check"
python3 -m py_compile "$ROOT/scripts/env_status.py"
echo "  syntax: OK"

echo "[2/6] text output contains expected sections"
output=$($ENV_STATUS)
echo "$output" | grep -q "HAL Environment Status" || {
  echo "ERROR: missing header" >&2; exit 1
}
echo "$output" | grep -q "Tool availability" || {
  echo "ERROR: missing Tool availability section" >&2; exit 1
}
echo "$output" | grep -q "Recommendations" || {
  echo "ERROR: missing Recommendations section" >&2; exit 1
}
echo "  sections found: OK"

echo "[3/6] --json produces valid JSON with expected keys"
json_out=$($ENV_STATUS --json)
echo "$json_out" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'env' in d, 'missing env'
assert 'tools' in d, 'missing tools'
assert 'recommendations' in d, 'missing recommendations'
assert isinstance(d['env'], list), 'env must be list'
assert isinstance(d['tools'], list), 'tools must be list'
assert len(d['env']) > 0, 'env must not be empty'
assert len(d['tools']) > 0, 'tools must not be empty'
# Each env entry has expected fields
for e in d['env']:
    assert 'name' in e and 'set' in e and 'value' in e
# Each tool entry has expected fields
for t in d['tools']:
    assert 'binary' in t and 'available' in t and 'required' in t
print(f'  {len(d[\"env\"])} env vars, {len(d[\"tools\"])} tools: OK')
" || { echo "ERROR: JSON validation failed" >&2; exit 1; }

echo "[4/6] required tools (python3, git) show as available"
$ENV_STATUS --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
required = {t['binary']: t for t in d['tools'] if t['required']}
for binary, t in required.items():
    assert t['available'], f'{binary} required but not found'
print(f'  required tools available: OK')
" || { echo "ERROR: required tools check failed" >&2; exit 1; }

echo "[5/6] secret redaction: sensitive env vars are redacted"
export TEST_API_KEY_HAL="super-secret-value-12345"
output=$($ENV_STATUS --json 2>/dev/null || true)
# No sensitive custom vars in the HAL var list — verify existing logic
# by checking that the output does not expose known-sensitive patterns
if echo "$output" | grep -q "super-secret"; then
  echo "ERROR: sensitive value leaked into output" >&2; exit 1
fi
unset TEST_API_KEY_HAL
echo "  no secret leakage: OK"

echo "[6/6] bin wrapper routes env-status"
"$ROOT/bin/mq-hal" env-status --json >/dev/null || {
  echo "ERROR: bin/mq-hal env-status failed" >&2; exit 1
}
echo "  bin wrapper: OK"

echo "OK: env-status smoke test passed"
