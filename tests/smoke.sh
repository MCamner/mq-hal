#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/27] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/27] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/27] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/27] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/27] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/27] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/27] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/27] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/27] feedback model smoke works"
"$ROOT/tests/feedback-model-smoke.sh" >/dev/null

echo "[10/27] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[11/27] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[12/27] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[13/27] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[14/27] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[15/27] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[16/27] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[17/27] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[18/27] install flow smoke works"
"$ROOT/tests/install-flow-smoke.sh" >/dev/null

echo "[19/27] visual HAL smoke works"
"$ROOT/tests/visual-hal-smoke.sh" >/dev/null

echo "[20/27] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[21/27] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[22/27] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[23/27] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "[24/27] runtime control smoke works"
"$ROOT/tests/runtime-smoke.sh" >/dev/null

echo "[25/27] dashboard smoke works"
"$ROOT/tests/dashboard-smoke.sh" >/dev/null

echo "[26/27] history smoke works"
"$ROOT/tests/history-smoke.sh" >/dev/null

echo "[27/27] operator actions smoke works"
"$ROOT/tests/operator-smoke.sh" >/dev/null

echo "OK: smoke test passed"
