#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/24] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/24] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/24] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/24] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/24] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/24] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/24] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/24] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/24] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/24] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[11/24] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[12/24] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[13/24] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[14/24] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[15/24] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[16/24] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[17/24] install flow smoke works"
"$ROOT/tests/install-flow-smoke.sh" >/dev/null

echo "[18/24] visual HAL smoke works"
"$ROOT/tests/visual-hal-smoke.sh" >/dev/null

echo "[19/24] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[20/24] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[21/24] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[22/24] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "[23/24] runtime control smoke works"
"$ROOT/tests/runtime-smoke.sh" >/dev/null

echo "[24/24] dashboard smoke works"
"$ROOT/tests/dashboard-smoke.sh" >/dev/null

echo "OK: smoke test passed"
