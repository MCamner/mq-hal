#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/15] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/15] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/15] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/15] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/15] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/15] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/15] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/15] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/15] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/15] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/15] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[12/15] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[13/15] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "[14/15] plan smoke works"
"$ROOT/tests/plan-smoke.sh" >/dev/null

echo "[15/15] critic smoke works"
"$ROOT/tests/critic-smoke.sh" >/dev/null

echo "OK: smoke test passed"
