#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/26] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/26] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/26] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/26] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/26] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/26] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/26] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/26] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/26] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/26] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[11/26] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[12/26] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[13/26] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[14/26] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[15/26] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[16/26] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[17/26] install flow smoke works"
"$ROOT/tests/install-flow-smoke.sh" >/dev/null

echo "[18/26] visual HAL smoke works"
"$ROOT/tests/visual-hal-smoke.sh" >/dev/null

echo "[19/26] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[20/26] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[21/26] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[22/26] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "[23/26] runtime control smoke works"
"$ROOT/tests/runtime-smoke.sh" >/dev/null

echo "[24/26] dashboard smoke works"
"$ROOT/tests/dashboard-smoke.sh" >/dev/null

echo "[25/26] history smoke works"
"$ROOT/tests/history-smoke.sh" >/dev/null

echo "[26/26] operator actions smoke works"
"$ROOT/tests/operator-smoke.sh" >/dev/null

echo "OK: smoke test passed"
