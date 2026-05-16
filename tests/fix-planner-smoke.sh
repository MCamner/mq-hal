#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal fix planner"

echo "[1/3] syntax check"
python3 -m py_compile "$ROOT/scripts/fix_planner.py"

echo "[2/3] JSON mode works"
"$ROOT/bin/mq-hal" fix-doctor --no-ai --json >/tmp/mq-hal-fix-plan.json
python3 -m json.tool /tmp/mq-hal-fix-plan.json >/dev/null

echo "[3/3] text mode works"
"$ROOT/bin/mq-hal" fix-doctor --no-ai >/tmp/mq-hal-fix-plan.txt
grep -q "HAL Fix Planner" /tmp/mq-hal-fix-plan.txt
grep -q "Nothing was executed" /tmp/mq-hal-fix-plan.txt

echo "OK: fix planner smoke test passed"
