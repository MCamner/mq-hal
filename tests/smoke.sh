#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/11] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/11] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/11] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/11] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/11] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/11] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/11] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/11] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/11] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/11] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/11] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "OK: smoke test passed"
