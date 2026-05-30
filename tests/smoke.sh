#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/20] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/20] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/20] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/20] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/20] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/20] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/20] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/20] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/20] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/20] repo-memory smoke works"
"$ROOT/tests/repo-memory-smoke.sh" >/dev/null

echo "[11/20] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[12/20] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[13/20] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[14/20] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[15/20] model-status smoke works"
"$ROOT/tests/model-status-smoke.sh" >/dev/null

echo "[16/20] model-test smoke works"
"$ROOT/tests/model-test-smoke.sh" >/dev/null

echo "[17/20] prompt regression smoke works"
"$ROOT/tests/prompt-regression-smoke.sh" >/dev/null

echo "[18/20] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[19/20] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "[20/20] execute smoke works"
"$ROOT/tests/execute-smoke.sh" >/dev/null

echo "OK: smoke test passed"
