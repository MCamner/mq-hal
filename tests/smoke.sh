#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/25] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/25] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/25] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/25] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/25] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/25] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/25] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/25] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/25] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/25] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[11/25] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[12/25] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[13/25] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[14/25] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[15/25] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[16/25] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[17/25] install flow smoke works"
"$ROOT/tests/install-flow-smoke.sh" >/dev/null

echo "[18/25] visual HAL smoke works"
"$ROOT/tests/visual-hal-smoke.sh" >/dev/null

echo "[19/25] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[20/25] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[21/25] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[22/25] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "[23/25] runtime control smoke works"
"$ROOT/tests/runtime-smoke.sh" >/dev/null

echo "[24/25] dashboard smoke works"
"$ROOT/tests/dashboard-smoke.sh" >/dev/null

echo "[25/25] history smoke works"
"$ROOT/tests/history-smoke.sh" >/dev/null

echo "OK: smoke test passed"
