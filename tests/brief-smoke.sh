#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HAL="$ROOT/bin/mq-hal"

echo "SMOKE: mq-hal brief"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/brief.py"

echo "[2/4] sample output works"
output="$("$HAL" brief --sample 2>&1)"
if [[ -z "$output" ]]; then
  echo "brief produced no output" >&2
  exit 1
fi

echo "[3/4] sample output contains expected sections"
echo "$output" | grep -q "HAL Brief"
echo "$output" | grep -q "Doctor:"
echo "$output" | grep -q "Next step"

echo "[4/4] sample --json produces valid JSON with expected keys"
json_out="$("$HAL" brief --sample --json 2>&1)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert 'git' in d and 'doctor' in d" <<< "$json_out"

echo "OK: brief smoke test passed"
