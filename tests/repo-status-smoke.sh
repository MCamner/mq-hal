#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: repo-status"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/repo_status.py"

echo "[2/4] repo-status --sample runs without error"
output="$("$ROOT/bin/mq-hal" repo-status --sample 2>&1)"
if [[ -z "$output" ]]; then
  echo "repo-status produced no output" >&2
  exit 1
fi

echo "[3/4] output contains expected sections"
echo "$output" | grep -q "HAL Repo Status"
echo "$output" | grep -q "Recommendation"

echo "[4/4] --json produces valid JSON with expected keys"
json_out="$("$ROOT/bin/mq-hal" repo-status --sample --json 2>&1)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert 'repo' in d and 'status' in d and 'branch' in d" <<< "$json_out"

echo "OK: repo-status smoke test passed"
