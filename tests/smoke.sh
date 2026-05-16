#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal"

echo "[1/5] wrapper exists"
test -x "$ROOT/bin/mq-hal"

echo "[2/5] python script exists"
test -f "$ROOT/scripts/hal.py"

echo "[3/5] config exists"
test -f "$ROOT/config/repos.json"

echo "[4/5] prompt exists"
test -f "$ROOT/prompts/system.txt"

echo "[5/5] help works"
"$ROOT/bin/mq-hal" --help >/dev/null

echo "OK: smoke test passed"
