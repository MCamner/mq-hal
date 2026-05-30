#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/14] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/14] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/14] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/14] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/14] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/14] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/14] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/14] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/14] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/14] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/14] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[12/14] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[13/14] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[14/14] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "OK: smoke test passed"
