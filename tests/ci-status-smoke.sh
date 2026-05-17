#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: ci-status"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/ci_status.py"

echo "[2/4] ci --sample runs without error"
output="$("$ROOT/bin/mq-hal" ci --sample 2>&1)"
if [[ -z "$output" ]]; then
  echo "ci produced no output" >&2
  exit 1
fi

echo "[3/4] output contains expected sections"
echo "$output" | grep -q "HAL CI Status"
echo "$output" | grep -q "Recommendation"

echo "[4/4] --json produces valid JSON with expected keys"
json_out="$("$ROOT/bin/mq-hal" ci --sample --json 2>&1)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert 'repo' in d and 'status' in d and 'runs' in d" <<< "$json_out"

echo "OK: ci-status smoke test passed"
