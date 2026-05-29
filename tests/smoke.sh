#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/8] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/8] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/8] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/8] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/8] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/10] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/10] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/10] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "[9/10] memory-status smoke works"
"$ROOT/tests/memory-status-smoke.sh" >/dev/null

echo "[10/10] agent-brief smoke works"
"$ROOT/tests/agent-brief-smoke.sh" >/dev/null

echo "OK: smoke test passed"
