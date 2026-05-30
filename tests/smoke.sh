#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/13] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/13] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/13] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/13] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/13] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/13] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/13] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/13] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/13] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/13] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "[11/13] hello smoke works"
"$ROOT/tests/hello-smoke.sh" >/dev/null

echo "[12/13] tools smoke works"
"$ROOT/tests/tools-smoke.sh" >/dev/null

echo "[13/13] models smoke works"
"$ROOT/tests/models-smoke.sh" >/dev/null

echo "OK: smoke test passed"
