#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/6] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/6] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/6] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/6] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/6] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "[6/6] router smoke works"
"$ROOT/tests/hal-router-smoke.sh" >/dev/null

echo "OK: smoke test passed"
