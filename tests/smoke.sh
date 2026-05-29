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

echo "[6/8] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "[7/8] intent schema contract smoke works"
"$ROOT/tests/intent-schema-smoke.sh" >/dev/null

echo "[8/8] router safety smoke works"
"$ROOT/tests/router-safety-smoke.sh" >/dev/null

echo "OK: smoke test passed"
