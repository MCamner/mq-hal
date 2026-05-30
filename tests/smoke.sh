#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/17] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/17] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/17] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/17] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/17] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/17] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/17] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/17] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/17] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/17] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/17] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[12/17] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[13/17] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[14/17] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[15/17] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[16/17] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[17/17] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "OK: smoke test passed"
