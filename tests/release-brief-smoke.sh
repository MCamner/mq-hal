#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: release-brief"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/release_brief.py"

echo "[2/4] sample text works"
output="$("$ROOT/bin/mq-hal" release-brief --sample --no-memory 2>&1)"
echo "$output" | grep -q "HAL Release Brief"

echo "[3/4] sample JSON valid"
json_out="$("$ROOT/bin/mq-hal" release-brief --sample --json --no-memory 2>&1)"
python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert 'repo' in d
assert 'overall' in d
assert 'checks' in d
assert isinstance(d['checks'], list)
" <<< "$json_out"

echo "[4/4] skip flags parse"
"$ROOT/bin/mq-hal" release-brief --sample --skip-gh --skip-doctor --skip-release-check --no-memory \
  | grep -q "HAL Release Brief"

echo "OK: release-brief smoke test passed"
