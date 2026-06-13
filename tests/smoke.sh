#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/23] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/23] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/23] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/23] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/23] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/23] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/23] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/23] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/23] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/23] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[11/23] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[12/23] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[13/23] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[14/23] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[15/23] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[16/23] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[17/23] install flow smoke works"
"$ROOT/tests/install-flow-smoke.sh" >/dev/null

echo "[18/23] visual HAL smoke works"
"$ROOT/tests/visual-hal-smoke.sh" >/dev/null

echo "[19/23] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[20/23] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[21/23] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[22/23] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "[23/23] runtime control smoke works"
"$ROOT/tests/runtime-smoke.sh" >/dev/null

echo "OK: smoke test passed"
