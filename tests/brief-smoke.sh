#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HAL="$ROOT/bin/mq-hal"

echo "SMOKE: mq-hal brief"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/brief.py"

echo "[2/4] brief runs without error"
output="$("$HAL" brief --no-memory 2>&1)"
if [[ -z "$output" ]]; then
  echo "brief produced no output" >&2
  exit 1
fi

echo "[3/4] brief output contains expected sections"
echo "$output" | grep -q "HAL Brief"
echo "$output" | grep -q "Doctor:"
echo "$output" | grep -q "Next step"

echo "[4/4] brief --json produces valid JSON"
json_out="$("$HAL" brief --json --no-memory 2>&1)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert 'git' in d and 'doctor' in d" <<< "$json_out"

echo "OK: brief smoke test passed"
