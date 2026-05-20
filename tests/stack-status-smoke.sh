#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: stack-status"

echo "[1/5] syntax"
python3 -m py_compile scripts/stack_status.py

echo "[2/5] sample text output"
python3 scripts/stack_status.py --sample | grep -q "HAL Stack Status"
python3 scripts/stack_status.py --sample | grep -q "repo-signal"
python3 scripts/stack_status.py --sample | grep -q "mq-mcp"

echo "[3/5] sample json output"
python3 scripts/stack_status.py --sample --json | python3 -m json.tool >/dev/null

echo "[4/5] bin wrapper routes stack-status"
./bin/mq-hal stack-status --sample | grep -q "HAL Stack Status"

echo "[5/5] alias routes stack"
./bin/mq-hal stack --sample | grep -q "HAL Stack Status"

echo "OK: stack-status smoke passed"
