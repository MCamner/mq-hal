#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/19] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/19] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/19] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/19] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/19] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/19] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/19] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/19] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/19] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/19] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/19] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[12/19] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[13/19] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[14/19] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[15/19] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[16/19] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[17/19] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[18/19] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[19/19] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "OK: smoke test passed"
